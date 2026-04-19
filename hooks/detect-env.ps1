# PowerShell environment detection for Flow
# Mirror of detect-env.sh logic for native Windows support

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-BeadsBackend {
    Write-Host "## Flow Environment Context"
    $beads_bd = Get-Command bd -ErrorAction SilentlyContinue
    $beads_br = Get-Command br -ErrorAction SilentlyContinue

    if ($beads_bd) {
        Write-Host "- **Beads Backend**: Official (bd)"
        return "bd"
    } elseif ($beads_br) {
        Write-Host "- **Beads Backend**: Compatibility (br)"
        return "br"
    } else {
        Write-Host "- **Beads Backend**: Missing (None)"
        return $null
    }
}

function Get-FlowRoot {
    $rootDir = ".agents"
    $setupStateFile = ".agents/setup-state.json"
    if (Test-Path $setupStateFile) {
        try {
            $setupState = Get-Content $setupStateFile -Raw | ConvertFrom-Json
            if ($setupState.root_directory) {
                $rootDir = $setupState.root_directory
                Write-Host "- **Flow Root**: $rootDir"
            } else {
                Write-Host "- **Flow Root**: .agents/ (default, missing in setup-state)"
            }
        } catch {
            Write-Host "- **Flow Root**: .agents/ (default, error parsing setup-state)"
        }
    } else {
        Write-Host "- **Flow Root**: .agents/ (default)"
    }
    return $rootDir
}

function Get-Tooling {
    $toolsToCheck = @("uv", "bun", "ruff", "make", "railway")
    $availableTools = @()
    foreach ($tool in $toolsToCheck) {
        if (Get-Command $tool -ErrorAction SilentlyContinue) {
            $availableTools += $tool
        }
    }

    if ($availableTools.Count -gt 0) {
        Write-Host ("- **Tooling**: " + ($availableTools -join " "))
    } else {
        Write-Host "- **Tooling**: None"
    }
}

function Get-GitContext($rootDir) {
    try {
        if (git rev-parse --is-inside-work-tree 2>$null) {
            $branch = git symbolic-ref --short HEAD 2>$null
            if (-not $branch) { $branch = "unborn" }
            Write-Host "- **Git Branch**: $branch"
            
            if (git check-ignore -q "$rootDir/" 2>$null) {
                Write-Host "- **Git Visibility**: $rootDir/ is GIT-IGNORED (Use 'cat' or bypass ignore filters)"
            } else {
                Write-Host "- **Git Visibility**: $rootDir/ is Tracked"
            }
        }
    } catch {
        # Git failed or not installed, skip silently
    }
}

function Get-ProjectIdentity($rootDir) {
    $productFile = Join-Path $rootDir "product.md"
    if (Test-Path $productFile) {
        Write-Host ""
        Write-Host "### Project Identity"
        try {
            Get-Content $productFile | Where-Object { $_ -trim() -and $_ -notmatch "^#" } | Select-Object -First 5 | ForEach-Object { Write-Host "  $_" }
        } catch {
            # Failed to read/process, skip
        }
    }
}

function Get-ContextIndex($rootDir) {
    Write-Host ""
    Write-Host "### Project Context Index"
    Write-Host "- **Product Definition**: $rootDir/product.md"
    Write-Host "- **Tech Stack**: $rootDir/tech-stack.md"
    Write-Host "- **Workflow**: $rootDir/workflow.md"
    Write-Host "- **Patterns**: $rootDir/patterns.md"
    Write-Host "- **Flow Registry**: $rootDir/flows.md"
}

function Get-ActiveWork($backend) {
    Write-Host ""
    Write-Host "### Active Work"
    if ($backend -eq "bd") {
        try {
            # Use a short timeout if possible (not native in PS, but we can try)
            $ready = bd ready --json | ConvertFrom-Json | Select-Object -First 3
            if ($ready) {
                $readyJson = $ready | ConvertTo-Json -Compress
                Write-Host "- **Ready Tasks (Top 3)**: $readyJson"
            } else {
                Write-Host "- **Ready Tasks**: None"
            }
        } catch {
            Write-Host "- **Ready Tasks**: None (error or no active session)"
        }
    } elseif ($backend -eq "br") {
        try {
            $ready = br ready | Select-Object -First 3
            if ($ready) {
                Write-Host "- **Ready Tasks (Top 3)**:"
                $ready | ForEach-Object { Write-Host "  $_" }
            } else {
                Write-Host "- **Ready Tasks**: None"
            }
        } catch {
            Write-Host "- **Ready Tasks**: None"
        }
    } else {
        Write-Host "- **Status**: No active backend for task tracking."
    }
}

