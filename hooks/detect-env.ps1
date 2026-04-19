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
    Write-Host "- **Beads Backend**: Missing (None)"
}

# 2. Project Config Detection
$ROOT_DIR = ".agents"
if (Test-Path ".agents/setup-state.json") {
    try {
        $setup_state = Get-Content ".agents/setup-state.json" | ConvertFrom-Json
        if ($setup_state.root_directory) {
            $ROOT_DIR = $setup_state.root_directory
        }
        Write-Host "- **Flow Root**: $ROOT_DIR"
    } catch {
        Write-Host "- **Flow Root**: .agents/ (default)"
    }
} else {
    Write-Host "- **Flow Root**: .agents/ (default)"
}

# 3. Tooling Detection
$tools = @()
if (Get-Command uv -ErrorAction SilentlyContinue) { $tools += "uv" }
if (Get-Command bun -ErrorAction SilentlyContinue) { $tools += "bun" }
if (Get-Command ruff -ErrorAction SilentlyContinue) { $tools += "ruff" }
if (Get-Command make -ErrorAction SilentlyContinue) { $tools += "make" }
if (Get-Command railway -ErrorAction SilentlyContinue) { $tools += "railway" }

if ($tools.Count -gt 0) {
    Write-Host ("- **Tooling**: " + ($tools -join " "))
} else {
    Write-Host "- **Tooling**: None"
}

# 4. Git Context
if (git rev-parse --is-inside-work-tree 2>$null) {
    $branch = git symbolic-ref --short HEAD 2>$null
    if (-not $branch) { $branch = "unborn" }
    Write-Host "- **Git Branch**: $branch"
    if (git check-ignore -q "$ROOT_DIR/" 2>$null) {
        Write-Host "- **Git Visibility**: $ROOT_DIR/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
    } else {
        Write-Host "- **Git Visibility**: $ROOT_DIR/ is Tracked"
    }
}

# 5. Project Identity
$product_file = "$ROOT_DIR/product.md"
if (Test-Path $product_file) {
    Write-Host ""
    Write-Host "### Project Identity"
    Get-Content $product_file | Where-Object { $_ -match "^[^#]" } | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
}

# 6. Context Index
Write-Host ""
Write-Host "### Project Context Index"
Write-Host "- **Product Definition**: $ROOT_DIR/product.md"
Write-Host "- **Tech Stack**: $ROOT_DIR/tech-stack.md"
Write-Host "- **Workflow**: $ROOT_DIR/workflow.md"
Write-Host "- **Patterns**: $ROOT_DIR/patterns.md"
Write-Host "- **Flow Registry**: $ROOT_DIR/flows.md"

# 7. Active Work
Write-Host ""
Write-Host "### Active Work"
if ($beads_bd) {
    try {
        $ready = bd ready --json | ConvertFrom-Json | Select-Object -First 3
        if ($ready) {
            $ready_json = $ready | ConvertTo-Json -Compress
            Write-Host "- **Ready Tasks (Top 3)**: $ready_json"
        } else {
            Write-Host "- **Ready Tasks**: None"
        }
    } catch {
        Write-Host "- **Ready Tasks**: None"
    }
} elseif ($beads_br) {
    $ready = br ready | Select-Object -First 3
    if ($ready) {
        Write-Host "- **Ready Tasks (Top 3)**:"
        $ready | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "- **Ready Tasks**: None"
    }
} else {
    Write-Host "- **Status**: No active backend for task tracking."
}

# 8. Essential Truths (Priming)
Write-Host ""
Write-Host "### Core Project Truths"

function Extract-Truths($file) {
    if (Test-Path $file) {
        $content = Get-Content $file
        $in_truth = $false
        $truths = @()
        foreach ($line in $content) {
            if ($line -match "<!-- truth: start -->") { $in_truth = $true; continue }
            if ($line -match "<!-- truth: end -->") { $in_truth = $false; continue }
            if ($in_truth) { $truths += $line }
        }
        if ($truths.Count -gt 0) {
            $truths | ForEach-Object { Write-Host "  $_" }
            return $true
        }
    }
    return $false
}

$tech_stack_file = "$ROOT_DIR/tech-stack.md"
Write-Host "- **Tech Stack Summary**:"
if (-not (Extract-Truths $tech_stack_file)) {
    if (Test-Path $tech_stack_file) {
        Get-Content $tech_stack_file | Where-Object { $_ -match "^-" } | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
    }
}

$workflow_file = "$ROOT_DIR/workflow.md"
Write-Host "- **Canonical Commands**:"
if (-not (Extract-Truths $workflow_file)) {
    if (Test-Path $workflow_file) {
        # Fallback to dev commands section if markers missing
        $wf_content = Get-Content $workflow_file
        $found_section = $false
        $count = 0
        foreach ($line in $wf_content) {
            if ($line -match "## Development Commands") { $found_section = $true; continue }
            if ($found_section) {
                if ($line -match "^##") { break }
                if ($line -trim() -and $line -notmatch "^#") {
                    Write-Host "  $line"
                    $count++
                    if ($count -ge 15) { break }
                }
            }
        }
    }
}

$patterns_file = "$ROOT_DIR/patterns.md"
Write-Host "- **Critical Patterns**:"
if (-not (Extract-Truths $patterns_file)) {
    if (Test-Path $patterns_file) {
        Get-Content $patterns_file | Where-Object { $_ -match "^-" } | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
    }
}

# 9. Knowledge Inventory
if ((Test-Path "$ROOT_DIR/knowledge") -or (Test-Path "$ROOT_DIR/patterns.md")) {
    Write-Host ""
    Write-Host "### Knowledge Base"
    if (Test-Path "$ROOT_DIR/patterns.md") { Write-Host "- **Consolidated Patterns**: $ROOT_DIR/patterns.md" }
    if (Test-Path "$ROOT_DIR/knowledge") {
        $chapters = Get-ChildItem "$ROOT_DIR/knowledge/*.md" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
        if ($chapters) {
            Write-Host ("- **Knowledge Chapters**: " + ($chapters -join " "))
        }
    }
}

# 10. Flow Mandate
Write-Host ""
Write-Host "### Flow Mandate"
Write-Host "- **Zero-Ambiguity Standard**: All PRDs MUST be Master Roadmaps (Sagas). ALL child plans MUST be 'High-Definition Worksheets' with exact line numbers and code snippets."
Write-Host "- **Synthesis Mandate**: You are responsible for the knowledge lifecycle. Autonomously identify patterns and synthesize learnings into formal guides in `"$ROOT_DIR/knowledge/"`."
Write-Host "- **Cleanup Mandate**: Regularly run \"/flow:cleanup\" to re-assess, reorganize, and optimize the project context. Verify task status against SOURCE CODE."
Write-Host "- **Inherit First**: READ `patterns.md` and `knowledge/` chapters before planning. Adhere to current state truth."
Write-Host "- **Deep Research First**: Do NOT defer research to implementation. ALL analysis and architectural decisions MUST be completed upfront."
Write-Host "- **Stateless Executor Test**: A plan is only 'Ready' if an agent with ZERO context can implement it 100% correctly based ONLY on the worksheet."
Write-Host "- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the `flow` skill."
Write-Host "- **Sync Requirement**: Run \"/flow:sync\" after any change to Beads state or project structure."
