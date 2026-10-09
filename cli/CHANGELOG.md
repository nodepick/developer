# CHANGELOG.md

## [0.1.4] - 2026-10-08

### Added
- Added `--region` (`-r`) option to `np node create` to specify the deployment region.
- Added `--host` option to `np node create` to deploy directly onto a specified compute Host ID.
- Added region validation against supported active regions for `np node create` and `np network create`.
- Added `np regions` command to list available compute regions.
- Added `np compute` top-level command for compute discovery with real-time pricing and consolidated RAM/Disk/CPU specs.
- Added `np --version` (`-v`) flag.
- Added `np ai mcp configure <agent> [nodes...]` command to configure MCP servers on AI agents (Antigravity, OpenCode).

### Changed
- Changed authentication command from `np auth save` to `np auth configure`.
- Replaced `np find` and `np node find` with top-level `np compute`.
- Removed NAT configuration options from `np network` commands (outbound NAT enabled upstream by default).

## [0.1.0] - 2026-07-31

### Added
- Created `np` CLI tool in `cli/` using Typer and Rich.
- Added commands: `list`, `create`, `get`, `delete`, `shutdown`, `reboot`.

