import typer
from typing import Optional
from rich.console import Console
from rich.table import Table, Column
from .node import get_client
from ..core.exceptions import handle_error
from ..core.formatters import OutputFormat, set_output_format, print_output

console = Console()


def _render_compute_hosts_table(hosts):
    if not hosts:
        console.print("[yellow]No compute hosts found matching criteria.[/yellow]")
        return

    table = Table(
        Column("Host ID", no_wrap=True),
        "Status",
        "Region",
        "Datacenter",
        "RAM/Disk/CPU",
        "Price/hr ($)",
        "Price/mo ($)",
    )
    for host in hosts:
        # Show requested specs (RAM, CPU, and Disk) for which pricing was evaluated,
        # rather than the compute host's total reported capacity.
        req_cpu = host.get("requested_cpu")
        if req_cpu is None:
            cpu_info = host.get("cpu", {})
            req_cpu = cpu_info.get("cores") if isinstance(cpu_info, dict) else cpu_info

        req_mem = host.get("requested_memory_gb")
        if req_mem is None:
            req_mem = host.get("memory_gb")
        elif isinstance(req_mem, (int, float)) and req_mem == int(req_mem):
            req_mem = int(req_mem)

        req_disk = host.get("requested_storage_gb")
        if req_disk is None:
            req_disk = host.get("storage_gb")

        def _fmt(val):
            if val is None:
                return "?"
            if isinstance(val, (int, float)):
                return str(int(val)) if val == int(val) else str(val)
            return str(val)

        specs_str = f"{_fmt(req_mem)}/{_fmt(req_disk)}/{_fmt(req_cpu)}"

        pricing = host.get("pricing") if isinstance(host.get("pricing"), dict) else {}
        hourly = pricing.get("hourly") or pricing.get("hour") or host.get("estimated_hourly_cost_usd")
        monthly = pricing.get("monthly") or host.get("estimated_monthly_cost_usd")

        if hourly is not None:
            try:
                hourly_str = f"${float(hourly):.4f}"
            except (ValueError, TypeError):
                hourly_str = f"${hourly}"
        else:
            hourly_str = "N/A"

        if monthly is not None:
            try:
                monthly_str = f"${float(monthly):.2f}"
            except (ValueError, TypeError):
                monthly_str = f"${monthly}"
        else:
            monthly_str = "N/A"

        status_val = str(host.get("status") or "active")

        table.add_row(
            str(host.get("id") or "N/A"),
            status_val,
            str(host.get("region") or "N/A"),
            str(host.get("datacenter") or "N/A"),
            specs_str,
            hourly_str,
            monthly_str,
        )
    console.print(table)


def compute_command(
    cpu: Optional[int] = typer.Option(None, "--cpu", "-c", help="Minimum CPU cores"),
    memory_gb: Optional[float] = typer.Option(None, "--memory", "-m", help="Minimum RAM in GB"),
    storage_gb: Optional[int] = typer.Option(None, "--storage", "-s", help="Minimum storage in GB"),
    max_price: Optional[float] = typer.Option(None, "--max-price", "-p", help="Maximum monthly price in USD"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Filter by target region"),
    datacenter: Optional[str] = typer.Option(None, "--datacenter", help="Filter by datacenter facility code"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by host status (active, reservable, all)"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """Find and discover available compute hosts matching specific hardware and pricing criteria."""
    set_output_format(format)
    client = get_client()
    try:
        hosts = client.find_compute(
            min_cpu=cpu,
            min_memory_gb=memory_gb,
            min_storage_gb=storage_gb,
            max_price=max_price,
            region=region,
            datacenter=datacenter,
            status=status,
        )
        print_output(hosts, table_render_func=_render_compute_hosts_table)
    except Exception as e:
        handle_error(e, "Error finding compute hosts")
