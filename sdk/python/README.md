# nodepick.ai Python SDK

A Python SDK for managing Compute Nodes from [`nodepick.ai`](https://www.nodepick.ai)

---

## Installation

### Recommended Method (`uv`)

Using [`uv`](https://github.com/astral-sh/uv) is the recommended fast, reliable way to install the `nodepick` SDK:

```bash
# Install published SDK from PyPI
uv add nodepick

# Or install from local source in development mode
uv pip install -e .
```

### Alternative Method (`pip`)

```bash
# Install from PyPI
pip install nodepick

# Or install local editable SDK
pip install -e .
```



---


## Manage Compute Nodes

Interact with the nodepick REST API to manage node lifecycles (create, list, reboot, shutdown, delete).

```python
from nodepick import NodePickClient

# Authenticate with Nodepick Developer API Key
client = NodePickClient(api_key="your-developer-api-key", base_url="https://api.nodepick.ai")

with client:
    # 1. Create a compute node
    node = client.node_create(
        memory=1024 * 1024 * 1024,
        cpu=2,
        network_type="public",
        display_name="pqc-agent-sandbox"
    )
    node_id = node["id"]
    print(f"Created node: {node_id}")

    # 2. Get node details (including VMM status, SSH options, and MCP configuration)
    details = client.node_get_details(node_id)
    print("Node details:", details)

    # 3. List all active nodes
    nodes = client.node_list()
    print("My nodes:", nodes)

    # 4. Reboot a node
    client.node_reboot(node_id)

    # 5. Shutdown a node
    client.node_shutdown(node_id)

    # 6. Delete a node and reclaim resources (polls until fully deleted)
    client.node_delete(node_id)
```

## Reference

Check the official [`Documentation`](https://docs.nodepick.ai/api-reference/overview) for a comprehensive reference guide.