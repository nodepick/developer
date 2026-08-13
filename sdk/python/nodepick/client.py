import time
import uuid
import logging
import httpx
from typing import Optional, List, Dict, Any

logger = logging.getLogger("nodepick")

def _log_request(request: httpx.Request):
    if not logger.isEnabledFor(logging.DEBUG):
        return
    body_str = ""
    if request.content:
        try:
            body_str = f" | Body: {request.content.decode('utf-8')}"
        except Exception:
            body_str = " | Body: <binary>"
    logger.debug(f"HTTP Request: {request.method} {request.url}{body_str}")

def _log_response(response: httpx.Response):
    if not logger.isEnabledFor(logging.DEBUG):
        return
    try:
        response.read()
        body_str = response.text
    except Exception:
        body_str = "<binary or stream>"
    logger.debug(f"HTTP Response: {response.status_code} {response.request.method} {response.request.url} | Response: {body_str}")

async def _async_log_request(request: httpx.Request):
    _log_request(request)

async def _async_log_response(response: httpx.Response):
    _log_response(response)

class NodePickClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.nodepick.ai"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=30.0,
            event_hooks={
                "request": [_log_request],
                "response": [_log_response],
            }
        )

    def mcp(self, node_id: str):
        """Obtain an initialized NodepickMCPClient for a specific compute node."""
        details = self.node_get_details(node_id)
        from .mcp import NodepickMCPClient
        return NodepickMCPClient(node_details=details)


    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def set_api_key(self, api_key: str) -> None:
        """Update API key header dynamically."""
        self.api_key = api_key
        self._client.headers.update(self._get_headers())

    def close(self) -> None:
        """Close the underlying synchronous HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # --- Auth Endpoints ---

    def auth_login(self, email: str, password: str) -> Dict[str, Any]:
        """Exchange email and password for a JWT access token (`POST /api/v1/auth/token`)."""
        response = self._client.post("/api/v1/auth/token", json={"email": email, "password": password})
        response.raise_for_status()
        data = response.json()
        if "accessToken" in data:
            self.set_api_key(data["accessToken"])
        return data

    def get_me(self) -> Dict[str, Any]:
        """Get current user profile (`GET /api/v1/me`)."""
        response = self._client.get("/api/v1/me")
        response.raise_for_status()
        return response.json()

    # --- Compute Nodes Endpoints ---

    def node_list(self) -> List[Dict[str, Any]]:
        """List all compute nodes (`GET /api/v1/nodes`)."""
        response = self._client.get("/api/v1/nodes")
        response.raise_for_status()
        res = response.json()
        return res.get("vms", res if isinstance(res, list) else [])

    def resolve_node_id(self, identifier: str) -> str:
        """Resolve node_id or display_name to node ID / VM UUID."""
        if not identifier:
            return identifier
        nodes = self.node_list()
        for node in nodes:
            name = node.get("display_name") or node.get("displayName")
            vm_id = node.get("id") or node.get("vmId")
            vm_uuid = node.get("vm_uuid") or node.get("vmUuid")
            if identifier in (name, vm_id, vm_uuid):
                return vm_uuid or vm_id or identifier
        return identifier


    def list_regions(self) -> Dict[str, Any]:
        """List regions and hardware options (`GET /api/v1/nodes?view=regions`)."""
        response = self._client.get("/api/v1/nodes?view=regions")
        response.raise_for_status()
        return response.json()

    def node_create(
        self,
        memory: Optional[int] = 512 * 1024 * 1024,
        cpu: Optional[int] = 1,
        network_type: str = "private",
        display_name: Optional[str] = None,
        storage_gb: Optional[int] = None,
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Deploy a new compute node (`POST /api/v1/nodes`)."""
        payload = {
            "networkType": network_type,
        }
        if display_name is not None:
            payload["displayName"] = display_name
        if memory is not None:
            payload["memory"] = memory
        if cpu is not None:
            payload["cpu"] = cpu
        if storage_gb is not None:
            payload["storageGb"] = storage_gb
        if region is not None:
            payload["region"] = region

        response = self._client.post("/api/v1/nodes", json=payload)
        response.raise_for_status()

        res_json = response.json()
        node = res_json.get("vm")
        if not isinstance(node, dict):
            node = res_json

        return node

    def node_wait(self, node_ids: List[str], delay: float = 1.0):
        """Poll list of node IDs until running."""
        import random
        pending = list(node_ids)
        completed = set()
        total = len(node_ids)

        while pending:
            for node_id in list(pending):
                try:
                    time.sleep(random.uniform(0.05, 0.2))
                    detail_resp = self._client.get(f"/api/v1/nodes/{node_id}")
                    detail_resp.raise_for_status()
                    details = detail_resp.json()

                    vmm_details = details.get("vmm") if isinstance(details.get("vmm"), dict) else {}
                    status = vmm_details.get("state", details.get("vm", {}).get("state", details.get("vm", {}).get("status")))

                    if status and str(status).lower() in ("running", "active"):
                        completed.add(node_id)
                        pending.remove(node_id)
                        yield node_id, len(completed), total
                except Exception:
                    pass
            if pending:
                time.sleep(delay)

    def node_get_details(self, node_id: str) -> Dict[str, Any]:
        """Get compute node details (`GET /api/v1/nodes/[id]`)."""
        target_id = self.resolve_node_id(node_id)
        response = self._client.get(f"/api/v1/nodes/{target_id}")
        response.raise_for_status()
        return response.json()

    def node_delete(self, node_id: str) -> Dict[str, Any]:
        """Delete compute node (`DELETE /api/v1/nodes/[id]`)."""
        target_id = self.resolve_node_id(node_id)
        response = self._client.delete(f"/api/v1/nodes/{target_id}")
        response.raise_for_status()
        res = response.json()

        # Poll until node is fully deleted
        while True:
            try:
                detail_resp = self._client.get(f"/api/v1/nodes/{target_id}")
                if detail_resp.status_code in (404, 502):
                    break
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (404, 502):
                    break
            except Exception:
                break
            time.sleep(1.0)

        return res

    def node_shutdown(self, node_id: str) -> Dict[str, Any]:
        """Shutdown compute node (`POST /api/v1/nodes/[id]/shutdown`)."""
        target_id = self.resolve_node_id(node_id)
        response = self._client.post(f"/api/v1/nodes/{target_id}/shutdown")
        response.raise_for_status()
        return response.json()

    def node_reboot(self, node_id: str) -> Dict[str, Any]:
        """Reboot compute node (`POST /api/v1/nodes/[id]/reboot`)."""
        target_id = self.resolve_node_id(node_id)
        response = self._client.post(f"/api/v1/nodes/{target_id}/reboot")
        response.raise_for_status()
        return response.json()

    def node_boot(self, node_id: str) -> Dict[str, Any]:
        """Boot compute node (`PUT /api/v1/nodes/[id]/boot`)."""
        target_id = self.resolve_node_id(node_id)
        response = self._client.put(f"/api/v1/nodes/{target_id}/boot")
        response.raise_for_status()
        return response.json()





    # --- Developer Keys Endpoints ---

    def key_list(self, key_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List developer keys (`GET /api/v1/developer/keys`). Optionally filter by `key_type` (e.g. 'ssh_key' or 'api_key')."""
        response = self._client.get("/api/v1/developer/keys")
        response.raise_for_status()
        keys = response.json().get("keys", [])
        if key_type:
            return [k for k in keys if k.get("key_type") == key_type]
        return keys

    def key_create(
        self,
        name: str,
        key_type: str = "api_key",
        ssh_public_key: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a developer key (`POST /api/v1/developer/keys`)."""
        payload: Dict[str, Any] = {
            "name": name,
            "key_type": key_type,
        }
        if ssh_public_key:
            payload["ssh_public_key"] = ssh_public_key
        if permissions:
            payload["permissions"] = permissions
        response = self._client.post("/api/v1/developer/keys", json=payload)
        response.raise_for_status()
        return response.json()

    def key_delete(self, key_id: str) -> Dict[str, Any]:
        """Delete a developer key (`DELETE /api/v1/developer/keys/[id]`)."""
        response = self._client.delete(f"/api/v1/developer/keys/{key_id}")
        response.raise_for_status()
        return response.json()




