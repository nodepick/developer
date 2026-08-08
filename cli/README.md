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

### Test authentication

```bash
# Save API key (and optional base URL) securely in OS keyring
np auth save

# Test API authentication status & organization details
np auth test

# Clear stored API key from OS keyring
np auth clear
```
