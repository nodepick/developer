#!/usr/bin/env bash
set -eo pipefail

VERSION="0.1.1"
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

log_warn() {
    if [[ "$QUIET" == "false" ]]; then
        echo -e "\033[33m!\033[0m $1" >&2
    fi
}

log_error() {
    echo -e "\033[31m✖\033[0m $1" >&2
}

run_cmd() {
    if [[ "$DRY_RUN" == "true" ]]; then
        log "[dry-run] Would execute: $*"
        return 0
    fi

    if [[ "$QUIET" == "true" ]]; then
        "$@" >/dev/null 2>&1
    else
        "$@"
    fi
}

install_uv() {
    log_step "Checking for 'uv'..."
    if command -v uv >/dev/null 2>&1; then
        log "Found uv: $(command -v uv)"
        log_step "Installing ${PACKAGE_NAME} via 'uv tool'..."
        if run_cmd uv tool install "${PACKAGE_NAME}" --with "${SDK_PACKAGE_NAME}"; then
            log_success "Successfully installed ${PACKAGE_NAME} using uv tool."
            return 0
        else
            log_error "Failed to install ${PACKAGE_NAME} using uv tool."
            if [[ "$MODE" == "uv" ]]; then
                exit 1
            fi
            return 1
        fi
    else
        if [[ "$MODE" == "uv" ]]; then
            log_error "'uv' binary not found in PATH."
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
        if run_cmd pipx install "${PACKAGE_NAME}"; then
            log_success "Successfully installed ${PACKAGE_NAME} using pipx."
            return 0
        else
            log_error "Failed to install ${PACKAGE_NAME} using pipx."
            if [[ "$MODE" == "pipx" ]]; then
                exit 1
            fi
            return 1
        fi
    else
        if [[ "$MODE" == "pipx" ]]; then
            log_error "'pipx' binary not found in PATH."
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
            log_error "Neither python3 nor python found in PATH."
            exit 1
        fi
        return 1
    fi

    log "Using Python: $($python_bin --version 2>&1)"

    if ! "$python_bin" -m pip --version >/dev/null 2>&1; then
        if [[ "$MODE" == "pip" ]]; then
            log_error "No module named pip found for $python_bin."
            echo "Please install pip (e.g. 'sudo apt install python3-pip' or 'python3 -m ensurepip') or install uv." >&2
            exit 1
        fi
        return 1
    fi

    log_step "Installing ${PACKAGE_NAME} via pip..."
    if run_cmd "$python_bin" -m pip install --upgrade "${PACKAGE_NAME}"; then
        log_success "Successfully installed ${PACKAGE_NAME} using pip."
        return 0
    else
        log_error "Failed to install ${PACKAGE_NAME} using pip."
        if [[ "$MODE" == "pip" ]]; then
            exit 1
        fi
        return 1
    fi
}

install_git() {
    log_step "Checking for 'uv' and 'git'..."
    if ! command -v uv >/dev/null 2>&1; then
        log_error "'uv' binary not found in PATH."
        echo "Please install uv (https://github.com/astral-sh/uv)." >&2
        exit 1
    fi

    if ! command -v git >/dev/null 2>&1; then
        log_error "'git' binary not found in PATH."
        echo "Please install git." >&2
        exit 1
    fi

    log "Found uv: $(command -v uv)"
    log "Found git: $(command -v git)"
    log_step "Installing ${PACKAGE_NAME} from Git repository via uv tool (${GIT_URL})..."
    if run_cmd uv tool install "${GIT_URL}" --with "${GIT_URL_SDK}"; then
        log_success "Successfully installed ${PACKAGE_NAME} from Git repository via uv tool."
        return 0
    else
        log_error "Failed to install ${PACKAGE_NAME} from Git repository."
        exit 1
    fi
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
            log_error "Could not install ${PACKAGE_NAME} via uv, pipx, or pip."
            echo "" >&2
            echo "No working package manager was found. Please do one of the following:" >&2
            echo "  1. Install uv (recommended): curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
            echo "  2. Install pip (e.g. 'sudo apt install python3-pip')" >&2
            echo "  3. Install pipx" >&2
            exit 1
        fi
        ;;
esac

if [[ "$DRY_RUN" == "false" ]]; then
    log ""
    log_success "nodepick.ai CLI installation process completed!"
    if ! command -v np >/dev/null 2>&1; then
        log_warn "'np' command was not found in your current PATH."
        log_warn "You may need to add '~/.local/bin' to your PATH:"
        log_warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    else
        log "Run 'np --help' to verify the installation."
    fi
fi
