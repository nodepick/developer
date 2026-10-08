import time
import uuid
import logging
import httpx
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger("nodepick")

HOURS_PER_MONTH = 730

def _calculate_host_hourly_cost(
    host: Dict[str, Any], cpu: float = 1, memory_gb: float = 0.5, storage_gb: float = 10
) -> float:
    """Calculate the estimated hourly cost in USD for a compute slice on a host."""
    pricing = host.get("pricing") if isinstance(host.get("pricing"), dict) else {}
    vcpu_micros = pricing.get("vcpu_micros_per_hour", 0)
    ram_micros = pricing.get("ram_gib_micros_per_hour", 0)
    storage_micros = pricing.get("storage_gib_micros_per_hour", 0)
    total_micros = (cpu * vcpu_micros) + (memory_gb * ram_micros) + (storage_gb * storage_micros)
    return total_micros / 1_000_000.0

def _calculate_host_monthly_cost(
    host: Dict[str, Any], cpu: float = 1, memory_gb: float = 0.5, storage_gb: float = 10
) -> float:
    """Calculate the estimated monthly cost in USD (~730 hours/month) for a compute slice on a host."""
    return _calculate_host_hourly_cost(host, cpu, memory_gb, storage_gb) * HOURS_PER_MONTH

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
            raise ValueError("Node not found")
        nodes = self.node_list()
        for node in nodes:
            name = node.get("display_name") or node.get("displayName")
            vm_id = node.get("id") or node.get("vmId")
            vm_uuid = node.get("vm_uuid") or node.get("vmUuid")
            if identifier in (name, vm_id, vm_uuid):
                return vm_uuid or vm_id or identifier
        raise ValueError(f"Node not found: '{identifier}'")


    def find_compute(
        self,
        min_memory_gb: Optional[float] = None,
        min_cpu: Optional[int] = None,
        min_cpu_: Optional[int] = None,
        min_storage_gb: Optional[int] = None,
        max_price: Optional[float] = None,
        region: Optional[str] = None,
        datacenter: Optional[str] = None,
        status: str = "active",
        gpu: Optional[bool] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search and find compute hosts matching specific hardware, region, and pricing filters (`GET /api/v1/compute`)."""
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status
        effective_cpu = min_cpu if min_cpu is not None else min_cpu_
        if effective_cpu is not None:
            params["min_cpu"] = effective_cpu
        if min_memory_gb is not None:
            params["min_memory_gb"] = min_memory_gb
        if min_storage_gb is not None:
            params["min_storage_gb"] = min_storage_gb
        if region:
            params["region"] = region
        if datacenter:
            params["datacenter"] = datacenter
        if gpu is not None:
            params["gpu"] = "true" if gpu else "false"
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit

        response = self._client.get("/api/v1/compute", params=params)
        response.raise_for_status()
        data = response.json()
        hosts = data.get("hosts", []) if isinstance(data, dict) else []

        spec_cpu = float(effective_cpu or 1)
        spec_mem = float(min_memory_gb or 0.5)
        spec_disk = float(min_storage_gb or 10)

        for host in hosts:
            if isinstance(host, dict):
                hourly = _calculate_host_hourly_cost(
                    host, cpu=spec_cpu, memory_gb=spec_mem, storage_gb=spec_disk
                )
                host["estimated_hourly_cost_usd"] = hourly
                host["estimated_monthly_cost_usd"] = round(hourly * HOURS_PER_MONTH, 4)

        if max_price is not None:
            hosts = [
                h for h in hosts
                if h.get("estimated_monthly_cost_usd", float("inf")) <= max_price
            ]

        return hosts

    def list_regions(self) -> Dict[str, Any]:
        """List regions and hardware options (`GET /api/v1/nodes?view=regions`)."""
        response = self._client.get("/api/v1/nodes?view=regions")
        response.raise_for_status()
        return response.json()

    # --- VPC Networks Endpoints ---

    def resolve_vpc_id(self, vpc_identifier: Union[str, Dict[str, Any]]) -> str:
        """Resolve a VPC network ID from a UUID, name, or VPC dictionary."""
        if isinstance(vpc_identifier, dict):
            vid = vpc_identifier.get("id") or vpc_identifier.get("network_id")
            if vid:
                return str(vid)
            raise ValueError("VPC dictionary missing 'id'")

        if not vpc_identifier:
            raise ValueError("VPC identifier cannot be empty")

        ident = str(vpc_identifier).strip()
        try:
            uuid.UUID(ident)
            return ident
        except (ValueError, AttributeError):
            pass

        networks = self.vpc_list()
        for net in networks:
            if net.get("name") == ident or net.get("id") == ident:
                return str(net.get("id"))

        raise ValueError(f"VPC network not found: '{ident}'")

    def vpc_list(self) -> List[Dict[str, Any]]:
        """List organization VPC networks (`GET /api/v1/networking`)."""
        response = self._client.get("/api/v1/networking")
        response.raise_for_status()
        data = response.json()
        return data.get("networks", []) if isinstance(data, dict) else []

    def vpc_create(
        self,
        name: str,
        description: Optional[str] = None,
        region: Optional[str] = None,
        availability_zone: Optional[str] = None,
        subnet: Optional[str] = None,
        gateway: Optional[str] = None,
        enable_outbound_nat: bool = True,
    ) -> Dict[str, Any]:
        """Create a new VPC network (`POST /api/v1/networking`)."""
        payload: Dict[str, Any] = {
            "name": name,
            "enableOutboundNat": enable_outbound_nat,
        }
        if description is not None:
            payload["description"] = description
        if region is not None:
            payload["region"] = region
        if availability_zone is not None:
            payload["availabilityZone"] = availability_zone
        if subnet is not None:
            payload["subnet"] = subnet
        if gateway is not None:
            payload["gateway"] = gateway

        response = self._client.post("/api/v1/networking", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("network", data) if isinstance(data, dict) else data

    def vpc_get(self, vpc_id: str) -> Dict[str, Any]:
        """Get VPC network details (`GET /api/v1/networking/[id]`)."""
        resolved_id = self.resolve_vpc_id(vpc_id)
        response = self._client.get(f"/api/v1/networking/{resolved_id}")
        response.raise_for_status()
        data = response.json()
        return data.get("network", data) if isinstance(data, dict) else data

    def vpc_delete(self, vpc_id: str) -> Dict[str, Any]:
        """Delete an organization VPC network (`DELETE /api/v1/networking/[id]`)."""
        resolved_id = self.resolve_vpc_id(vpc_id)
        response = self._client.delete(f"/api/v1/networking/{resolved_id}")
        response.raise_for_status()
        return response.json()

    # --- Node Lifecycle Endpoints ---

    def node_create(
        self,
        memory: Optional[int] = 512 * 1024 * 1024,
        cpu: Optional[int] = 1,
        network_type: str = "private",
        display_name: Optional[str] = None,
        storage_gb: Optional[int] = None,
        region: Optional[str] = None,
        network_id: Optional[str] = None,
        vpc: Optional[Union[str, Dict[str, Any]]] = None,
        vpc_id: Optional[str] = None,
        system_id: Optional[str] = None,
        host_id: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Deploy a new compute node (`POST /api/v1/nodes`)."""
        payload: Dict[str, Any] = {
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

        # Resolve VPC network if specified
        target_vpc = network_id or vpc_id or vpc
        if target_vpc is not None:
            payload["networkId"] = self.resolve_vpc_id(target_vpc)

        # Resolve target host (pinned) or auto-discover smallest & cheapest host
        target_host = system_id or host_id
        if target_host is not None:
            payload["systemId"] = str(target_host)
        else:
            try:
                req_cpu = cpu or 1
                if memory and memory > 1024 * 1024:
                    req_mem_gb = memory / (1024 * 1024 * 1024)
                else:
                    req_mem_gb = float(memory or 0.5)
                req_storage_gb = storage_gb or 10

                candidates = self.find_compute(
                    min_cpu=req_cpu,
                    min_memory_gb=req_mem_gb,
                    min_storage_gb=req_storage_gb,
                    max_price=max_price,
                    region=region,
                    status="active",
                )

                if candidates:
                    def _rank_key(c: Dict[str, Any]):
                        price = c.get("estimated_monthly_cost_usd", float("inf"))
                        cores = c.get("cpu", {}).get("cores", 9999) if isinstance(c.get("cpu"), dict) else 9999
                        mem = c.get("memory_gb", 9999)
                        return (price, cores, mem)

                    best_host = min(candidates, key=_rank_key)
                    if best_host.get("id"):
                        payload["systemId"] = best_host["id"]
                        if not payload.get("region") and best_host.get("region"):
                            payload["region"] = best_host["region"]
            except Exception as e:
                logger.debug(f"Compute discovery auto-selection skipped: {e}")

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

    def node_attach_ip(self, node_id: str, ip: str = "auto") -> Dict[str, Any]:
        """Attach a public IP address (IPv4 or IPv6) to a node (`POST /api/v1/nodes/[id]/network/ip`)."""
        target_id = self.resolve_node_id(node_id)
        payload = {"ip": ip}
        response = self._client.post(f"/api/v1/nodes/{target_id}/network/ip", json=payload)
        response.raise_for_status()
        return response.json()

    def node_detach_ip(self, node_id: str, ip: Optional[str] = None) -> Dict[str, Any]:
        """Detach a public IP address from a node (`DELETE /api/v1/nodes/[id]/network/ip`)."""
        target_id = self.resolve_node_id(node_id)
        params = {"ip": ip} if ip else None
        response = self._client.delete(f"/api/v1/nodes/{target_id}/network/ip", params=params)
        response.raise_for_status()
        return response.json()

    # --- Developer SSH Keys Endpoints ---

    def key_list(self) -> List[Dict[str, Any]]:
        """List SSH public keys (`GET /api/v1/developer/keys`)."""
        response = self._client.get("/api/v1/developer/keys")
        response.raise_for_status()
        return response.json().get("keys", [])

    def key_create(
        self,
        name: str,
        public_key: str,
    ) -> Dict[str, Any]:
        """Register an SSH public key (`POST /api/v1/developer/keys`)."""
        payload: Dict[str, Any] = {
            "name": name,
            "public_key": public_key,
        }
        response = self._client.post("/api/v1/developer/keys", json=payload)
        response.raise_for_status()
        return response.json()

    def key_delete(self, key_id: str) -> Dict[str, Any]:
        """Delete an SSH key (`DELETE /api/v1/developer/keys/[id]`)."""
        response = self._client.delete(f"/api/v1/developer/keys/{key_id}")
        response.raise_for_status()
        return response.json()




