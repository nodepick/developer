import time
import uuid
import logging
import httpx
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger("nodepick")

HOURS_PER_MONTH = 730


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

def _normalize_memory_gb(memory: Optional[Union[int, float]]) -> float:
    if memory is None:
        return 1.0
    if memory > 1024 * 1024:
        return memory / (1024 * 1024 * 1024)
    if memory > 128:
        return memory / 1024.0
    return float(memory)

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
        status: Optional[str] = None,
        gpu: Optional[bool] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Search and find compute hosts matching specific hardware, region, and pricing filters (`GET /api/v1/compute`)."""
        params: Dict[str, Any] = {}
        effective_cpu = min_cpu if min_cpu is not None else min_cpu_
        req_cpu = max(int(effective_cpu if effective_cpu is not None else 1), 1)
        req_mem = max(float(min_memory_gb if min_memory_gb is not None else 1.0), 1.0)
        req_disk = max(int(min_storage_gb if min_storage_gb is not None else 10), 10)

        params: Dict[str, Any] = {
            "min_cpu": req_cpu,
            "min_memory_gb": int(req_mem) if req_mem == int(req_mem) else req_mem,
            "min_storage_gb": req_disk,
        }
        if status:
            params["status"] = status
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

        for host in hosts:
            if isinstance(host, dict):
                # Preserve host reported capacity
                host["capacity_cpu_cores"] = host.get("cpu", {}).get("cores") if isinstance(host.get("cpu"), dict) else host.get("cpu")
                host["capacity_memory_gb"] = host.get("memory_gb")
                host["capacity_storage_gb"] = host.get("storage_gb")

                # Store requested specs for which pricing was evaluated
                host["requested_cpu"] = req_cpu
                host["requested_memory_gb"] = req_mem
                host["requested_storage_gb"] = req_disk

                pricing = host.get("pricing") if isinstance(host.get("pricing"), dict) else {}
                hourly_raw = pricing.get("hourly") or pricing.get("hour")
                monthly_raw = pricing.get("monthly")

                # Convenience float properties mapped directly from upstream pricing
                if hourly_raw is not None:
                    try:
                        host["estimated_hourly_cost_usd"] = float(hourly_raw)
                    except (ValueError, TypeError):
                        pass
                if monthly_raw is not None:
                    try:
                        host["estimated_monthly_cost_usd"] = float(monthly_raw)
                    except (ValueError, TypeError):
                        pass

        if max_price is not None:
            def _get_monthly_cost(h: Dict[str, Any]) -> float:
                pricing = h.get("pricing") if isinstance(h.get("pricing"), dict) else {}
                monthly = pricing.get("monthly") or h.get("estimated_monthly_cost_usd")
                if monthly is not None:
                    try:
                        return float(monthly)
                    except (ValueError, TypeError):
                        pass
                return float("inf")

            hosts = [h for h in hosts if _get_monthly_cost(h) <= max_price]

        return hosts

    def list_regions(self) -> Dict[str, Any]:
        """List regions and hardware options (`GET /api/v1/nodes?view=regions`)."""
        response = self._client.get("/api/v1/nodes?view=regions")
        response.raise_for_status()
        return response.json()

    def get_available_regions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available compute regions with status 'active' or 'reservable' (`GET /api/v1/regions`)."""
        params = {}
        if status:
            params["status"] = status
        response = self._client.get("/api/v1/regions", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("regions", []) if isinstance(data, dict) else []

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

    def _validate_region(self, region: str) -> None:
        """Validate region against available regions if regions are returned by the API."""
        if not region:
            return
        try:
            regions = self.get_available_regions()
            if isinstance(regions, list) and len(regions) > 0:
                valid_ids = set()
                for r in regions:
                    if isinstance(r, dict):
                        if r.get("id"):
                            valid_ids.add(str(r["id"]).lower())
                        for dc in r.get("datacenters") or []:
                            valid_ids.add(str(dc).lower())
                if valid_ids and region.lower() not in valid_ids:
                    sorted_ids = sorted(list({str(r.get("id")) for r in regions if isinstance(r, dict) and r.get("id")}))
                    raise ValueError(
                        f"Unsupported region '{region}'. Supported regions are: {', '.join(sorted_ids)}"
                    )
        except ValueError:
            raise
        except Exception as e:
            logger.debug(f"Region validation check skipped: {e}")

    def vpc_create(
        self,
        name: str,
        region: Optional[str] = None,
        description: Optional[str] = None,
        for_provision: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Create a new VPC network (`POST /api/v1/networking`)."""
        payload: Dict[str, Any] = {
            "name": name,
        }
        if region is not None:
            self._validate_region(region)
            payload["region"] = region
        if description is not None:
            payload["description"] = description
        if for_provision is not None:
            payload["forProvision"] = for_provision

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
        memory: Optional[int] = 1,
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
        # Enforce minimum requirements: 1 GB RAM, 1 vCPU, 10 GB Disk
        effective_mem_gb = _normalize_memory_gb(memory) if memory is not None else 1.0
        if effective_mem_gb < 1.0:
            raise ValueError(f"Memory must be at least 1 GB (got {memory})")

        if cpu is not None and cpu < 1:
            raise ValueError(f"CPU must be at least 1 vCPU (got {cpu})")

        if storage_gb is not None and storage_gb < 10:
            raise ValueError(f"Storage must be at least 10 GB (got {storage_gb})")

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
            self._validate_region(region)
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
                req_cpu = max(cpu or 1, 1)
                req_mem_gb = max(effective_mem_gb, 1.0)
                req_storage_gb = max(storage_gb or 10, 10)

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
                        pricing = c.get("pricing") if isinstance(c.get("pricing"), dict) else {}
                        monthly_val = pricing.get("monthly") or c.get("estimated_monthly_cost_usd")
                        try:
                            price = float(monthly_val) if monthly_val is not None else float("inf")
                        except (ValueError, TypeError):
                            price = float("inf")
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

    def node_attach_ip(
        self,
        node_id: str,
        ip: str = "auto",
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Attach a public IP address (IPv4 or IPv6) to a node (`POST /api/v1/nodes/[id]/network/ip`)."""
        target_id = self.resolve_node_id(node_id)
        target_ip = ip
        if version == 6:
            if target_ip in ("auto", "auto-ipv4"):
                target_ip = "auto-ipv6"
        elif version == 4:
            if target_ip == "auto-ipv6":
                target_ip = "auto"
        elif isinstance(target_ip, str):
            cleaned = target_ip.strip().lower()
            if cleaned in ("auto-ipv6", "ipv6", "v6", "6"):
                target_ip = "auto-ipv6"
            elif cleaned in ("auto-ipv4", "ipv4", "v4", "4"):
                target_ip = "auto"

        payload = {"ip": target_ip}
        response = self._client.post(f"/api/v1/nodes/{target_id}/network/ip", json=payload)
        response.raise_for_status()
        return response.json()

    attach_ip = node_attach_ip

    def node_detach_ip(
        self,
        node_id: str,
        ip: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Detach a public IP address from a node (`DELETE /api/v1/nodes/[id]/network/ip`)."""
        target_id = self.resolve_node_id(node_id)
        target_ip = ip
        if target_ip is None and version == 6:
            try:
                details = self.node_get_details(target_id)
                connect = details.get("connect") or {}
                candidate = connect.get("publicIpv6") or connect.get("ipv6")
                if candidate:
                    target_ip = candidate
            except Exception:
                pass
        elif isinstance(target_ip, str) and target_ip.strip().lower() in ("ipv6", "v6", "auto-ipv6", "6"):
            try:
                details = self.node_get_details(target_id)
                connect = details.get("connect") or {}
                candidate = connect.get("publicIpv6") or connect.get("ipv6")
                if candidate:
                    target_ip = candidate
            except Exception:
                pass

        params = {"ip": target_ip} if target_ip else None
        response = self._client.delete(f"/api/v1/nodes/{target_id}/network/ip", params=params)
        response.raise_for_status()
        return response.json()

    detach_ip = node_detach_ip

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




