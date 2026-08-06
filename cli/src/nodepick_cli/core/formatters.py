import json
from enum import Enum
from typing import Any
from rich.console import Console

console = Console()

import sys

class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"

_current_format: OutputFormat = OutputFormat.TABLE

def set_output_format(fmt: OutputFormat) -> None:
    global _current_format
    _current_format = fmt

def get_output_format() -> OutputFormat:
    return _current_format

def print_output(data: Any, table_render_func=None) -> None:
    """Print data according to active output format setting."""
    if _current_format == OutputFormat.JSON:
        if isinstance(data, (dict, list)):
            console.print_json(data=data)
        else:
            console.print_json(data={"result": data})
    else:
        if table_render_func:
            table_render_func(data)
        elif isinstance(data, (dict, list)):
            console.print_json(data=data)
        else:
            console.print(data)



