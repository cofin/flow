#!/usr/bin/env bash
# Mirror repo-root .codex-plugin/, commands/, and skills/ into the Codex
# marketplace package at .agents/plugins/plugins/flow/. Codex 0.125 cannot
# follow symlinks out of an installed plugin package, so the package must
# contain real copies of these directories.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package="${repo_root}/.agents/plugins/plugins/flow"

for dir in .codex-plugin commands skills; do
  src="${repo_root}/${dir}"
  dst="${package}/${dir}"
  if [[ ! -d "${src}" ]]; then
    echo "error: source ${src} is missing" >&2
    exit 1
  fi
  rm -rf "${dst}"
  cp -a "${src}" "${dst}"
done

echo "synced .codex-plugin/, commands/, skills/ -> ${package}"
