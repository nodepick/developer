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
def auth_configure(
    base_url: Optional[str] = typer.Option(
        None, "--base-url", "-u", help="API base URL (default: https://api.nodepick.ai)"
    ),
):
    """Configure API key (and optional base URL) securely in the OS keyring."""
    try:
        api_key = typer.prompt("API Key", default="", hide_input=True, show_default=False)
        if not api_key or not api_key.strip():
            console.print("[yellow]No API key entered. Aborting.[/yellow]")
            raise typer.Exit(1)

        resolved_url = (base_url or get_base_url()).rstrip("/")

        _keyring_set(KEYRING_API_KEY, api_key.strip())
        # Save base_url to config file; only the API key lives in the keyring.
        save_config({"base_url": resolved_url})

        console.print(
            "[bold green]Credentials configured.[/bold green] "
            f"API key stored in OS keyring. Base URL: {resolved_url}"
        )
    except typer.Exit:
        raise
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
        user = user_info.get("user", {}) if isinstance(user_info.get("user"), dict) else {}
        org  = user_info.get("org", {}) if isinstance(user_info.get("org"), dict) else {}

        user_id = (
            user.get("id")
            or user.get("userId")
            or user_info.get("userId")
            or user_info.get("user_id")
            or user.get("email")
            or "unknown"
        )
        org_id = (
            org.get("id")
            or org.get("orgId")
            or user_info.get("orgId")
            or user_info.get("org_id")
            or "unknown"
        )

        console.print("[bold green]API access OK[/bold green]")
        console.print(f"API URL: {url}")
        console.print(f"User: {user_id}")
        console.print(f"Organization: {org_id}")
    except Exception as e:
        handle_error(e, "API access test failed")
