# Flow Studio & Extensions

Flow Studio is a companion UI and editor integration for managing specs, chapter progress, line-anchored review comments, bundle notes, and cross-harness runs across every supported harness — zero Python or DuckDB setup required by default.

## Host Surfaces

1. **Google Antigravity MCP App (`mcp_config.json` + `sidecars/studio/mcp-server.mjs`)**:
   - **Side Panel & Full Page (`flow_studio`, `ui://flow/studio.html`)**: Self-contained single-file MCP App (`@modelcontextprotocol/ext-apps`) exposed in Antigravity App and Antigravity Web via `com.google.antigravity/ui` (`aux_pane` and `global` entrypoints) with zero local ports or cookies. Adapts live to host light/dark theme tokens, attaches spec context/notes to the user's next prompt (`updateModelContext`), and opens workspace files in the side panel (`com.google.antigravity/toggle-aux-pane`).
   - **Inline Status Card (`flow_status`, `ui://flow/status-card.html`)**: Compact inline chat card showing active specs, verified task progress, and next ready task; falls back to plain-text JSON on `agy` CLI and non-UI MCP clients.
2. **Standalone Loopback Server (`npx --yes --package github:cofin/flow flow-studio` / `make studio`)**:
   - Binds to `127.0.0.1` (`--port 0` dynamic port or `$FLOW_STUDIO_PORT`) with Server-Sent Events (`/api/events`) for **Claude Code**, **Codex CLI**, **OpenCode V2**, or browser tabs alongside any terminal harness.
3. **VS Code & Cursor Extension (`vscode-extension/`)**:
   - **Inline Spec Review (`CommentController`)**: Add, reply to, resolve, and reopen review threads directly in the editor gutter of `.agents/bundles/specs/**/*.md` and bundle notes, persisted to `<git-common-dir>/spec-feedback/` and dispatched to `/flow:revise`.
   - **Active-Flow Status Bar & Specs Explorer**: Displays active spec progress and open review notes in the status bar with a quick-action menu. Also provides a cached `Specs & Tasks` tree, `spec.md` CodeLenses (`Implement`, `Review`, `Sync`, `Revise`, `Open in Flow Studio`), pure-Node bundle search (`flow.searchDocs`), and an optional Studio webview.
   - **Installation**: Run `npx --yes --package github:cofin/flow flow-studio-vscode [--target vscode|cursor|windsurf|positron|all]` (or `make install-vscode`), then run `Developer: Reload Window`. Existing installs are kept up to date automatically via `--update-only` on `SessionStart`.

## Spec Review & Authoring Loop

- **Create Spec / PRD (`+ New Spec`)**: Scaffolds `.agents/bundles/specs/<flow_id>/spec.md` (and optional `chapters/` directory) on disk and dispatches `/flow:spec` or `/flow:prd` to plan the full spec.
- **Line-Anchored Review Comments & Multi-Branch Sync**: Attach review notes in VS Code gutters or Flow Studio's `Reader` / `Source` views. Notes store under `<git-common-dir>/spec-feedback/<flow_id>/<author_slug>.json` (with `<spec_dir>/feedback/` fallback outside Git), merge across sibling stores, sync with spec PRs (`flow spec pr`), and dispatch `/flow:revise`.

## Instant Bundle Search & Optional DuckDB Catalog (`flow-catalog`)

Markdown files under `.agents/bundles/` remain the single source of truth.
By default, Flow Studio and the VS Code extension use the zero-Python **pure-Node BM25 + bundle-graph** engine (`sidecars/studio/knowledge/catalog.mjs`) for instant local/sibling search, reverse provenance, and citation drift checks.

Optional **DuckDB + EmbeddingGemma** hybrid semantic search (`tools/catalog/`) and Google Knowledge Catalog (`kcmd`) compatibility remain available strictly as opt-in features (`FLOW_ENABLE_DUCKDB=1` or explicit CLI invocation):

```bash
uv sync --group catalog
FLOW_ENABLE_DUCKDB=1 uv run flow-catalog index .
FLOW_ENABLE_DUCKDB=1 uv run flow-catalog search "hybrid catalog" --mode hybrid
```

## Native Python Runner Detection

Flow Studio probes target workspaces in priority order (`uv.lock` &rarr; `[tool.hatch]` &rarr; `pdm.lock` &rarr; `poetry.lock` &rarr; `Pipfile.lock` &rarr; `.venv` &rarr; `python3`) to run `[project.scripts]` entrypoints without publishing to PyPI.

## Cross-Harness Execution Modes & Loopback A2A

When dispatching a task or second-opinion review to `claude`, `codex`, `opencode`, `cursor-agent`, or `agy`, pick the execution mode via `flow.executionMode` or the per-dispatch toggle:

| Mode | Workspace Isolation | Best For |
| --- | --- | --- |
| `direct-workspace` (Default) | Runs in the repository root with an advisory active-writer banner if another turn is mid-flight | Sequential implementation and interactive handoffs across harnesses |
| `worktree-isolated` | Creates a temporary Git worktree under `.agents/scratch/worktrees/<harness>-<runId>/` | Parallel cross-harness tasks without index or working-tree collisions |
| `read-only` | Enforces read-only sandbox flags (`--sandbox read-only` / disallowed write tools) | Cross-model spec critiques and independent code reviews |

The standalone Studio server also exposes a loopback-only **A2A v1** facade (`GET /.well-known/agent-card.json` and `POST /a2a` supporting `message/send`, `tasks/get`, and `tasks/cancel`).
