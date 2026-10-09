import sys
import logging
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger("nodepick")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)

__version__ = "0.1.4"

from .client import NodePickClient
from .mcp import NodepickMCPClient
from .llm import (
    AgentLoop,
    GeminiProvider,
    AnthropicProvider,
    OpenAIProvider,
    OllamaProvider,
)


_default_client: Optional[NodePickClient] = None

def _get_default_client() -> NodePickClient:
    global _default_client
    if _default_client is None:
        _default_client = NodePickClient()
    return _default_client

def find_compute(
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
    return _get_default_client().find_compute(
        min_memory_gb=min_memory_gb,
        min_cpu=min_cpu,
        min_cpu_=min_cpu_,
        min_storage_gb=min_storage_gb,
        max_price=max_price,
        region=region,
        datacenter=datacenter,
        status=status,
        gpu=gpu,
        page=page,
        limit=limit,
    )

def list_regions() -> Dict[str, Any]:
    return _get_default_client().list_regions()

def get_available_regions(status: Optional[str] = None) -> List[Dict[str, Any]]:
    return _get_default_client().get_available_regions(status=status)

def vpc_list() -> List[Dict[str, Any]]:
    return _get_default_client().vpc_list()

def vpc_create(
    name: str,
    region: Optional[str] = None,
    description: Optional[str] = None,
    for_provision: Optional[bool] = None,
) -> Dict[str, Any]:
    return _get_default_client().vpc_create(
        name=name,
        region=region,
        description=description,
        for_provision=for_provision,
    )

def vpc_get(vpc_id: str) -> Dict[str, Any]:
    return _get_default_client().vpc_get(vpc_id)

def vpc_delete(vpc_id: str) -> Dict[str, Any]:
    return _get_default_client().vpc_delete(vpc_id)

def node_list() -> List[Dict[str, Any]]:
    return _get_default_client().node_list()

def node_create(
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
    return _get_default_client().node_create(
        memory=memory,
        cpu=cpu,
        network_type=network_type,
        display_name=display_name,
        storage_gb=storage_gb,
        region=region,
        network_id=network_id,
        vpc=vpc,
        vpc_id=vpc_id,
        system_id=system_id,
        host_id=host_id,
        max_price=max_price,
    )

def node_wait(node_ids: List[str], delay: float = 1.0):
    return _get_default_client().node_wait(node_ids, delay=delay)

def node_get_details(node_id: str) -> Dict[str, Any]:
    return _get_default_client().node_get_details(node_id)

def node_mcp(node_id: str) -> NodepickMCPClient:
    return _get_default_client().mcp(node_id)

def node_delete(node_id: str) -> Dict[str, Any]:
    return _get_default_client().node_delete(node_id)

def node_shutdown(node_id: str) -> Dict[str, Any]:
    return _get_default_client().node_shutdown(node_id)

def node_reboot(node_id: str) -> Dict[str, Any]:
    return _get_default_client().node_reboot(node_id)

def node_boot(node_id: str) -> Dict[str, Any]:
    return _get_default_client().node_boot(node_id)

def node_attach_ip(node_id: str, ip: str = "auto", version: Optional[int] = None) -> Dict[str, Any]:
    return _get_default_client().node_attach_ip(node_id, ip=ip, version=version)

def node_detach_ip(node_id: str, ip: Optional[str] = None, version: Optional[int] = None) -> Dict[str, Any]:
    return _get_default_client().node_detach_ip(node_id, ip=ip, version=version)

attach_ip = node_attach_ip
detach_ip = node_detach_ip

def key_list() -> List[Dict[str, Any]]:
    return _get_default_client().key_list()

def key_create(
    name: str,
    public_key: str,
) -> Dict[str, Any]:
    return _get_default_client().key_create(
        name=name,
        public_key=public_key,
    )

def key_delete(key_id: str) -> Dict[str, Any]:
    return _get_default_client().key_delete(key_id)

__all__ = [
    "__version__",
    "NodePickClient",
    "NodepickMCPClient",
    "AgentLoop",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "find_compute",
    "list_regions",
    "get_available_regions",
    "vpc_list",
    "vpc_create",
    "vpc_get",
    "vpc_delete",
    "node_list",
    "node_create",
    "node_wait",
    "node_get_details",
    "node_mcp",
    "node_delete",
    "node_shutdown",
    "node_reboot",
    "node_boot",
    "node_attach_ip",
    "node_detach_ip",
    "attach_ip",
    "detach_ip",
    "key_list",
    "key_create",
    "key_delete",
]



