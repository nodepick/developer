import typer
import httpx
from rich.console import Console

from .formatters import get_output_format, OutputFormat

console = Console()

def handle_error(e: Exception, message: str = "An error occurred"):
    if get_output_format() == OutputFormat.JSON:
        err_obj = {"code": "error", "message": message}
        if isinstance(e, httpx.HTTPStatusError):
            try:
                body = e.response.json()
                if isinstance(body, dict):
                    inner_err = body.get("error")
                    if isinstance(inner_err, dict):
                        err_code = inner_err.get("code") or body.get("code") or "error"
                        err_msg = inner_err.get("message") or str(e)
                        err_obj = {"code": err_code, "message": err_msg}
                        if "details" in inner_err:
                            err_obj["details"] = inner_err["details"]
                    else:
                        err_code = body.get("code") or inner_err or "error"
                        err_msg = body.get("message") or inner_err or str(e)
                        err_obj = {"code": err_code, "message": err_msg}
                    if "details" in body and "details" not in err_obj:
                        err_obj["details"] = body["details"]
                else:
                    err_obj = {"code": f"http_{e.response.status_code}", "message": str(e)}
            except Exception:
                err_obj = {"code": f"http_{e.response.status_code}", "message": str(e)}
        else:
            err_obj = {"code": "error", "message": str(e)}
        console.print_json(data=err_obj)
        raise typer.Exit(code=1)

    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        err_msg = ""
        try:
            body = e.response.json()
            if isinstance(body, dict):
                inner_err = body.get("error")
                if isinstance(inner_err, dict):
                    err_msg = inner_err.get("message") or ""
                elif isinstance(inner_err, str):
                    err_msg = inner_err
                else:
                    err_msg = body.get("message") or ""
                details = body.get("details") or (inner_err.get("details") if isinstance(inner_err, dict) else None)
                if details and isinstance(details, dict):
                    field_errs = details.get("fieldErrors")
                    if field_errs:
                        errs = [f"{k}: {', '.join(v)}" for k, v in field_errs.items() if v]
                        if errs:
                            err_msg += f" ({'; '.join(errs)})"
        except Exception:
            pass

        if err_msg:
            console.print(f"[bold red]{message}:[/bold red] {err_msg}")
        elif status == 404:
            console.print("[bold red]Node not found[/bold red]")
        elif status == 400:
            console.print("[bold red]Invalid request[/bold red]")
        elif status in (401, 403):
            console.print("[bold red]Authentication failed.[/bold red] Check your API key or run 'np auth configure'.")
        else:
            console.print(f"[bold red]{message}:[/bold red] {e}")
    else:
        console.print(f"[bold red]{message}:[/bold red] {e}")
    raise typer.Exit(code=1)
