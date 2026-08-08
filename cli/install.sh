#!/usr/bin/env bash
set -eo pipefail

VERSION="0.0.1"
PACKAGE_NAME="nodepick-cli"
SDK_PACKAGE_NAME="nodepick"
GIT_URL="git+https://github.com/nodepick/developer#subdirectory=cli"
GIT_URL_SDK="git+https://github.com/nodepick/developer#subdirectory=sdk/python"

# Defaults
MODE="auto"
DRY_RUN=false
NON_INTERACTIVE=false
QUIET=false

show_help() {
    cat <<EOF
nodepick.ai CLI Installer (v${VERSION})

Usage:
  curl -sSL https://raw.githubusercontent.com/nodepick/developer/main/cli/install.sh | bash [options]
  or:
  ./install.sh [options]

Options:
  --mode MODE       Installation mode (auto, uv, pipx, pip, git) (default: auto)
  --dry-run         Preview changes without installing
  --non-interactive Skip all prompts (use defaults)
  --quiet           Minimal output
  --help            Show this help message
  --version         Show installer version

Installation Modes:
  auto    Detect best method: tries uv -> pipx -> pip
  uv      Install via uv tool
  pipx    Install via pipx
  pip     Install directly via python pip
  git     Install directly from GitHub repository via uv tool
EOF
}

show_version() {
    echo "nodepick.ai CLI Installer v${VERSION}"
}

# Parse CLI flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            if [[ -n "$2" && "$2" != --* ]]; then
                MODE="$2"
                shift 2
            else
                echo "Error: --mode requires an argument (auto, uv, pipx, pip, or git)." >&2
                exit 1
            fi
            ;;
        --mode=*)
            MODE="${1#*=}"
            shift 1
            ;;
        --dry-run)
            DRY_RUN=true
            shift 1
            ;;
        --non-interactive)
            NON_INTERACTIVE=true
            shift 1
            ;;
        --quiet)
            QUIET=true
            shift 1
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            show_version
            exit 0
            ;;
        *)
            echo "Error: Unknown option '$1'." >&2
            echo "Run with --help for usage guidance." >&2
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "$MODE" != "auto" && "$MODE" != "uv" && "$MODE" != "pipx" && "$MODE" != "pip" && "$MODE" != "git" ]]; then
    echo "Error: Invalid mode '$MODE'. Valid modes are 'auto', 'uv', 'pipx', 'pip', or 'git'." >&2
    exit 1
fi

log() {
    if [[ "$QUIET" == "false" ]]; then
        echo "$@"
    fi
}

log_step() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "\033[34m==>\033[0m \033[1m$1\033[0m"
    fi
}

log_success() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "\033[32m✔\033[0m $1"
    fi
}

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[dry-run] Would execute: $*"
    else
        if [[ "$QUIET" == "true" ]]; then
            "$@" >/dev/null 2>&1
        else
            "$@"
        fi
    fi
}

install_uv() {
    log_step "Checking for 'uv'..."
    if command -v uv >/dev/null 2>&1; then
        log "Found uv: $(command -v uv)"
        log_step "Installing ${PACKAGE_NAME} via 'uv tool'..."
        run_cmd uv tool install "${PACKAGE_NAME}" --with "${SDK_PACKAGE_NAME}"
        log_success "Successfully installed ${PACKAGE_NAME} using uv tool."
    else
        if [[ "$MODE" == "uv" ]]; then
            echo "Error: 'uv' binary not found in PATH." >&2
            echo "Please install uv (https://github.com/astral-sh/uv) or run with '--mode auto'." >&2
            exit 1
        fi
        return 1
    fi
}

install_pipx() {
    log_step "Checking for 'pipx'..."
    if command -v pipx >/dev/null 2>&1; then
        log "Found pipx: $(command -v pipx)"
        log_step "Installing ${PACKAGE_NAME} via 'pipx'..."
        run_cmd pipx install "${PACKAGE_NAME}"
        log_success "Successfully installed ${PACKAGE_NAME} using pipx."
    else
        if [[ "$MODE" == "pipx" ]]; then
            echo "Error: 'pipx' binary not found in PATH." >&2
            echo "Please install pipx or run with '--mode auto'." >&2
            exit 1
        fi
        return 1
    fi
}

install_pip() {
    log_step "Checking for 'python3' / 'pip'..."
    local python_bin=""
    if command -v python3 >/dev/null 2>&1; then
        python_bin="python3"
    elif command -v python >/dev/null 2>&1; then
        python_bin="python"
    else
        if [[ "$MODE" == "pip" ]]; then
            echo "Error: Neither python3 nor python found in PATH." >&2
            exit 1
        fi
        return 1
    fi

    log "Using Python: $($python_bin --version 2>&1)"
    log_step "Installing ${PACKAGE_NAME} via pip..."
    run_cmd "$python_bin" -m pip install --upgrade "${PACKAGE_NAME}"
    log_success "Successfully installed ${PACKAGE_NAME} using pip."
}

install_git() {
    log_step "Checking for 'uv' and 'git'..."
    if ! command -v uv >/dev/null 2>&1; then
        echo "Error: 'uv' binary not found in PATH." >&2
        echo "Please install uv (https://github.com/astral-sh/uv)." >&2
        exit 1
    fi

    if ! command -v git >/dev/null 2>&1; then
        echo "Error: 'git' binary not found in PATH." >&2
        exit 1
    fi

    log "Found uv: $(command -v uv)"
    log "Found git: $(command -v git)"
    log_step "Installing ${PACKAGE_NAME} from Git repository via uv tool (${GIT_URL})..."
    run_cmd uv tool install "${GIT_URL}" --with "${GIT_URL_SDK}"
    log_success "Successfully installed ${PACKAGE_NAME} from Git repository via uv tool."
}

# Main execution
log "--------------------------------------------------------"
log "Installing nodepick.ai CLI (np) v${VERSION}"
log "Mode: ${MODE} | Dry Run: ${DRY_RUN} | Non-interactive: ${NON_INTERACTIVE}"
log "--------------------------------------------------------"

case "$MODE" in
    uv)
        install_uv
        ;;
    pipx)
        install_pipx
        ;;
    pip)
        install_pip
        ;;
    git)
        install_git
        ;;
    auto)
        log_step "Detecting best installation method (uv -> pipx -> pip)..."
        if install_uv; then
            :
        elif install_pipx; then
            :
        elif install_pip; then
            :
        else
            echo "Error: Could not install via uv, pipx, or pip." >&2
            exit 1
        fi
        ;;
esac

if [[ "$DRY_RUN" == "false" ]]; then
    log ""
    log_success "nodepick.ai CLI installation process completed!"
    log "Run 'np --help' to verify the installation."
fi
