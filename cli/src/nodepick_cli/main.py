import typer
from rich.console import Console
from .commands.node import app as node_app
from .commands.ssh import app as ssh_app
from .auth.login import app as auth_app


app = typer.Typer(
    name="np",
    help="Nodepick CLI - Manage micro-VM compute nodes, SSH keys, and authentication.",
    add_completion=False,
)
console = Console()

from click.core import ParameterSource

import sys
import logging

@app.callback()
def main_callback(
    debug: bool = typer.Option(
        False,
        "--debug", "-d",
        help="Enable DEBUG logging output.",
    ),
):
    if debug:
        logger = logging.getLogger("nodepick")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

# Register command sub-groups
app.add_typer(node_app, name="node")
app.add_typer(ssh_app, name="ssh")
app.add_typer(auth_app, name="auth")

if __name__ == "__main__":
    app()


