# nodepick.ai CLI (`np`)

`np` is a command-line interface tool built with Python for managing Compute nodes.

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
# List all compute nodes (table view with SSH connect command)
np node list

# Output compute nodes as raw formatted JSON
np node list -f json

# Deploy a new compute node (custom name, cpu, memory MB, network, storage GB)
np node create --name my-vm --cpu 2 --memory 1024 --network private --storage 20

# Get detailed info for a specific node (by ID, VM UUID, or display name)
np node get <node_id>

# Output node details as raw formatted JSON
np node get <node_id> -f json

# List Guest VM MCP tools exposed by node
np node tools <node_id>

# Boot, Shutdown, or Reboot a node
np node boot <node_id>
np node shutdown <node_id>
np node reboot <node_id>

# Delete a compute node
np node delete <node_id>
```

### SSH Key Management Commands (`np ssh`)

```bash
# List all registered SSH public keys
np ssh list

# Output SSH keys list as raw JSON
np ssh list -f json

# Add an SSH public key from a file
np ssh add --name my-key --file ~/.ssh/id_ed25519.pub

# Add an SSH public key from a raw key string
np ssh add --name dev-key --key "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5..."

# Delete an SSH key
np ssh delete <key_id>
```

### Authentication Commands (`np auth`)

```bash
# Save API key (and optional base URL) securely in OS keyring
np auth save

# Save API key non-interactively
np auth save --api-key <your_api_key>

# Test API authentication status & organization details
np auth test

# Clear stored API key from OS keyring
np auth clear
```
