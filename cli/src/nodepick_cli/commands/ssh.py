import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
import nodepick
from ..core.config import get_api_key, get_base_url
from ..core.exceptions import handle_error
from ..core.formatters import OutputFormat, set_output_format, print_output


app = typer.Typer(name="ssh", help="Manage developer SSH public keys.")
console = Console()


from click.core import ParameterSource

@app.callback(invoke_without_command=True)
def ssh_callback():
    pass


def get_client() -> nodepick.NodePickClient:
    key = get_api_key()
    url = get_base_url()
    if not key:
        console.print(
            "[yellow]No API key found.[/yellow] "
            "Run [bold]np auth save[/bold] to store your API key."
        )
        raise typer.Exit(1)
    return nodepick.NodePickClient(api_key=key, base_url=url)


def _render_ssh_keys_table(keys):
    if not keys:
        console.print("[yellow]No SSH keys found.[/yellow]")
        return

    table = Table("ID", "Name", "Type", "Created At")
    for key in keys:
        table.add_row(
            str(key.get("id", "N/A")),
            str(key.get("name", "N/A")),
            str(key.get("key_type", "N/A")),
            str(key.get("created_at", "N/A")),
        )
    console.print(table)


@app.command("add")
def add_ssh_key(
    name: str = typer.Option(..., "--name", "-n", help="Friendly name for the SSH key"),
    key_file: Optional[str] = typer.Option(None, "--file", "-f", help="Path to SSH public key file (e.g. ~/.ssh/id_ed25519.pub)"),
    public_key: Optional[str] = typer.Option(None, "--key", help="Raw SSH public key string"),
):
    """Add an SSH public key for automatic injection into new compute nodes."""
    client = get_client()
    try:
        ssh_str = public_key
        if not ssh_str and key_file:
            with open(key_file, "r", encoding="utf-8") as f:
                ssh_str = f.read().strip()
        if not ssh_str:
            raise ValueError("Must provide either --file or --key")

        res = client.key_create(name=name, key_type="ssh_key", ssh_public_key=ssh_str)
        key_id = res.get("key", {}).get("id", "N/A")
        console.print(f"[bold green]SSH Key registered successfully![/bold green] Key ID: {key_id}")
    except Exception as e:
        handle_error(e, "Error adding SSH key")


@app.command("delete")
def delete_ssh_key(
    key_id: str = typer.Argument(..., help="Key ID to delete"),
):
    """Delete an SSH key."""
    client = get_client()
    try:
        res = client.key_delete(key_id)
        console.print(f"[bold green]SSH key {key_id} deleted.[/bold green]")
    except Exception as e:
        handle_error(e, "Error deleting SSH key")


@app.command("list")
def list_ssh_keys(
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--format", "-f",
        help="Output format (table or json).",
        case_sensitive=False,
    ),
):
    """List all organization SSH keys."""
    set_output_format(format)
    client = get_client()
    try:
        keys = client.key_list(key_type="ssh_key")
        print_output(keys, table_render_func=_render_ssh_keys_table)
    except Exception as e:
        handle_error(e, "Error listing SSH keys")