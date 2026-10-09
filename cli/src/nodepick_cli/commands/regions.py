import typer
from rich.console import Console
from rich.table import Table
from typing import Optional
import nodepick
from nodepick_cli.core.config import get_api_key, get_base_url
from nodepick_cli.core.formatters import OutputFormat, set_output_format, print_output
from nodepick_cli.core.exceptions import handle_error

console = Console()


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


def validate_region(client, region: Optional[str]) -> None:
    """Validate that region is among available regions if regions are returned by the API."""
    if not region:
        return
    try:
        raw_regions = client.get_available_regions()
        if isinstance(raw_regions, list) and len(raw_regions) > 0:
            supported = set()
            for r in raw_regions:
                if isinstance(r, dict):
                    if r.get("id"):
                        supported.add(str(r["id"]).lower())
                    for dc in r.get("datacenters") or []:
                        supported.add(str(dc).lower())
            if supported and region.lower() not in supported:
                sorted_ids = sorted(list({str(r.get("id")) for r in raw_regions if isinstance(r, dict) and r.get("id")}))
                raise typer.BadParameter(
                    f"Unsupported region '{region}'. Supported regions are: {', '.join(sorted_ids)}"
                )
    except typer.BadParameter:
        raise
    except Exception:
        # Ignore network/mock failures during pre-validation; backend API will enforce
        pass


def _render_regions_table(regions):
    if not regions:
        console.print("[yellow]No regions found.[/yellow]")
        return

    table = Table("Region ID", "Name", "Datacenters", "Location")
    for r in regions:
        table.add_row(
            str(r.get("id") or "N/A"),
            str(r.get("name") or r.get("label") or "N/A"),
            ", ".join(r.get("datacenters") or []) or "-",
            str(r.get("location") or r.get("continent") or "-"),
        )
    console.print(table)


def regions_command(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter regions by status ('active' or 'reservable')"),
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """List available compute regions."""
    set_output_format(format)
    client = get_client()
    try:
        regions = client.get_available_regions(status=status)
        print_output(regions, table_render_func=_render_regions_table)
    except Exception as e:
        handle_error(e, "Error listing regions")
