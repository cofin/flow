# Flow Studio for VS Code & Cursor

**Flow Studio** brings multi-harness Spec-Driven Development (`OKF v0.2`), active-workspace spec planning (`/flow:spec`, `/flow:prd`, `/flow:revise`, `/flow:implement`), line-anchored specification review comments, and the local **DuckDB + EmbeddingGemma** hybrid Knowledge Catalog directly into **VS Code**, **Cursor**, **Windsurf**, and **Positron**.

## Features

- **Active-Workspace Tracking**: Automatically follows the workspace folder of the active editor (and multi-root workspace changes), keeping the Activity Bar trees (`Specs & Chapters`, `Knowledge Catalog`) and Studio webview synchronized with your active project.
- **Direct Spec & PRD Authoring (`/flow:spec` & `/flow:prd`)**: Scaffold `.agents/bundles/specs/<flow_id>/spec.md` blueprints or dispatch `/flow:spec` and `/flow:prd` directly into your configured AI harness (`copilot`, `cursor`, `claude`, `codex`, `opencode`, or `agy`).
- **Line-Anchored Spec Review (`/flow:revise`)**: Attach review comments to exact line numbers on any `spec.md` or OKF knowledge document and send structured batch revisions to `/flow:revise`.
- **Quiet `spec.md` CodeLenses**: Inline `Open in Flow Studio`, `Implement <chapter>`, and `Run Zero-Context Review` actions at the top of `.agents/bundles/specs/**/spec.md`.

## Installation

From a local checkout of [`cofin/flow`](https://github.com/cofin/flow), run:

```bash
make install-vscode
```

Or invoke the zero-dependency installer directly with Node.js (`>= 20`):

```bash
# Auto-detect and install into ~/.vscode/extensions, ~/.cursor/extensions, etc.
node ./vscode-extension/install.mjs

# Target a specific editor (vscode | cursor | windsurf | positron | all)
node ./vscode-extension/install.mjs --target cursor

# Symlink live checkout for extension development
node ./vscode-extension/install.mjs --link
```

Reload the window (`Developer: Reload Window` in the Command Palette) after installing.
