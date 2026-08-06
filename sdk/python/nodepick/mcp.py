import ssl
import logging
import httpx
from typing import Optional, List, Dict, Any
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from .client import _async_log_request, _async_log_response

def create_pq_ssl_context() -> ssl.SSLContext:
    """Create a client-side SSLContext enforcing TLS 1.3 and Post-Quantum hybrid groups."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    
    pq_groups = ["x25519_mlkem768", "X25519MLKEM768", "x25519_kyber768"]
    for group in pq_groups:
        try:
            ctx.set_groups([group])
            break
        except Exception:
            continue
    return ctx

class NodepickMCPClient:
    def __init__(self, node_details: Dict[str, Any]):
        connect = (node_details or {}).get("connect") or {}
        self.url = connect.get("nmcpUrl")
        self.api_key = connect.get("nmcpApiKey") or connect.get("nmcpdApiKey")
        if not self.url or not self.api_key:
            raise ValueError("Node details do not contain a valid MCP endpoint ('nmcpUrl') or API key ('nmcpApiKey').")

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers



    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools exposed by the VM's MCP server."""
        ssl_ctx = create_pq_ssl_context()
        headers = self._get_headers()
        
        async with httpx.AsyncClient(
            headers=headers,
            verify=ssl_ctx,
            event_hooks={
                "request": [_async_log_request],
                "response": [_async_log_response],
            }
        ) as http_client:
            async with streamable_http_client(self.url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    
                    tools_list = []
                    for tool in tools_result.tools:
                        tools_list.append({
                            "name": tool.name,
                            "description": tool.description,
                            "input_schema": tool.input_schema,
                        })
                    return tools_list

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific MCP tool on the guest VM."""
        ssl_ctx = create_pq_ssl_context()
        headers = self._get_headers()
        
        async with httpx.AsyncClient(
            headers=headers,
            verify=ssl_ctx,
            event_hooks={
                "request": [_async_log_request],
                "response": [_async_log_response],
            }
        ) as http_client:

            async with streamable_http_client(self.url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    
                    content_list = []
                    for content in result.content:
                        content_dict = {"type": content.type}
                        if content.type == "text":
                            content_dict["text"] = content.text
                        elif content.type == "image":
                            content_dict["data"] = content.data
                            content_dict["mime_type"] = content.mime_type
                        content_list.append(content_dict)
                        
                    return {
                        "is_error": result.isError,
                        "content": content_list
                    }