function Extract-Truths($file) {
    if (Test-Path $file) {
        try {
            $content = Get-Content $file
            $inTruth = $false
            $truths = @()
            foreach ($line in $content) {
                if ($line -match "<!-- truth: start -->") { $inTruth = $true; continue }
                if ($line -match "<!-- truth: end -->") { $inTruth = $false; continue }
                if ($inTruth) { $truths += $line }
            }
            if ($truths.Count -gt 0) {
                $truths | ForEach-Object { Write-Host "  $_" }
                return $true
            }
        } catch {
            return $false
        }
    }
    return $false
}

function Get-EssentialTruths($rootDir) {
    Write-Host ""
    Write-Host "### Core Project Truths"

    $techStackFile = Join-Path $rootDir "tech-stack.md"
    if (Test-Path $techStackFile) {
        Write-Host "- **Tech Stack Summary**:"
        if (-not (Extract-Truths $techStackFile)) {
            Get-Content $techStackFile | Where-Object { $_ -match "^-" } | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
        }
    }

    $workflowFile = Join-Path $rootDir "workflow.md"
    if (Test-Path $workflowFile) {
        Write-Host "- **Canonical Commands**:"
        if (-not (Extract-Truths $workflowFile)) {
            $wfContent = Get-Content $workflowFile
            $foundSection = $false
            $count = 0
            foreach ($line in $wfContent) {
                if ($line -match "## Development Commands") { $foundSection = $true; continue }
                if ($foundSection) {
                    if ($line -match "^##") { break }
                    if ($line.Trim() -and $line -notmatch "^#") {
                        Write-Host "  $line"
                        $count++
                        if ($count -ge 15) { break }
                    }
                }
            }
        }
    }

    $patternsFile = Join-Path $rootDir "patterns.md"
    if (Test-Path $patternsFile) {
        Write-Host "- **Critical Patterns**:"
        if (-not (Extract-Truths $patternsFile)) {
            Get-Content $patternsFile | Where-Object { $_ -match "^-" } | Select-Object -First 10 | ForEach-Object { Write-Host "  $_" }
        }
    }
}

function Get-KnowledgeInventory($rootDir) {
    if ((Test-Path (Join-Path $rootDir "knowledge")) -or (Test-Path (Join-Path $rootDir "patterns.md"))) {
        Write-Host ""
        Write-Host "### Knowledge Base"
        if (Test-Path (Join-Path $rootDir "patterns.md")) { Write-Host "- **Consolidated Patterns**: $rootDir/patterns.md" }
        $knowledgeDir = Join-Path $rootDir "knowledge"
        if (Test-Path $knowledgeDir) {
            try {
                $chapters = Get-ChildItem "$knowledgeDir/*.md" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
                if ($chapters) {
                    Write-Host ("- **Knowledge Chapters**: " + ($chapters -join " "))
                }
            } catch {
                # Skip
            }
        }
    }
}

function Get-FlowMandate($rootDir) {
    Write-Host ""
    Write-Host "### Flow Mandate"
    Write-Host "- **Zero-Ambiguity Standard**: All PRDs MUST be Master Roadmaps (Sagas). ALL child plans MUST be 'High-Definition Worksheets' with exact line numbers and code snippets."
    Write-Host "- **Synthesis Mandate**: You are responsible for the knowledge lifecycle. Autonomously identify patterns and synthesize learnings into formal guides in `"$rootDir/knowledge/"`."
    Write-Host "- **Cleanup Mandate**: Regularly run \"/flow:cleanup\" to re-assess, reorganize, and optimize the project context. Verify task status against SOURCE CODE."
    Write-Host "- **Inherit First**: READ `patterns.md` and `knowledge/` chapters before planning. Adhere to current state truth."
    Write-Host "- **Deep Research First**: Do NOT defer research to implementation. ALL analysis and architectural decisions MUST be completed upfront."
    Write-Host "- **Stateless Executor Test**: A plan is only 'Ready' if an agent with ZERO context can implement it 100% correctly based ONLY on the worksheet."
    Write-Host "- **TDD Discipline**: Follow the Red-Green-Refactor cycle and verify coverage as outlined in the `flow` skill."
    Write-Host "- **Sync Requirement**: Run \"/flow:sync\" after any change to Beads state or project structure."
}

function Main {
    $backend = Get-BeadsBackend
    $rootDir = Get-FlowRoot
    Get-Tooling
    Get-GitContext $rootDir
    Get-ProjectIdentity $rootDir
    Get-ContextIndex $rootDir
    Get-ActiveWork $backend
    Get-EssentialTruths $rootDir
    Get-KnowledgeInventory $rootDir
    Get-FlowMandate $rootDir
}

Main

