# Flow Studio for VS Code & Cursor

**Flow Studio** brings multi-harness Spec-Driven Development (`OKF v0.2`) directly into **VS Code**, **Cursor**, **Windsurf**, and **Positron**. It includes active-workspace spec planning (`/flow:spec`, `/flow:prd`, `/flow:revise`, `/flow:implement`), line-anchored review comments, and a local **DuckDB + EmbeddingGemma** hybrid Knowledge Catalog.

## Features

- **Active-Workspace Tracking**: Automatically follows the workspace folder of the active editor and multi-root workspace changes. Keeps the Activity Bar trees (`Specs & Chapters`, `Knowledge Catalog`) and Studio webview synchronized with your active project.
- **Direct Spec & PRD Authoring (`/flow:spec` & `/flow:prd`)**: Scaffold `.agents/bundles/specs/<flow_id>/spec.md` specs or dispatch `/flow:spec` and `/flow:prd` directly into your configured AI harness (`copilot`, `cursor`, `claude`, `codex`, `opencode`, or `agy`).
- **Line-Anchored Spec Review (`/flow:revise`)**: Attach review comments to exact line numbers on any `spec.md` or OKF knowledge document and send structured batch revisions to `/flow:revise`.
- **Quiet `spec.md` CodeLenses**: Inline `Open in Flow Studio`, `Implement <chapter>`, and `Run Independent Review` actions at the top of `.agents/bundles/specs/**/spec.md`.

## Installation

### End Users (No Repository Clone Required)

1. **Automatic via Flow Agent Plugin (`SessionStart` Hook)**: Installing the Flow plugin in Cursor, Claude Code, OpenCode, or Google Antigravity runs `hooks/session-start.{sh,ps1}`. The hook installs and registers `cofin.flow-studio` into any detected `~/.vscode/extensions`, `~/.cursor/extensions`, `~/.windsurf/extensions`, or `~/.positron/extensions` directory.
2. **One-Command Remote Install via `npx`**: Install or update `cofin.flow-studio` directly from GitHub without cloning the repository:

```bash
# Auto-detect installed VS Code-compatible editors and install cofin.flow-studio
npx --yes --package github:cofin/flow flow-studio-vscode

# Target a specific editor (vscode | vscode-insiders | cursor | windsurf | positron | all)
npx --yes --package github:cofin/flow flow-studio-vscode --target cursor
```

### Contributors (From a Local Checkout)

From a local checkout of [`cofin/flow`](https://github.com/cofin/flow), run:

```bash
# Bundle and install into detected editors
make install-vscode

# Or symlink live checkout for extension development
node ./vscode-extension/install.mjs --link
```

Reload the window (`Developer: Reload Window` in the Command Palette) after installing.
