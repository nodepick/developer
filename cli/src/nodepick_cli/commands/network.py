import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from ..commands.regions import validate_region
from ..commands.node import get_client
from ..core.exceptions import handle_error
from ..core.formatters import OutputFormat, set_output_format, print_output

app = typer.Typer(name="network", help="Manage VPC Networks.")
console = Console()


def _render_networks_table(networks):
    if not networks:
        console.print("[yellow]No VPC networks found.[/yellow]")
        return

    table = Table("ID", "Name", "Subnet", "Region")
    for net in networks:
        table.add_row(
            str(net.get("id") or "N/A"),
            str(net.get("name") or "N/A"),
            str(net.get("subnet") or "N/A"),
            str(net.get("region") or "-"),
        )
    console.print(table)


def _render_network_details_table(network):
    if not network:
        console.print("[yellow]No VPC network details found.[/yellow]")
        return

    table = Table("Field", "Value")
    fields = [
        ("ID", network.get("id")),
        ("Name", network.get("name")),
        ("Description", network.get("description")),
        ("Subnet", network.get("subnet")),
        ("Gateway", network.get("gateway")),
        ("Region", network.get("region")),
        ("VNI", network.get("vni")),
        ("Outbound NAT", "Enabled" if network.get("enableOutboundNat", True) else "Disabled"),
        ("Created At", network.get("createdAt") or network.get("created_at")),
    ]
    for field, value in fields:
        if value is not None:
            table.add_row(field, str(value))
    console.print(table)


@app.command("list")
def network_list(
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """List organization VPC networks."""
    set_output_format(format)
    client = get_client()
    try:
        networks = client.vpc_list()
        print_output(networks, table_render_func=_render_networks_table)
    except Exception as e:
        handle_error(e, "Error listing VPC networks")


@app.command("create")
def network_create(
    name: str = typer.Argument(..., help="Name for the VPC network (alphanumeric, dashes, and underscores)"),
    region: str = typer.Option(..., "--region", "-r", help="Target geographic region (e.g. us-west-1)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Optional description"),
):
    """Create a new VPC network."""
    client = get_client()
    if region:
        validate_region(client, region)
    try:
        console.print(f"[cyan]Creating VPC network '{name}'...[/cyan]")
        network = client.vpc_create(
            name=name,
            region=region,
            description=description,
        )
        vpc_id = network.get("id")
        console.print(f"[bold green]VPC network created successfully![/bold green] ID: {vpc_id}")
    except Exception as e:
        handle_error(e, "Error creating VPC network")


@app.command("get")
def network_get(
    vpc_id: str = typer.Argument(..., help="VPC Network ID or name"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """Get details of a specific VPC network."""
    set_output_format(format)
    client = get_client()
    try:
        network = client.vpc_get(vpc_id)
        print_output(network, table_render_func=_render_network_details_table)
    except Exception as e:
        handle_error(e, "Error getting VPC network details")


@app.command("delete")
def network_delete(
    vpc_id: str = typer.Argument(..., help="VPC Network ID or name to delete"),
):
    """Delete an organization VPC network."""
    client = get_client()
    try:
        console.print(f"[cyan]Deleting VPC network {vpc_id}...[/cyan]")
        res = client.vpc_delete(vpc_id)
        console.print(f"[bold green]VPC network {vpc_id} deleted.[/bold green]")
    except Exception as e:
        handle_error(e, "Error deleting VPC network")
