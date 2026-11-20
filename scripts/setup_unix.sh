#!/usr/bin/env bash
# Sets up VeriGreen-ops on macOS / Linux: creates .venv, installs Python
# dependencies, and symlinks .claude/skills and .gemini/skills -> ../skills.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

echo "==> VeriGreen-ops Unix Setup"
echo "    Repository Root: ${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "ERROR: python3 not found. Please install Python 3.11+." >&2
    exit 1
fi

"${PYTHON_BIN}" -c "import sys; assert sys.version_info >= (3, 11), f'Python 3.11+ required, found {sys.version}'"

VENV_DIR="${REPO_ROOT}/.venv"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "==> Creating virtual environment (.venv)..."
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
else
    echo "==> Existing .venv detected."
fi

echo "==> Installing Python requirements..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${REPO_ROOT}/requirements.txt"

mkdir -p skills src data/raw_docs data/sample output .claude .gemini

link_skills() {
    local link_path="$1"
    if [[ -e "${link_path}" && ! -L "${link_path}" ]]; then
        echo "ERROR: ${link_path} exists and is not a symlink. Remove or rename it manually." >&2
        exit 1
    fi
    ln -sfn ../skills "${link_path}"
    echo "==> Symlink created: ${link_path} -> ../skills"
}

link_skills "${REPO_ROOT}/.claude/skills"
link_skills "${REPO_ROOT}/.gemini/skills"

echo ""
echo "Setup complete!"
echo "Next steps:"
echo "  1. Activate venv (optional): source .venv/bin/activate"
echo "  2. Generate sample corpus:   .venv/bin/python scripts/create_sample_data.py"
echo "  3. Launch your CLI agent:    claude   (or: gemini)"
