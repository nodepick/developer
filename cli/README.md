# Nodepick CLI (`np`)

`np` is a command-line interface tool built with Python and [Typer](https://typer.tiangolo.com/) for managing Nodepick compute nodes on Linux and macOS.

## Installation

### Recommended Method (`uv`)

Using [`uv`](https://github.com/astral-sh/uv) is the recommended way to install and manage the `np` CLI tool globally in an isolated environment:

```bash
# Install published package from PyPI
uv tool install nodepick-cli

# Or install from inside the cli directory:
uv tool install -e . --with ../sdk/python

# Or re-install
uv tool install -e . --with ../sdk/python --reinstall
```

### Alternative Method (`pip`)

You can also install using standard `pip`:

```bash
# Install published package from PyPI
pip install nodepick-cli

# Or install local editable source
pip install -e cli
```


## Usage

### Global Options

- `--debug`, `-d`: Enable DEBUG logging output. Default is disabled.

```bash
# Output list as Rich table (default)
np node list

# Output list as raw formatted JSON
np node list -f json

# Output node details as raw JSON
np node get <node_id> -f json

# Output SSH keys list as raw JSON
np ssh list -f json

# Enable debug logging output
np --debug node list
```

### Node Management Commands (`np node`)


```bash
# List all compute nodes
np node list

# Create a new compute node
np node create --name my-vm --cpu 2 --memory 1024

# Get node details
np node get <node_id>

# List MCP tools exposed by node
np node tools <node_id>

# Delete a node
np node delete <node_id>

# Shutdown or Reboot
np node shutdown <node_id>
np node reboot <node_id>
```

### Authentication Commands (`np auth`)

```bash
# Log in and store API key locally
np auth login

# Check authentication status
np auth status

# Clear stored credentials
np auth logout
```
