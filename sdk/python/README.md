# Nodepick Python SDK

A modern Python SDK for interacting with the Nodepick micro-VM orchestration API and executing agent tasks on Guest VM Model Context Protocol (MCP) servers using Post-Quantum Cryptography (PQC) TLS.

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

## Features

### 1. Manage Compute Nodes

Interact with the Nodepick REST API to manage node lifecycles (create, list, reboot, shutdown, delete).

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

---

### 2. Connect to the Guest VM MCP Server

Directly interact with the zero-dependency Guest VM MCP server (`mcp`) over a secure, Streamable HTTP connection. The client automatically configures TLS to exclusively negotiate post-quantum hybrid groups (`X25519MLKEM768`).

```python
from nodepick import NodePickClient

async def main():
    # 1. Initialize main client
    client = NodePickClient(api_key="your-developer-api-key")

    # 2. Obtain initialized MCP client directly from the node ID/UUID
    mcp_client = client.mcp("node-uuid")
    
    # 3. List available tools
    tools = await mcp_client.list_tools()
    print("Available tools:")
    for tool in tools:
        print(f"- {tool['name']}: {tool['description']}")
        
    # 4. Execute a tool inside the Guest VM
    res = await mcp_client.call_tool("manage_services", {"action": "status", "service": "nginx"})
    print("Tool Output:", res)
```

---

### 3. LLM Agent Loops (Tool Calling)

Integrate LLM models directly with the Guest VM's MCP tools. The SDK exposes an `AgentLoop` runner with built-in REST client providers for Ollama (local), Google Gemini, Anthropic, and OpenAI.

```python
from nodepick import NodePickClient, AgentLoop, OllamaProvider, GeminiProvider, OpenAIProvider

async def main():
    client = NodePickClient(api_key="your-developer-api-key")

    # Obtain the Guest VM's MCP client directly from the node
    mcp_client = client.mcp("node-uuid")

    # Pick an LLM provider:
    
    # A. Local Ollama (zero API keys needed)
    provider = OllamaProvider(model="llama3.1")
    
    # B. Google Gemini
    # provider = GeminiProvider(api_key="your-gemini-key", model="gemini-1.5-flash")
    
    # C. OpenAI GPT
    # provider = OpenAIProvider(api_key="your-openai-key", model="gpt-4o")
    
    # D. Anthropic Claude
    # provider = AnthropicProvider(api_key="your-anthropic-key", model="claude-3-5-sonnet-latest")

    # Initialize the runner
    agent = AgentLoop(provider=provider, mcp_client=mcp_client)
    
    # Run the prompt (the loop executes tool calls recursively until final answer is reached)
    result = await agent.run(
        prompt="Check if nginx service is running, and if not, try to start it and verify.",
        system_instruction="You are a systems administration copilot operating inside the guest VM."
    )
    print("Agent Final Answer:")
    print(result)
```

---

## Publishing to PyPI

To build and publish this SDK package to PyPI using [`uv`](https://github.com/astral-sh/uv):

1. **Build the package**:
   ```bash
   uv build
   ```
   This generates distribution archives (`.tar.gz` and `.whl`) in the `dist/` directory.

2. **Publish to PyPI**:
   ```bash
   uv publish
   ```
   *Note: You can pass `--token <your-pypi-token>` or set `UV_PUBLISH_TOKEN` in your environment.*

