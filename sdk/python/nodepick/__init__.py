import sys
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("nodepick")
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)

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

def node_list() -> List[Dict[str, Any]]:
    return _get_default_client().node_list()

def node_create(
    memory: Optional[int] = 512 * 1024 * 1024,
    cpu: Optional[int] = 1,
    network_type: str = "private",
    display_name: Optional[str] = None,
    storage_gb: Optional[int] = None,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_default_client().node_create(
        memory=memory,
        cpu=cpu,
        network_type=network_type,
        display_name=display_name,
        storage_gb=storage_gb,
        region=region,
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

def ssh_list() -> List[Dict[str, Any]]:
    return _get_default_client().ssh_list()

def ssh_add(name: str, ssh_public_key: str) -> Dict[str, Any]:
    return _get_default_client().ssh_add(name=name, ssh_public_key=ssh_public_key)

def ssh_delete(key_id: str) -> Dict[str, Any]:
    return _get_default_client().ssh_delete(key_id)

# Backwards compatibility aliases
list_nodes = node_list
create_node = node_create
wait_for_nodes = node_wait
get_node_details = node_get_details
delete_node = node_delete
shutdown_node = node_shutdown
reboot_node = node_reboot
boot_node = node_boot

__all__ = [
    "NodePickClient",
    "NodepickMCPClient",
    "AgentLoop",
    "GeminiProvider",
    "AnthropicProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "node_list",
    "node_create",
    "node_wait",
    "node_get_details",
    "node_mcp",
    "node_delete",
    "node_shutdown",
    "node_reboot",
    "node_boot",
    "ssh_list",
    "ssh_add",
    "ssh_delete",
    "list_nodes",
    "create_node",
    "wait_for_nodes",
    "get_node_details",
    "delete_node",
    "shutdown_node",
    "reboot_node",
    "boot_node",
]



