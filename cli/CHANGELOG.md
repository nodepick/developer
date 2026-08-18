# CHANGELOG.md

## [Unreleased]

### Changed
- Changed authentication command from `np auth save` to `np auth configure`.

### Added
- Added `np --version` (`-v`) flag.
- Added `np ai mcp configure <agent> [nodes...]` command to configure MCP servers on AI agents (such as Antigravity) over HTTP Stream with self-signed certificate verification bypassed.

## [0.1.0] - 2026-07-31

### Added
- Created `np` CLI tool in `cli/` using Typer and Rich.
- Added commands: `list`, `create`, `get`, `delete`, `shutdown`, `reboot`.

