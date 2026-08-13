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

def key_list(key_type: Optional[str] = None) -> List[Dict[str, Any]]:
    return _get_default_client().key_list(key_type=key_type)

def key_create(
    name: str,
    key_type: str = "api_key",
    ssh_public_key: Optional[str] = None,
    permissions: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return _get_default_client().key_create(
        name=name, key_type=key_type, ssh_public_key=ssh_public_key, permissions=permissions
    )

def key_delete(key_id: str) -> Dict[str, Any]:
    return _get_default_client().key_delete(key_id)

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
    "key_list",
    "key_create",
    "key_delete",
]



