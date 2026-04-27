#!/usr/bin/env bash
# Assemble the Codex marketplace package at <repo-root>/plugins/flow/.
#
# Codex resolves marketplace `source.path` relative to the marketplace ROOT
# (the repo), not relative to the marketplace.json file. So `./plugins/flow`
# in .agents/plugins/marketplace.json must exist at <repo-root>/plugins/flow/.
#
# We use symlinks back to the repo-root sources to avoid duplication:
#   plugins/flow/.codex-plugin -> ../../.codex-plugin   (whole-dir symlink)
#   plugins/flow/skills        -> ../../skills          (whole-dir symlink)
#   plugins/flow/commands/<f>  -> ../../../commands/<f> (per-file symlinks
#                                  so the commands/flow/*.toml Gemini-CLI
#                                  files are excluded from the Codex package)
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
package="${repo_root}/plugins/flow"

mkdir -p "${package}"
rm -rf "${package}/.codex-plugin" "${package}/skills" "${package}/commands"

ln -s ../../.codex-plugin "${package}/.codex-plugin"
ln -s ../../skills "${package}/skills"

mkdir -p "${package}/commands"
shopt -s nullglob
for f in "${repo_root}/commands"/flow-*.md; do
  name="$(basename "${f}")"
  ln -s "../../../commands/${name}" "${package}/commands/${name}"
done
shopt -u nullglob

echo "assembled package at ${package}"
