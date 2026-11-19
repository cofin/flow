# Flow Studio & Local Knowledge Catalog

Flow Studio is a companion UI for managing specs, chapter progress, line-anchored review comments, cross-harness runs, and a derived local **DuckDB + EmbeddingGemma** hybrid Knowledge Catalog across every supported harness.

## Host Surfaces

1. **Google Antigravity Sidecar (`sidecars/studio/`)**:
   - **AuxPane Companion (`/`)**: Compact active-chapter progress, next-step launcher, and quick Studio opener.
   - **Full Studio (`/dashboard`, `sidecar://flow/studio/dashboard`)**: Four views—`Roadmap`, `Spec & Review`, `Knowledge Catalog`, and `Activity & Hooks`—adapted to host light and dark CSS tokens via `/preload.js`.
   - **Workspace-Bound Dispatch**: Launches new conversations bound to the target repository via loopback `LanguageServerService` (`StartCascade` + `SendUserCascadeMessage`) instead of inheriting the plugin checkout directory.
2. **Standalone Loopback Server (`npx --yes --package github:cofin/flow flow-studio` / `make studio`)**:
   - Binds to `127.0.0.1` (`--port 0` dynamic port by default) with Server-Sent Events (`/api/events`) for **Claude Code**, **Codex CLI**, **OpenCode V2**, or browser tabs alongside any terminal harness.
3. **VS Code & Cursor Extension (`vscode-extension/`)**:
   - Contributes the `Flow Studio` Activity Bar container (`Specs & Chapters` and `Knowledge Catalog` tree views), quiet `spec.md` CodeLenses (`Open in Flow Studio`, `Implement <chapter>`, `Independent Review`), and a Webview Studio panel sharing `StudioApiService` with `sidecars/studio/router.mjs`.
   - Follows the active editor's workspace folder (and multi-root changes), routing prompts to GitHub Copilot Chat, Cursor Chat, Claude Code, Codex CLI, OpenCode, or Google Antigravity per `flow.defaultHarness` and `flow.executionMode`.
   - **Installation**: Installed into detected `~/.vscode/extensions` and `~/.cursor/extensions` on `SessionStart` (`hooks/session-start.{sh,ps1}`), or run `npx --yes --package github:cofin/flow flow-studio-vscode [--target vscode|cursor|windsurf|positron|all]` (or `make install-vscode`), then run `Developer: Reload Window`.

## Spec Review & Authoring Loop

- **Create Spec / PRD (`+ New Spec`)**: Scaffolds `.agents/bundles/specs/<flow_id>/spec.md` (and optional `chapters/` directory) on disk and dispatches `/flow:spec` or `/flow:prd` to plan the full spec.
- **Line-Anchored Review Comments & Multi-Branch Sync**: Select any block or range in `Reader` (or line in `Source`) to add review notes under `<git-common-dir>/spec-feedback/<flow_id>/<author_slug>.json`. Sibling feedback stores merge on read, with a `<spec_dir>/feedback/` fallback outside Git. Browse other branches, pull or publish spec PRs (`flow spec pr`, `flow spec share`), and dispatch `/flow:revise`.

## Derived Hybrid DuckDB Knowledge Catalog (`flow-catalog`)

Markdown files under `.agents/bundles/` remain the single source of truth.
The DuckDB index (`~/.cache/flow/catalog.duckdb` or `$FLOW_CATALOG_DB`) is a disposable, rebuildable read model built with `sqlspec[duckdb,msgspec]`:

- **Hybrid Retrieval (`RRF`)**: Combines DuckDB `fts` (`pragma_create_fts_index` + pure-SQL Okapi BM25 fallback) with cosine vector similarity (`array_cosine_distance` over `FLOAT[256]`) fused via Reciprocal Rank Fusion (`k = 60`).
- **Local `EmbeddingGemma-300m` ONNX**: Uses quantized `onnx-community/embeddinggemma-300m-ONNX` via `fastembed` with task prefixes and Matryoshka `256`-dim L2-normalized truncation. Embeddings are cached by content SHA-256 in `embedding_cache` and fall back to BM25-only when absent.
- **Reverse Provenance & Drift Checks**: Indexes `sources[].resource` (`path/to/file::Symbol`) into `entry_sources` to answer *"Which specs and ADRs cite this module?"* and surface missing source citations.

Install optional catalog acceleration dependencies in a Python environment:

=== "uv"

    ```bash
    uv sync --group catalog
    uv run flow-catalog index .
    uv run flow-catalog search "hybrid catalog" --mode hybrid
    ```

=== "pip"

    ```bash
    pip install "sqlspec[duckdb,msgspec]>=0.38.0" "fastembed>=0.6.0" "msgspec>=0.19.0"
    flow-catalog index .
    ```

=== "pdm"

    ```bash
    pdm add -G catalog "sqlspec[duckdb,msgspec]>=0.38.0" "fastembed>=0.6.0" "msgspec>=0.19.0"
    pdm run flow-catalog index .
    ```

=== "poetry"

    ```bash
    poetry add --group catalog "sqlspec[duckdb,msgspec]>=0.38.0" "fastembed>=0.6.0" "msgspec>=0.19.0"
    poetry run flow-catalog index .
    ```

## Native Python Runner Detection

Flow Studio probes target workspaces in priority order (`uv.lock` &rarr; `[tool.hatch]` &rarr; `pdm.lock` &rarr; `poetry.lock` &rarr; `Pipfile.lock` &rarr; `.venv` &rarr; `python3`).
This runs `[project.scripts]` entrypoints and `flow-catalog` through the repository's native environment manager without publishing to PyPI.

## Cross-Harness Execution Modes & Loopback A2A

When dispatching a task or second-opinion review to `claude`, `codex`, `opencode`, `cursor-agent`, or `agy`, pick the execution mode via `flow.executionMode` or the per-dispatch toggle:

| Mode | Workspace Isolation | Best For |
| --- | --- | --- |
| `direct-workspace` (Default) | Runs in the repository root with an advisory active-writer banner if another turn is mid-flight | Sequential implementation and interactive handoffs across harnesses |
| `worktree-isolated` | Creates a temporary Git worktree under `.agents/scratch/worktrees/<harness>-<runId>/` | Parallel cross-harness tasks without index or working-tree collisions |
| `read-only` | Enforces read-only sandbox flags (`--sandbox read-only` / disallowed write tools) | Cross-model spec critiques and independent code reviews |

The standalone Studio server and Antigravity sidecar also expose a loopback-only **A2A v1** facade (`GET /.well-known/agent-card.json` and `POST /a2a` supporting `message/send`, `tasks/get`, and `tasks/cancel`).
