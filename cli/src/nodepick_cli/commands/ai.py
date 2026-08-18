import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import typer
from rich.console import Console
from ..commands.node import get_client
from ..core.exceptions import handle_error

app = typer.Typer(name="ai", help="[BETA] Manage AI integrations and agent configurations.")
mcp_app = typer.Typer(name="mcp", help="Manage Model Context Protocol (MCP) integrations.")
app.add_typer(mcp_app, name="mcp")

console = Console()

SUPPORTED_AGENTS = ["antigravity"]


def _update_json_mcp_servers(file_path: Path, servers: Dict[str, Any]) -> None:
    """Safely merge MCP servers into a JSON configuration file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    data = json.loads(content)
        except Exception:
            data = {}

    if not isinstance(data, dict):
        data = {}

    if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
        data["mcpServers"] = {}

    data["mcpServers"].update(servers)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def configure_antigravity_mcp(servers: Dict[str, Any]) -> List[Path]:
    """Configure MCP servers for Google Antigravity across its standard configuration locations."""
    home = Path.home()
    target_files = [
        home / ".gemini" / "config" / "mcp_config.json",
        home / ".gemini" / "settings.json",
        home / ".gemini" / "antigravity-cli" / "settings.json",
    ]
    updated_files = []
    for path in target_files:
        try:
            _update_json_mcp_servers(path, servers)
            updated_files.append(path)
        except Exception as e:
            console.print(f"[dim yellow]Warning: Failed writing to {path}: {e}[/dim yellow]")
    return updated_files


@mcp_app.command("configure")
def mcp_configure(
    agent: str = typer.Argument(
        ...,
        help=f"AI Agent to configure (supported: {', '.join(SUPPORTED_AGENTS)})",
    ),
    nodes: Optional[List[str]] = typer.Argument(
        None, help="Node IDs or display names to configure MCP for (if omitted, configures all nodes)"
    ),
):
    """Configure MCP servers for an AI agent (e.g. antigravity) to connect to compute nodes."""
    agent_clean = agent.strip().lower()
    if agent_clean not in ("antigravity", "agy", "gemini"):
        console.print(
            f"[bold red]Unsupported agent '{agent}'.[/bold red] Supported agents: [bold]"
            + ", ".join(SUPPORTED_AGENTS)
            + "[/bold]"
        )
        raise typer.Exit(1)

    client = get_client()

    try:
        if nodes:
            target_nodes = list(nodes)
        else:
            all_nodes = client.node_list()
            if not all_nodes:
                console.print("[yellow]No compute nodes found to configure.[/yellow]")
                return
            target_nodes = [
                node.get("vm_uuid") or node.get("id") or node.get("display_name")
                for node in all_nodes
            ]
            target_nodes = [n for n in target_nodes if n]

        servers_to_add: Dict[str, Any] = {}

        for node_identifier in target_nodes:
            try:
                details = client.node_get_details(node_identifier)
            except Exception as e:
                handle_error(e, f"Failed to get details for node '{node_identifier}'")
                continue

            connect = details.get("connect") or {}
            if not connect and "vm" in details and isinstance(details["vm"], dict):
                connect = details["vm"].get("connect") or {}

            mcp_url = connect.get("mcpUrl") or details.get("mcpUrl") or details.get("nmcpUrl")
            mcp_api_key = connect.get("mcpApiKey") or details.get("mcpApiKey")

            node_name = (
                details.get("display_name")
                or details.get("displayName")
                or details.get("name")
                or details.get("vm_uuid")
                or details.get("id")
                or node_identifier
            )

            if not mcp_url:
                console.print(
                    f"[yellow]Node '{node_name}' does not have an active MCP endpoint ('mcpUrl'). Skipping.[/yellow]"
                )
                continue

            server_config: Dict[str, Any] = {
                "serverUrl": mcp_url,
                "url": mcp_url,
                "type": "http",
                "transport": "http",
                "protocol": "streamable_http",
                "insecure": True,
                "insecureSkipVerify": True,
                "rejectUnauthorized": False,
                "verify": False,
                "tls": {
                    "insecure": True,
                    "insecureSkipVerify": True,
                },
            }
            if mcp_api_key:
                server_config["headers"] = {
                    "Authorization": f"Bearer {mcp_api_key}",
                    "X-API-Key": mcp_api_key,
                }

            servers_to_add[node_name] = server_config

        if not servers_to_add:
            console.print("[yellow]No active MCP servers found for the specified node(s).[/yellow]")
            return

        if agent_clean in ("antigravity", "agy", "gemini"):
            configure_antigravity_mcp(servers_to_add)

        for s_name, s_cfg in servers_to_add.items():
            console.print(
                f"[bold green]✔[/bold green] Configured MCP server '[bold]{s_name}[/bold]' -> [cyan]{s_cfg['url']}[/cyan]"
            )

        console.print(
            f"[bold green]Successfully configured {len(servers_to_add)} MCP server(s) for {agent_clean}.[/bold green]"
        )

    except Exception as e:
        handle_error(e, "Error configuring MCP servers")
