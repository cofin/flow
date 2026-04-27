#!/usr/bin/env bash
# Compatibility wrapper for the Python Codex package materializer.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "${repo_root}/tools/sync-codex-package.py" "$@"
