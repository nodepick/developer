# nodepick.ai CLI (`np`)

`np` is a command-line interface tool built with Python for managing Compute nodes.

## Installation

### Recommended Method using Shell Installer (`curl`)

```bash
# Install using auto-detection (uv -> pipx -> pip)
curl -sSL https://raw.githubusercontent.com/nodepick/developer/main/cli/install.sh | bash

# Install latest from Git repo
curl -sSL https://raw.githubusercontent.com/nodepick/developer/main/cli/install.sh | bash -s -- --mode git
```

### Recommended Method using (`uv`)

Using [`uv`](https://github.com/astral-sh/uv) is the recommended way to install and manage the `np` CLI tool globally in an isolated environment:

```bash
# Install published package from PyPI
uv tool install nodepick-cli

# Or install from inside the cli directory:
uv tool install -e . --with ../sdk/python

# Or re-install
uv tool install -e . --with ../sdk/python --reinstall
```

### `pip` Method

Installing published package from PyPI:

```bash
pip install nodepick-cli
```

When installing from a local git repository, first install the local `nodepick` SDK dependency before installing `nodepick-cli`:

```bash
# Install from the "cli" folder using pip:
pip install -e ../sdk/python .
```


## Usage

[`nodepick.ai Documentation`](https://docs.nodepick.ai/cli-reference/overview)


### Basic Usage

```bash
# List all compute nodes (table view with SSH connect command)
np --version
```

### Authentication

```bash
# Configure API key (and optional base URL) securely in OS keyring
np auth configure

# Test API authentication status & organization details
np auth test

# Clear stored API key from OS keyring
np auth clear
```

### SSH Key Management

```bash
# Register an SSH public key from a file
np ssh add -n "MBA 2026" --file ~/.ssh/id_ed25519.pub

# Register an SSH public key directly
np ssh add -n "Desktop" --key "ssh-ed25519 AAAAC3... user@host"

# List registered SSH keys
np ssh list

# Delete an SSH key by ID
np ssh delete <key_id>
```

### Compute Nodes

```bash
# List all compute nodes
np node list

# Create a new compute node
np node create --name "my-sandbox" --cpu 2 --memory 2048

# Get details & connection info for a node
np node get <node_id>

# Reboot a node
np node reboot <node_id>

# Shutdown a node
np node shutdown <node_id>

# Delete a node
np node delete <node_id>
```

### [BETA] AI & Model Context Protocol (MCP)

```bash
# Configure Antigravity to connect to a specific node MCP server over HTTP Stream
np ai mcp configure antigravity dev

# Configure Antigravity to connect to multiple nodes
np ai mcp configure antigravity dev prod

# Configure Antigravity for all available compute nodes
np ai mcp configure antigravity
```