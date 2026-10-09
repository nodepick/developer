import typer
import typer.core
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table, Column
import nodepick
from ..core.config import get_api_key, get_base_url
from ..core.exceptions import handle_error
from ..core.formatters import OutputFormat, set_output_format, get_output_format, print_output


class NodeTyperGroup(typer.core.TyperGroup):
    """Custom TyperGroup allowing both 'np node <action> <node_id>' and 'np node <node_id> <action>'."""
    def parse_args(self, ctx, args):
        actions = {
            "attach-ip", "detach-ip",
            "boot", "reboot", "shutdown", "delete", "get"
        }
        if len(args) >= 2 and args[1] in actions and args[0] not in self.commands:
            args = [args[1], args[0]] + list(args[2:])
        return super().parse_args(ctx, args)


app = typer.Typer(cls=NodeTyperGroup, name="node", help="Manage Compute Nodes.")
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


from .regions import validate_region, _render_regions_table


@app.command("create")
def node_create(
    display_name: Optional[str] = typer.Option(None, "--name", "-n", help="Display name for the node"),
    cpu: int = typer.Option(1, "--cpu", "-c", min=1, help="Number of vCPUs (min: 1)"),
    memory: int = typer.Option(1, "--memory", "-m", min=1, help="Memory size in GB (min: 1, default: 1)"),
    storage_gb: Optional[int] = typer.Option(None, "--storage", min=10, help="Disk storage in GB (min: 10, default: 10)"),
    vpc: Optional[str] = typer.Option(None, "--vpc", help="VPC network ID or name to deploy node into"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Target geographic region (e.g. us-west-1, fmt1)"),
    host_id: Optional[str] = typer.Option(None, "--host", "--host-id", "--system-id", help="Target Host ID to deploy onto"),
):
    """Deploy a new compute node."""
    client = get_client()
    if region:
        validate_region(client, region)
    try:
        console.print("[cyan]Creating node...[/cyan]")
        node = client.node_create(
            memory=memory,
            cpu=cpu,
            display_name=display_name,
            storage_gb=storage_gb,
            vpc=vpc,
            region=region,
            host_id=host_id,
        )
        node_id = node.get("vm_uuid") or node.get("id")
        console.print(f"[bold green]Node created successfully![/bold green] ID: {node_id}")
    except Exception as e:
        handle_error(e, "Error creating node")


@app.command("attach-ip")
def node_attach_ip(
    node_id: str = typer.Argument(..., help="Node ID or display name"),
    ip: str = typer.Option(
        "auto",
        "--ip",
        help="Public IP address to attach (IPv4 or IPv6), or 'auto' (IPv4) / 'auto-ipv6' (IPv6)",
    ),
):
    """Attach a public IP address (IPv4 or IPv6) to a compute node."""
    client = get_client()
    target_ip = ip
    if isinstance(target_ip, str):
        cleaned = target_ip.strip().lower()
        if cleaned in ("auto-ipv6", "ipv6", "v6", "6"):
            target_ip = "auto-ipv6"
        elif cleaned in ("auto-ipv4", "ipv4", "v4", "4"):
            target_ip = "auto"

    is_v6_target = target_ip == "auto-ipv6" or ":" in target_ip
    ver_target = "IPv6" if is_v6_target else "IPv4"
    try:
        console.print(f"[cyan]Attaching public {ver_target} to node {node_id}...[/cyan]")
        res = client.node_attach_ip(node_id, ip=target_ip)
        assigned_ip = res.get("ip") or "assigned"
        is_v6_res = res.get("ipVersion") == 6 or ":" in str(assigned_ip)
        ver_res = "IPv6" if is_v6_res else "IPv4"
        console.print(f"[bold green]Public {ver_res} attached to node {node_id}:[/bold green] [cyan]{assigned_ip}[/cyan]")
    except Exception as e:
        handle_error(e, f"Error attaching public {ver_target}")


@app.command("detach-ip")
def node_detach_ip(
    node_id: str = typer.Argument(..., help="Node ID or display name"),
    ip: Optional[str] = typer.Option(None, "--ip", help="Specific public IP address to detach (auto-detected if omitted)"),
    ipv6: bool = typer.Option(False, "--ipv6", "-6", help="Detach public IPv6 address"),
):
    """Detach a public IP address (IPv4 or IPv6) from a compute node."""
    client = get_client()
    target_ip = ip
    if not target_ip and ipv6:
        try:
            details = client.node_get_details(node_id)
            connect = details.get("connect") or {}
            candidate = connect.get("publicIpv6") or connect.get("ipv6")
            if candidate:
                target_ip = candidate
        except Exception:
            pass
    elif not target_ip:
        try:
            details = client.node_get_details(node_id)
            connect = details.get("connect") or {}
            pub4 = connect.get("publicIp")
            pub6 = connect.get("publicIpv6") or connect.get("ipv6")
            if pub6 and not pub4:
                target_ip = pub6
            elif pub4:
                target_ip = pub4
        except Exception:
            pass

    is_v6 = (":" in target_ip) if target_ip else ipv6
    ver_label = "IPv6" if is_v6 else "IPv4"
    try:
        console.print(f"[cyan]Detaching public {ver_label} from node {node_id}...[/cyan]")
        res = client.node_detach_ip(node_id, ip=target_ip)
        console.print(f"[bold green]Public {ver_label} detached from node {node_id}.[/bold green]")
    except Exception as e:
        handle_error(e, f"Error detaching public {ver_label}")


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








