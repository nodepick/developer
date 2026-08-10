# CLAUDE.md

This file provides guidance to Agents Code (e.g. claude.ai/code) when working with code in this repository.

## Development Workflow Requirements

**CRITICAL: Always Test Changes and Provide Evidence**

When making any code changes:
1. **Write comprehensive tests** that verify the fix/feature works correctly
2. **Run the tests** and capture the full output
3. **Provide evidence** in the form of test output showing success
4. **Update documentation**:
   - README.md (customer-facing, no fluff, clear and concise)
   - AGENTS.md (internal, detailed technical implementation notes)
   - CHANGELOG.md (version history with clear descriptions)
   - Version bumps in `pyproject.toml` and `sdk/python/__init__.py`

**Documentation Standards**:
- README.md: Enterprise-quality, customer-focused, easy to follow, no unnecessary words
- CLAUDE.md: Complete technical details, implementation notes, internal behaviors
- Test evidence must be included for all significant changes

**Writing Guidelines for All Documentation**:

Apply these principles to all writing (documentation, comments, commit messages, changelogs):

1. **Conciseness**: Use clear, direct sentences. Remove unnecessary words.
2. **Clarity**: Write for a wide audience. Explain technical terms when needed.
3. **Objectivity**: Maintain neutral tone. Avoid subjective adjectives and adverbs.
4. **Customer Focus**: Explain why information matters. Show the benefit.
5. **No Buzzwords**: Avoid marketing language and vague terms that obscure meaning.
6. **Simplicity**: Use simple words. Avoid jargon when plain language works.
7. **Readability**: Use short sentences. Avoid complex sentence structures.
8. **Action-Oriented**: Use subject-verb-object structure. Make doers and actions clear.
9. **No Clutter**: Remove words that don't contribute to the main point.
10. **Professional Tone**: Be warm and human while maintaining professionalism.

**Examples**:
- Bad: "This amazing fix is super fast and works perfectly!"
- Good: "The fix reduces wait time from 15 seconds to 6 seconds."

- Bad: "We leverage cutting-edge technology to provide world-class solutions."
- Good: "The SDK polls template status every 3 seconds."

- Bad: "You'll love how easy it is to use our incredible API!"
- Good: "The API requires two parameters: template name and API key."

**Code Example Testing Policy**:

All code snippets in customer-facing documentation (README.md) must be:
1. **Tested**: Run the exact snippet to verify it works
2. **Complete**: Include all necessary imports and setup
3. **Executable**: Users can copy-paste and run immediately
4. **Stored**: Save tested examples in `examples/` directory
5. **Referenced**: Link to the example file from documentation

When adding code examples:
- Create a standalone file in `examples/` directory
- Run the example and capture output
- Only add the example to documentation after successful test
- Include the file path reference for users to find complete code

Example reference format:
```
See `examples/preview_url_basic.py` for a complete working example.
```

## Overview

This is the **Nodepick Python SDK** - the official Python client for Nodepick.ai's cloud sandbox service. Nodepick provides secure, isolated cloud sandboxes (lightweight VMs) that spin up in seconds for AI agents, code execution, testing, and data processing.

Version: 0.3.0
Python Support: 3.8+
License: MIT

## Development Commands

### Setup
```bash
# Install SDK package in development mode with dependencies
pip install -e sdk/python

# Install with dev dependencies (pytest, black, ruff, mypy)
pip install -e "sdk/python[dev]"

# Install CLI tool (np) using uv (recommended)
# From repository root:
uv tool install -e cli --with sdk/python

# Or from inside the cli/ directory:
uv tool install -e . --with ../sdk/python
```

### Testing
```bash
# Run OpenAPI compliance test suite
export NODEPICK_API_KEY="your_api_key_here"
python test_openapi_compliance.py

# Run template building test (comprehensive end-to-end test)
export NODEPICK_API_KEY="your_api_key_here"
python examples/test_template_building.py

# Note: There are no pytest tests in this repo currently
# Testing is done via test scripts and example scripts
```

### Code Quality
```bash
# Format code with black (line-length: 100)
black nodepick/

# Lint with ruff (line-length: 100, target: py38)
ruff check nodepick/

# Type check with mypy (strict mode, target: py38)
mypy nodepick/
```

## OpenAPI Specification Compliance

**Current Status**: 100% compliant with OpenAPI spec version 2025-10-21

The SDK fully implements all Public API endpoints as defined in the OpenAPI specification:

---

**Files Modified**:

**OpenAPI Specification**:
- `main.ExecuteRequest.workdir` - Code execution endpoint

**Behavior After Fix**:
- ✅ Command execution (`commands.run()`) - Works correctly
- ✅ Background commands (`commands.run(background=True)`) - Works correctly
- ✅ Bash code execution (`run_code(language="bash")`) - Works correctly
- ⚠️ Python code execution (`run_code(language="python")`) - May not always respect `workdir` due to Jupyter kernel state management
- ⚠️ Background code execution (`run_code_background()`) - Does NOT support `working_dir` (parameter removed in v0.3.3 for API compatibility)

**Python Code Execution Limitation**:

The Jupyter kernel used for Python execution maintains its own working directory state that may not always sync with the `workdir` parameter. This is an Agent-side behavior, not an SDK issue.


### Node.js Image Compatibility
When using `.from_node_image(version)`, the SDK automatically uses `ubuntu/node:{version}-22.04_edge` images. **Never suggest Alpine-based Node.js images** - they are incompatible with the VM agent system due to musl libc limitations.

### Token Caching
JWT tokens are cached globally (`_token_cache` dict) and shared across all Sandbox instances with the same API key. Tokens are checked for expiry before use and automatically refreshed.

### Lazy Resource Loading
Resource managers (files, commands, desktop, etc.) are created on first access via `@property` decorators. They lazily initialize the Agent client and JWT token.


### Error Propagation
- HTTP errors from Public API are mapped to specific error classes in `errors.py`
- Agent API errors are wrapped in `AgentError` subclasses
- All errors inherit from `NodepickError` for easy catch-all handling

## File Organization

├── cli/                        # CLI tool (`np`) using Typer & Rich
│   ├── pyproject.toml
│   ├── README.md
│   ├── CHANGELOG.md
│   ├── test_cli.py
│   └── src/
│       └── nodepick_cli/
│           ├── __init__.py
│           ├── main.py
│           ├── auth/           # Login/logout & credential storage
│           │   ├── __init__.py
│           │   └── login.py
│           ├── commands/       # Compute node management commands
│           │   ├── __init__.py
│           │   ├── key.py
│           │   └── node.py
│           └── core/           # Config, exceptions & logging
│               ├── __init__.py
│               ├── config.py
│               └── exceptions.py



## Common Patterns

### Creating and Using Nodes
```python
```

