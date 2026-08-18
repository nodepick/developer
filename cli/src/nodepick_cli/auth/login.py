import os
import typer
from typing import Optional
from rich.console import Console
import keyring
import nodepick
from ..core.config import get_api_key, get_base_url, load_config, save_config
from ..core.exceptions import handle_error

KEYRING_SERVICE = "nodepick-cli"
KEYRING_API_KEY = "api_key"

app = typer.Typer(name="auth", help="Manage API key authentication.")
console = Console()


def _get_api_key_with_source() -> tuple:
    """Return (api_key, source) where source is a human-readable label."""
    if os.getenv("NODEPICK_API_KEY"):
        return os.getenv("NODEPICK_API_KEY"), "env var NODEPICK_API_KEY"
    try:
        kr_key = keyring.get_password(KEYRING_SERVICE, KEYRING_API_KEY)
        if kr_key:
            return kr_key, "OS keyring"
    except Exception:
        pass
    return None, None


def _keyring_get(key_name: str) -> Optional[str]:
    try:
        return keyring.get_password(KEYRING_SERVICE, key_name) or None
    except Exception:
        return None


def _keyring_set(key_name: str, value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, key_name, value)


def _keyring_delete(key_name: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, key_name)
    except Exception:
        pass  # already absent


@app.command("clear")
def auth_clear():
    """Remove the API key from the OS keyring."""
    try:
        _keyring_delete(KEYRING_API_KEY)
        console.print("[bold green]API key cleared from OS keyring.[/bold green]")
    except Exception as e:
        handle_error(e, "Failed to clear credentials")


@app.command("configure")
@app.command("save")
def auth_configure(
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="Nodepick API key / bearer token"
    ),
    base_url: Optional[str] = typer.Option(
        None, "--base-url", "-u", help="API base URL (default: https://api.nodepick.ai)"
    ),
):
    """Configure API key (and optional base URL) securely in the OS keyring."""
    try:
        if not api_key:
            api_key = typer.prompt("Nodepick API Key", hide_input=True)

        resolved_url = (base_url or get_base_url()).rstrip("/")

        _keyring_set(KEYRING_API_KEY, api_key)
        # Save base_url to config file; only the API key lives in the keyring.
        save_config({"base_url": resolved_url})

        console.print(
            "[bold green]Credentials configured.[/bold green] "
            f"API key stored in OS keyring. Base URL: {resolved_url} (saved to config)"
        )
    except Exception as e:
        handle_error(e, "Failed to configure credentials")


@app.command("test")
def auth_test():
    """Test API access using the stored API key."""
    key, source = _get_api_key_with_source()
    url = get_base_url()
    if not key:
        console.print(
            "[yellow]No API key found.[/yellow] "
            "Run 'np auth configure' or set NODEPICK_API_KEY."
        )
        raise typer.Exit(1)

    try:
        client = nodepick.NodePickClient(api_key=key, base_url=url)
        user_info = client.get_me()
        user = user_info.get("user", {})
        org  = user_info.get("org", {})
        console.print(
            f"[bold green]API access OK.[/bold green] "
            f"User: [bold]{user.get('email', 'unknown')}[/bold] | "
            f"Org: {org.get('name', 'N/A')} | "
            f"URL: {url} | "
            f"Key source: [dim]{source}[/dim]"
        )
    except Exception as e:
        handle_error(e, "API access test failed")
