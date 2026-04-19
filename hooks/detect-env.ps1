# PowerShell environment detection for Flow
# Mirror of detect-env.sh logic for native Windows support

Write-Host "## Flow Environment Context"

# 1. Beads Backend Detection
$beads_bd = Get-Command bd -ErrorAction SilentlyContinue
$beads_br = Get-Command br -ErrorAction SilentlyContinue

if ($beads_bd) {
    Write-Host "- **Beads Backend**: Official (bd)"
} elseif ($beads_br) {
    Write-Host "- **Beads Backend**: Compatibility (br)"
} else {
    Write-Host "- **Beads Backend**: None (markdown-only mode)"
}

# 2. Flow Root Detection
$root = ".agents/"
if (Test-Path "setup-state.json") {
    $setup_state = Get-Content "setup-state.json" | ConvertFrom-Json
    if ($setup_state.root_directory) {
        $root = $setup_state.root_directory
    }
} elseif (Test-Path ".agents/setup-state.json") {
    $setup_state = Get-Content ".agents/setup-state.json" | ConvertFrom-Json
    if ($setup_state.root_directory) {
        $root = $setup_state.root_directory
    }
}
Write-Host "- **Flow Root**: $root"

# 3. Tooling Detection
$tools = @()
if (Get-Command uv -ErrorAction SilentlyContinue) { $tools += "uv" }
if (Get-Command bun -ErrorAction SilentlyContinue) { $tools += "bun" }
if (Get-Command make -ErrorAction SilentlyContinue) { $tools += "make" }
if ($tools.Count -gt 0) {
    Write-Host ("- **Tooling**: " + ($tools -join " "))
}

# 4. Git Context
if (git rev-parse --is-inside-work-tree 2>$null) {
    $branch = git rev-parse --abbrev-ref HEAD
    Write-Host "- **Git Branch**: $branch"
    if (git check-ignore -q .agents/ 2>$null) {
        Write-Host "- **Git Visibility**: .agents/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
    } else {
        Write-Host "- **Git Visibility**: .agents/ is Tracked"
    }
}

# 5. Knowledge Inventory
if ((Test-Path ".agents/knowledge") -or (Test-Path ".agents/patterns.md")) {
    Write-Host "- **Knowledge Base**: Active"
    if (Test-Path ".agents/patterns.md") { Write-Host "  - Patterns: .agents/patterns.md" }
    if (Test-Path ".agents/knowledge") {
        $chapters = Get-ChildItem ".agents/knowledge/*.md" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
        if ($chapters) {
            Write-Host ("  - Chapters: " + ($chapters -join " "))
        }
    }
} else {
    Write-Host "- **Knowledge Base**: Empty"
}

# 6. Flow Mandate
Write-Host ""
Write-Host "### Flow Mandate"
Write-Host "- **Zero-Ambiguity Standard**: All PRDs MUST be Master Roadmaps (Sagas). ALL child plans MUST be 'High-Definition Worksheets' with exact line numbers and code snippets."
Write-Host "- **Synthesis Mandate**: You are responsible for the knowledge lifecycle. Autonomously identify patterns and synthesize learnings into formal guides in ".agents/knowledge/"."
Write-Host "- **Cleanup Mandate**: Regularly run \"/flow:cleanup\" to re-assess, reorganize, and optimize the project context. Verify task status against SOURCE CODE."
Write-Host "- **Inherit First**: READ `patterns.md` and `knowledge/` chapters before planning. Adhere to current state truth."
Write-Host "- **Deep Research First**: Do NOT defer research to implementation. ALL analysis and architectural decisions MUST be completed upfront."
Write-Host "- **Stateless Executor Test**: A plan is only 'Ready' if an agent with ZERO context can implement it 100% correctly based ONLY on the worksheet."
Write-Host "- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the `flow` skill."
Write-Host "- **Sync Requirement**: Run \"/flow:sync\" after any change to Beads state or project structure."
