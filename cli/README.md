# nodepick.ai CLI (`np`)

`np` is a command-line interface tool built with Python for managing Compute nodes.

## Installation

### Recommended Method using Shell Installer (`curl`)

```bash
# Install using auto-detection (uv -> pipx -> pip)
curl -sSL https://raw.githubusercontent.com/nodepick/developer/main/cli/install.sh | bash

# Install latest from a local Git repo
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


## Reference

Check the official [`Documentation`](https://docs.nodepick.ai/cli-reference/overview) for the comprehensive reference guide.


### Basic Usage

```bash
# Check version
np --version

# List available regions
np regions

# Deploy a compute node in a specific region
np node create --name dev-node --region us-west-1

# List compute nodes
np node list
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
