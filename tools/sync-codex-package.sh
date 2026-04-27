#!/usr/bin/env bash
# Mirror repo-root sources into the Codex marketplace package at
# .agents/plugins/plugins/flow/. Codex 0.125 cannot follow symlinks out of an
# installed plugin package, so the package must contain real copies.
#
#   .codex-plugin/, skills/  -> full directory mirror
#   commands/flow-*.md       -> Codex-format command markdowns only; the
#                               commands/flow/*.toml subdirectory is
#                               Gemini-CLI-only and is intentionally excluded.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package="${repo_root}/.agents/plugins/plugins/flow"

for dir in .codex-plugin skills; do
  src="${repo_root}/${dir}"
  dst="${package}/${dir}"
  if [[ ! -d "${src}" ]]; then
    echo "error: source ${src} is missing" >&2
    exit 1
  fi
  rm -rf "${dst}"
  cp -a "${src}" "${dst}"
done

src_cmds="${repo_root}/commands"
dst_cmds="${package}/commands"
if [[ ! -d "${src_cmds}" ]]; then
  echo "error: source ${src_cmds} is missing" >&2
  exit 1
fi
rm -rf "${dst_cmds}"
mkdir -p "${dst_cmds}"
shopt -s nullglob
for f in "${src_cmds}"/flow-*.md; do
  cp -a "${f}" "${dst_cmds}/"
done
shopt -u nullglob

echo "synced .codex-plugin/, commands/flow-*.md, skills/ -> ${package}"
