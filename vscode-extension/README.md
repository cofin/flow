# Flow Studio for VS Code & Cursor

**Flow Studio** brings editor-native Spec-Driven Development (`OKF v0.2`) directly into **VS Code**, **Cursor**, **Windsurf**, and **Positron** — without requiring Python, DuckDB, or external services.

## Features

- **Native Inline Spec Review (`CommentController`)**: Add, reply to, resolve, and reopen line-anchored review notes directly in the gutter of any `.agents/bundles/specs/**/*.md` or bundle doc. Notes persist to Flow's out-of-tree `SpecFeedbackStore` (`<git-common-dir>/spec-feedback/`) and dispatch straight into `/flow:revise`.
- **Active-Flow Status Bar & Quick Actions**: Displays the active spec, verified task count, and unresolved review notes in the status bar with a single-click action menu (`Sync`, `Implement`, `Review`, `Revise`, `Search Bundle Notes`, `Open Flow Studio`).
- **Specs & Tasks Explorer**: Browse specs, chapters, and tasks with status icons, open Markdown worksheets directly in the editor, and launch implement/review/sync actions inline.
- **Actionable `spec.md` CodeLenses**: Inline `Implement <chapter>`, `Review Flow`, `Sync`, `Revise (N open notes)`, and `Open in Flow Studio` links at the top of every spec.
- **Optional Studio Webview**: Open the full multi-branch spec/DAG/activity dashboard on demand inside a CSP-hardened VS Code Webview.

## Installation

### One-Command Remote Install via `npx`

```bash
# Auto-detect installed VS Code-compatible editors and install cofin.flow-studio
npx --yes --package github:cofin/flow flow-studio-vscode

# Target a specific editor (vscode | vscode-insiders | cursor | windsurf | positron | all)
npx --yes --package github:cofin/flow flow-studio-vscode --target cursor
```

### Contributors (From a Local Checkout)

```bash
# Bundle and install into detected editors
make install-vscode

# Or symlink live checkout for extension development
node ./vscode-extension/install.mjs --link
```

Reload the window (`Developer: Reload Window` in the Command Palette) after installing. Existing installs are kept up to date automatically on `SessionStart` (`--update-only`).
