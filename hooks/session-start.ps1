#!/usr/bin/env pwsh
# Portable PowerShell SessionStart priming hook for Flow.
# Requires zero Python, Node.js, or external modules on Windows/Linux/macOS.
$ErrorActionPreference = "Stop"

$Harness = "claude"
$ProjectDir = ""

for ($i = 0; $i -lt $args.Count; $i++) {
    $arg = [string]$args[$i]
    if ($arg -eq "--harness" -or $arg -eq "-Harness") {
        if ($i + 1 -lt $args.Count) {
            $Harness = [string]$args[$i + 1]
            $i++
        }
    } elseif ($arg -like "--harness=*") {
        $Harness = $arg.Substring(10)
    } elseif ($arg -like "-Harness=*") {
        $Harness = $arg.Substring(9)
    } elseif ($arg -eq "--project" -or $arg -eq "-Project") {
        if ($i + 1 -lt $args.Count) {
            $ProjectDir = [string]$args[$i + 1]
            $i++
        }
    } elseif ($arg -like "--project=*") {
        $ProjectDir = $arg.Substring(10)
    } elseif ($arg -like "-Project=*") {
        $ProjectDir = $arg.Substring(9)
    }
}

# Suppress third-party Claude hook double-firing inside Cursor when native Cursor hook is active.
if ($Harness -eq "claude" -and -not [string]::IsNullOrEmpty($env:CURSOR_VERSION)) {
    [Console]::Out.WriteLine('{"continue":true}')
    exit 0
}

$StdinPayload = ""
try {
    if ([Console]::IsInputRedirected) {
        $StdinPayload = [Console]::In.ReadToEnd()
    }
} catch {
    $StdinPayload = ""
}

if ([string]::IsNullOrEmpty($ProjectDir) -and -not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    foreach ($pattern in @(
        '"workspacePaths"\s*:\s*\[\s*"([^"]+)"',
        '"workspace_roots"\s*:\s*\[\s*"([^"]+)"',
        '"cwd"\s*:\s*"([^"]+)"',
        '"workspaceRoot"\s*:\s*"([^"]+)"'
    )) {
        $m = [regex]::Match($StdinPayload, $pattern)
        if ($m.Success) {
            $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'
            break
        }
    }
}

if ([string]::IsNullOrEmpty($ProjectDir)) {
    if (-not [string]::IsNullOrEmpty($env:CURSOR_PROJECT_DIR)) {
        $ProjectDir = $env:CURSOR_PROJECT_DIR
    } elseif (-not [string]::IsNullOrEmpty($env:CLAUDE_PROJECT_DIR)) {
        $ProjectDir = $env:CLAUDE_PROJECT_DIR
    } else {
        $ProjectDir = (Get-Location).Path
    }
}

$BundleRel = ".agents/bundles"
$SetupStateFile = Join-Path $ProjectDir ".agents/setup-state.json"
if (Test-Path -LiteralPath $SetupStateFile -PathType Leaf) {
    try {
        $SetupRaw = Get-Content -LiteralPath $SetupStateFile -Raw -Encoding UTF8
        $m = [regex]::Match($SetupRaw, '"bundle_root"\s*:\s*"([^"]+)"')
        if ($m.Success -and -not [string]::IsNullOrWhiteSpace($m.Groups[1].Value)) {
            $BundleRel = $m.Groups[1].Value.Trim()
        }
    } catch {
        $BundleRel = ".agents/bundles"
    }
}

$ActiveSpecsList = New-Object System.Collections.Generic.List[string]
$SpecsDir = Join-Path $ProjectDir "$BundleRel/specs"
if (Test-Path -LiteralPath $SpecsDir -PathType Container) {
    $SpecDirs = Get-ChildItem -LiteralPath $SpecsDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name
    foreach ($dir in $SpecDirs) {
        $SpecFile = Join-Path $dir.FullName "spec.md"
        if (Test-Path -LiteralPath $SpecFile -PathType Leaf) {
            try {
                $Lines = Get-Content -LiteralPath $SpecFile -Encoding UTF8
                if ($Lines.Count -gt 0 -and $Lines[0].Trim() -eq "---") {
                    $FlowId = ""
                    $State = ""
                    $CurrentTask = ""
                    for ($idx = 1; $idx -lt $Lines.Count; $idx++) {
                        $line = $Lines[$idx]
                        if ($line.Trim() -eq "---") {
                            break
                        }
                        if ($line -match '^flow_id:\s*(.+)$') {
                            $FlowId = $Matches[1].Trim().Trim('"').Trim("'")
                        } elseif ($line -match '^state:\s*(.+)$') {
                            $State = $Matches[1].Trim().Trim('"').Trim("'")
                        } elseif ($line -match '^current_task:\s*(.+)$') {
                            $CurrentTask = $Matches[1].Trim().Trim('"').Trim("'")
                        }
                    }
                    if (-not [string]::IsNullOrEmpty($FlowId) -and $State -ne "completed" -and $State -ne "archived") {
                        if (-not [string]::IsNullOrEmpty($CurrentTask) -and $CurrentTask -ne "null") {
                            $ActiveSpecsList.Add("$FlowId($State, task=$CurrentTask)")
                        } else {
                            $ActiveSpecsList.Add("$FlowId($State)")
                        }
                    }
                }
            } catch {
                # Ignore unreadable spec files during startup priming.
            }
        }
    }
}

$ActiveSpecs = $ActiveSpecsList -join ", "
$BaseMsg = "Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity."
$AgentsDir = Join-Path $ProjectDir ".agents"
if (Test-Path -LiteralPath $AgentsDir -PathType Container) {
    $BaseMsg = "$BaseMsg Workspace bundle root: $BundleRel."
    $SkillsIndex = Join-Path $ProjectDir ".agents/skills/index.md"
    if (Test-Path -LiteralPath $SkillsIndex -PathType Leaf) {
        $BaseMsg = "$BaseMsg Project-local domain and review skills index: .agents/skills/index.md."
    }
    if (-not [string]::IsNullOrEmpty($ActiveSpecs)) {
        $BaseMsg = "$BaseMsg Active specs: $ActiveSpecs."
    }
}

function ConvertTo-JsonEscaped([string]$Text) {
    if ($null -eq $Text) { return "" }
    $escaped = $Text.Replace('\', '\\').Replace('"', '\"').Replace("`r", "").Replace("`t", " ").Replace("`n", "\n")
    return $escaped
}

$EscapedMsg = ConvertTo-JsonEscaped $BaseMsg
$EscapedBundle = ConvertTo-JsonEscaped $BundleRel
$EscapedSpecs = ConvertTo-JsonEscaped $ActiveSpecs

switch -Regex ($Harness) {
    '^(agy|antigravity)$' {
        [Console]::Out.WriteLine("{`"injectSteps`":[{`"systemMessage`":{`"systemMessage`":`"$EscapedMsg`"}}]}")
    }
    '^cursor$' {
        [Console]::Out.WriteLine("{`"continue`":true,`"additional_context`":`"$EscapedMsg`"}")
    }
    '^json$' {
        [Console]::Out.WriteLine("{`"bundle_root`":`"$EscapedBundle`",`"active_specs`":`"$EscapedSpecs`",`"message`":`"$EscapedMsg`"}")
    }
    default {
        [Console]::Out.WriteLine("{`"continue`":true,`"systemMessage`":`"$EscapedMsg`",`"hookSpecificOutput`":{`"hookEventName`":`"SessionStart`",`"additionalContext`":`"$EscapedMsg`"}}")
    }
}
