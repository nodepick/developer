import typer
from typing import Optional
from rich.console import Console
from rich.table import Table, Column
import nodepick
from ..core.config import get_api_key, get_base_url
from ..core.exceptions import handle_error
from ..core.formatters import OutputFormat, set_output_format, get_output_format, print_output



app = typer.Typer(name="node", help="Manage Compute Nodes.")
console = Console()

from click.core import ParameterSource

@app.callback(invoke_without_command=True)
def node_callback():
    pass


def get_client() -> nodepick.NodePickClient:
    key = get_api_key()
    url = get_base_url()
    if not key:
        console.print(
            "[yellow]No API key found.[/yellow] "
            "Run [bold]np auth configure[/bold] to store your API key."
        )
        raise typer.Exit(1)
    return nodepick.NodePickClient(api_key=key, base_url=url)

def _extract_ssh_command(details) -> str:
    ssh = ((details or {}).get("connect") or {}).get("ssh") or {}
    cmd = ssh.get("command")
    if cmd:
        return cmd
    host = ssh.get("sshHost")
    port = ssh.get("sshPort")
    username = ssh.get("username", "nodepick")
    if host and port:
        return f"ssh {username}@{host} -p {port}"
    return "N/A"

def _get_ssh_command(client, node) -> str:
    node_id = node.get("vm_uuid") or node.get("vmUuid") or node.get("vmId") or node.get("id")
    try:
        details = client.node_get_details(node_id)
        return _extract_ssh_command(details)
    except Exception:
        return "N/A"

def _render_nodes_table(nodes, client=None):
    if not nodes:
        console.print("[yellow]No nodes found.[/yellow]")
        return

    table = Table("ID", "Name", "State", Column("SSH Connect", no_wrap=True))
    for node in nodes:
        node_id = node.get("vm_uuid") or node.get("vmUuid") or node.get("vmId") or node.get("id", "N/A")
        name = node.get("display_name") or node.get("displayName") or "N/A"
        vmm = node.get("vmm", {}) if isinstance(node.get("vmm"), dict) else {}
        state = node.get("state") or vmm.get("state") or node.get("status", "unknown")
        ssh_cmd = _get_ssh_command(client, node) if client else "N/A"
        table.add_row(
            str(node_id),
            str(name),
            str(state),
            ssh_cmd,
        )
    console.print(table)

@app.command("boot")
def node_boot(
    node_id: str = typer.Argument(..., help="Node ID or display name to boot"),
):
    """Boot a node."""
    client = get_client()
    try:
        console.print(f"[cyan]Booting node {node_id}...[/cyan]")
        res = client.node_boot(node_id)
        console.print(f"[bold green]Node {node_id} boot request sent.[/bold green]")
    except Exception as e:
        handle_error(e, "Error booting node")


@app.command("create")
def node_create(
    display_name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name for the node"),
    cpu: int = typer.Option(1, "--cpu", "-c", help="Number of vCPUs"),
    memory_mb: int = typer.Option(512, "--memory", "-m", help="Memory size in MB"),
    network_type: str = typer.Option("private", "--network", help="Network type (private/public)"),
    storage_gb: Optional[int] = typer.Option(None, "--storage", help="Disk storage in GB (default: 10)"),
):
    """Deploy a new compute node."""
    client = get_client()
    memory_bytes = memory_mb * 1024 * 1024
    try:
        console.print("[cyan]Creating node...[/cyan]")
        node = client.node_create(
            memory=memory_bytes,
            cpu=cpu,
            network_type=network_type,
            display_name=display_name,
            storage_gb=storage_gb,
        )
        node_id = node.get("vm_uuid")
        console.print(f"[bold green]Node created successfully![/bold green] ID: {node_id}")
    except Exception as e:
        handle_error(e, "Error creating node")


@app.command("delete")
def node_delete(
    node_id: str = typer.Argument(..., help="Node ID or display name to delete"),
):
    """Delete a compute node."""
    client = get_client()
    try:
        console.print(f"[cyan]Deleting node {node_id}...[/cyan]")
        res = client.node_delete(node_id)
        console.print(f"[bold green]Node {node_id} deleted.[/bold green]")
    except Exception as e:
        handle_error(e, "Error deleting node")


def _render_node_details_table(node):
    if not node:
        console.print("[yellow]No node details found.[/yellow]")
        return

    table = Table("Field", "Value")
    fields = [
        ("ID", node.get("vm_uuid") or node.get("id")),
        ("Org ID", node.get("orgId") or node.get("org_id")),
        ("User ID", node.get("created_by_id")),
        ("Server ID", node.get("serverId") or node.get("server_id")),
        ("Name", node.get("display_name")),
        ("State", node.get("state")),
        ("Status", node.get("status")),
        ("SSH Connect", _extract_ssh_command(node)),
        ("CPU Cores", node.get("cpu")),
        (
            "Memory (MB)",
            round(node.get("memory_bytes") / (1024 * 1024))
            if node.get("memory_bytes") is not None
            else node.get("memory_mb"),
        ),
        (
            "Storage (GB)",
            round(node.get("storage_bytes") / (1024 * 1024 * 1024))
            if node.get("storage_bytes") is not None
            else node.get("storage_gb"),
        ),
        ("Region", node.get("region")),
    ]
    for field, value in fields:
        if value is not None:
            table.add_row(field, str(value))
    console.print(table)


@app.command("get")
def node_get(
    node_id: str = typer.Argument(..., help="Node ID or display name"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """Get details of a specific node."""
    set_output_format(format)
    client = get_client()
    try:
        details = client.node_get_details(node_id)
        print_output(details, table_render_func=_render_node_details_table)
    except Exception as e:
        handle_error(e, "Error getting node details")


@app.command("list")
def node_list(
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """List all compute nodes."""
    set_output_format(format)
    client = get_client()
    try:
        nodes = client.node_list()
        print_output(nodes, table_render_func=lambda data: _render_nodes_table(data, client))
    except Exception as e:
        handle_error(e, "Error listing nodes")


@app.command("reboot")
def node_reboot(
    node_id: str = typer.Argument(..., help="Node ID or display name to reboot"),
):
    """Reboot a node."""
    client = get_client()
    try:
        console.print(f"[cyan]Rebooting node {node_id}...[/cyan]")
        res = client.node_reboot(node_id)
        console.print(f"[bold green]Node {node_id} reboot request sent.[/bold green]")
    except Exception as e:
        handle_error(e, "Error rebooting node")


@app.command("shutdown")
def node_shutdown(
    node_id: str = typer.Argument(..., help="Node ID or display name to shut down"),
):
    """Gracefully shut down a node."""
    client = get_client()
    try:
        console.print(f"[cyan]Shutting down node {node_id}...[/cyan]")
        res = client.node_shutdown(node_id)
        console.print(f"[bold green]Node {node_id} shutdown request sent.[/bold green]")
    except Exception as e:
        handle_error(e, "Error shutting down node")








