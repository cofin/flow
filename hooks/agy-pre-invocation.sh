#!/usr/bin/env bash
# Static Flow PreInvocation router. This entrypoint reads no project state.
set -eu

printf '%s\n' '{"injectSteps":[{"ephemeralMessage":"Flow continuity is direct Markdown. Resolve the configured root from .agents/setup-state.json (default .agents/), read its index.md, then follow skills/flow/references/state.md. After compaction or session loss, use the journal-first direct-read continuity contract there; never treat hook context as authority."}]}'
