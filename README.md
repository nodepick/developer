# Nodepick Developer Platform

Nodepick provides secure, isolated micro-VM compute nodes and integrated Model Context Protocol (MCP) servers tailored for AI agents, automated tasks, and developer workloads over Post-Quantum Cryptography (PQC) TLS.

This repository contains the developer tools for interacting with Nodepick:

- **[Python SDK (`sdk/python`)](sdk/python)**: Programmatic interface for node management, Guest VM MCP communication, and LLM agent tool calling loops.
- **[CLI Tool (`np`)](cli)**: Command-line interface for managing compute nodes, SSH keys, and authentication credentials.

---

## Key Capabilities

- **Micro-VM Orchestration**: Spin up, scale, reboot, and tear down secure compute nodes in seconds.
- **Post-Quantum Cryptography**: Direct Guest VM MCP server (`mcp`) access over HTTP/PQC-TLS (`X25519MLKEM768`).
- **LLM Agent Loops**: First-class support for autonomous agent execution with Ollama, Google Gemini, Anthropic, and OpenAI models.
- **Developer CLI**: Manage nodes, SSH access, and environment authentication directly from your terminal.

---

## Primary Use Cases

1. **AI Agent Tool Execution**: Safely run untrusted or dynamic agent code inside isolated micro-VMs using MCP tools.
2. **Infrastructure Automation**: Automate VM provisioning, service management, and remote execution via Python scriptable APIs.
3. **Interactive Terminal Workflows**: Perform quick administration tasks, manage SSH keys, and inspect node state using the `np` CLI.

---

## Quick Start

### Installation

Install the CLI tool using `uv` or `pip`:

```bash
# Recommended via uv
uv tool install nodepick-cli --with nodepick

# Or via pip
pip install nodepick-cli nodepick
```

### Authentication

Log in with your Nodepick API key:

```bash
np auth login
```

### Command-Line Usage (`np`)

```bash
# List compute nodes
np node list

# Create a new compute node
np node create --name agent-sandbox --cpu 2 --memory 1024

# View exposed MCP tools on a node
np node tools <node_id>
```

### Python SDK Usage (`nodepick`)

```python
from nodepick import NodePickClient, AgentLoop, GeminiProvider

client = NodePickClient(api_key="your-api-key")

# Provision node & connect to guest VM MCP server
node = client.node_create(display_name="demo-node", cpu=1, memory=512)
mcp_client = client.node_mcp(node["id"])

# Run LLM Agent with tool calling
provider = GeminiProvider(api_key="your-gemini-key", model="gemini-1.5-flash")
agent = AgentLoop(provider=provider, mcp_client=mcp_client)

result = await agent.run("Inspect system status and verify active services.")
print(result)
```

---

## Repository Structure

```
├── cli/         # Nodepick CLI tool (`np`) built with Typer & Rich
└── sdk/
    └── python/  # Official Python SDK (`nodepick`)
```

For technical details and contribution guidelines, see [AGENTS.md](AGENTS.md).
