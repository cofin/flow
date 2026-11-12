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

$IsSubagent = $false
$ConvId = ""
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([regex]::IsMatch($StdinPayload, '"parentConversationId"\s*:\s*"[^"]+"')) {
        $IsSubagent = $true
    }
    foreach ($convPat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"', '"conversation_id"\s*:\s*"([^"]+)"')) {
        $cm = [regex]::Match($StdinPayload, $convPat)
        if ($cm.Success) {
            $ConvId = $cm.Groups[1].Value
            break
        }
    }
    if ([string]::IsNullOrEmpty($ProjectDir)) {
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

function Get-SetupField([string]$FilePath, [string]$Key) {
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { return "" }
    try {
        $raw = Get-Content -LiteralPath $FilePath -Raw -Encoding UTF8
        $m = [regex]::Match($raw, "`"$Key`"\s*:\s*`"([^`"]+)`"")
        if ($m.Success) { return $m.Groups[1].Value.Trim() }
    } catch {}
    return ""
}

function New-WorktreeLink([string]$LinkPath, [string]$TargetPath) {
    if ((Test-Path -LiteralPath $LinkPath) -or (-not (Test-Path -LiteralPath $TargetPath))) { return }
    try {
        $isDir = Test-Path -LiteralPath $TargetPath -PathType Container
        if ($IsWindows -and $isDir) {
            New-Item -ItemType Junction -Path $LinkPath -Target $TargetPath -ErrorAction SilentlyContinue | Out-Null
        } else {
            New-Item -ItemType SymbolicLink -Path $LinkPath -Target $TargetPath -ErrorAction SilentlyContinue | Out-Null
        }
    } catch {}
}

$EffectiveRoot = $ProjectDir
$WorktreeNote = ""
$GitDotFile = Join-Path $ProjectDir ".git"
if ((Test-Path -LiteralPath $GitDotFile -PathType Leaf) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    try {
        $commonDir = (& git -C $ProjectDir rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($commonDir)) {
            $candMain = Split-Path -Parent $commonDir.Trim()
            if (-not [string]::IsNullOrWhiteSpace($candMain) -and ([IO.Path]::GetFullPath($candMain) -ne [IO.Path]::GetFullPath($ProjectDir))) {
                foreach ($sharedArt in @(".venv", "node_modules", "uv.toml", ".npmrc", ".python-version")) {
                    New-WorktreeLink (Join-Path $ProjectDir $sharedArt) (Join-Path $candMain $sharedArt)
                }
                $ignorePolicy = Get-SetupField (Join-Path $ProjectDir ".agents/setup-state.json") "ignore_policy"
                if ([string]::IsNullOrEmpty($ignorePolicy)) {
                    $ignorePolicy = Get-SetupField (Join-Path $candMain ".agents/setup-state.json") "ignore_policy"
                }
                if ([string]::IsNullOrEmpty($ignorePolicy)) {
                    $mainAgents = Join-Path $candMain ".agents"
                    $projAgents = Join-Path $ProjectDir ".agents"
                    if ((-not (Test-Path -LiteralPath $projAgents)) -and (Test-Path -LiteralPath $mainAgents -PathType Container)) {
                        $ignorePolicy = "local-only"
                    } else {
                        $ignorePolicy = "shared"
                    }
                }
                if ($ignorePolicy -eq "local-only" -and (Test-Path -LiteralPath (Join-Path $candMain ".agents") -PathType Container)) {
                    New-WorktreeLink (Join-Path $ProjectDir ".agents") (Join-Path $candMain ".agents")
                    $EffectiveRoot = $candMain
                    $WorktreeNote = "Linked Git worktree (local-only .agents): .agents is shared from primary checkout $candMain/.agents — edit Flow Markdown in $candMain/.agents (or via symlinked .agents/), and reuse symlinked .venv with uv run --no-sync (do not run make install)."
                } else {
                    $WorktreeNote = "Linked Git worktree (shared .agents): edit worktree .agents/ directly, and reuse symlinked .venv with uv run --no-sync (do not run make install)."
                }
            }
        }
    } catch {}
}

$BundleRel = ".agents/bundles"
$DetectedBundle = Get-SetupField (Join-Path $EffectiveRoot ".agents/setup-state.json") "bundle_root"
if (-not [string]::IsNullOrWhiteSpace($DetectedBundle)) {
    $BundleRel = $DetectedBundle
}

$ActiveSpecs = ""
$PendingSync = ""
$DegradedPlans = ""

if ($IsSubagent) {
    try {
        $tmpRaw = if (-not [string]::IsNullOrEmpty($env:TMPDIR)) { $env:TMPDIR.TrimEnd('/', '\') } else { [IO.Path]::GetTempPath().TrimEnd('/', '\') }
        $rtBase = if (-not [string]::IsNullOrEmpty($env:FLOW_RUNTIME_DIR)) { $env:FLOW_RUNTIME_DIR.TrimEnd('/', '\') } else { Join-Path $tmpRaw "flow-runtime" }
        $normRoot = ($EffectiveRoot -replace '\\', '/').TrimEnd('/')
        $wsId = [regex]::Replace($normRoot, '[^A-Za-z0-9._-]', '_')
        if ($wsId.Length -gt 120) { $wsId = $wsId.Substring($wsId.Length - 120) }
        if ([string]::IsNullOrEmpty($wsId)) { $wsId = "default" }
        $leaseDir = Join-Path (Join-Path $rtBase $wsId) "subagents"
        if (-not (Test-Path -LiteralPath $leaseDir -PathType Container)) {
            New-Item -ItemType Directory -Path $leaseDir -Force | Out-Null
        }
        $safeConv = if (-not [string]::IsNullOrEmpty($ConvId)) { [regex]::Replace($ConvId, '[^A-Za-z0-9._-]', '_') } else { "pid-$PID" }
        $epochNow = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds().ToString()
        Set-Content -LiteralPath (Join-Path $leaseDir "$safeConv.lease") -Value $epochNow -Encoding UTF8 -ErrorAction SilentlyContinue
    } catch {}
    if (Test-Path -LiteralPath (Join-Path $EffectiveRoot ".agents") -PathType Container) {
        $BaseMsg = "Flow subagent context: bundle root $EffectiveRoot/$BundleRel. Stay strictly within your assigned Bounded Read Manifest."
    } else {
        $BaseMsg = "Flow subagent context: no .agents bundle in workspace."
    }
} else {
    try {
        $IsRepoWorkspace = (Test-Path -LiteralPath (Join-Path $ProjectDir ".agents")) -or
                           (Test-Path -LiteralPath (Join-Path $ProjectDir ".git")) -or
                           (Test-Path -LiteralPath (Join-Path $ProjectDir ".jj")) -or
                           (Test-Path -LiteralPath (Join-Path $ProjectDir ".hg"))
        $NormProj = $ProjectDir -replace '\\', '/'
        $AllowRecord = (-not [string]::IsNullOrEmpty($env:FLOW_CONFIG_DIR)) -or
                       ($NormProj -notmatch '^/tmp/|/pytest-of-|/sidecars/studio$|/\.gemini/config/plugins/')
        if ($IsRepoWorkspace -and $AllowRecord) {
            $CfgDir = if (-not [string]::IsNullOrEmpty($env:FLOW_CONFIG_DIR)) {
                $env:FLOW_CONFIG_DIR
            } elseif (-not [string]::IsNullOrEmpty($env:XDG_CONFIG_HOME)) {
                Join-Path $env:XDG_CONFIG_HOME "flow"
            } else {
                Join-Path ([Environment]::GetFolderPath("UserProfile")) ".config/flow"
            }
            if (-not (Test-Path -LiteralPath $CfgDir -PathType Container)) {
                New-Item -ItemType Directory -Path $CfgDir -Force | Out-Null
            }
            $RecentFile = Join-Path $CfgDir "recent-workspaces.tsv"
            $TsIso = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
            Add-Content -LiteralPath $RecentFile -Value "$TsIso`t$ProjectDir" -Encoding UTF8 -ErrorAction SilentlyContinue

            if ([string]::IsNullOrEmpty($env:FLOW_CONFIG_DIR) -and [string]::IsNullOrEmpty($env:FLOW_SKIP_VSCODE_AUTO_INSTALL)) {
                $PluginRoot = Split-Path -Parent $PSScriptRoot
                $InstallerPath = Join-Path $PluginRoot "vscode-extension/install.mjs"
                if ((Test-Path -LiteralPath $InstallerPath -PathType Leaf) -and (Get-Command node -ErrorAction SilentlyContinue)) {
                    & node $InstallerPath --if-needed --quiet 2>$null | Out-Null
                }
            }
        }
    } catch {}

    $ActiveSpecsList = New-Object System.Collections.Generic.List[string]
    $PendingSyncList = New-Object System.Collections.Generic.List[string]
    $DegradedList = New-Object System.Collections.Generic.List[string]
    $SpecsDir = Join-Path $EffectiveRoot "$BundleRel/specs"
    if (Test-Path -LiteralPath $SpecsDir -PathType Container) {
        $SpecDirs = Get-ChildItem -LiteralPath $SpecsDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name
        foreach ($dir in $SpecDirs) {
            $SpecFile = Join-Path $dir.FullName "spec.md"
            if (Test-Path -LiteralPath $SpecFile -PathType Leaf) {
                try {
                    $Lines = @(Get-Content -LiteralPath $SpecFile -Encoding UTF8)
                    if ($Lines.Count -gt 0 -and $Lines[0].Trim() -eq "---") {
                        $FlowId = ""
                        $State = ""
                        $CurrentChapter = ""
                        $CurrentTask = ""
                        $PlanQual = ""
                        for ($idx = 1; $idx -lt $Lines.Count; $idx++) {
                            $line = $Lines[$idx]
                            if ($line.Trim() -eq "---") { break }
                            if ($line -match '^flow_id:\s*(.+)$') {
                                $FlowId = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                            } elseif ($line -match '^state:\s*(.+)$') {
                                $State = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                            } elseif ($line -match '^current_chapter:\s*(.+)$') {
                                $CurrentChapter = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                            } elseif ($line -match '^current_task:\s*(.+)$') {
                                $CurrentTask = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                            } elseif ($line -match '^planning_quality:\s*(.+)$') {
                                $PlanQual = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                            }
                        }
                        if ([string]::IsNullOrEmpty($FlowId)) { $FlowId = $dir.Name }

                        $ChaptersDir = Join-Path $dir.FullName "chapters"
                        if (Test-Path -LiteralPath $ChaptersDir -PathType Container) {
                            $ChDirs = @(Get-ChildItem -LiteralPath $ChaptersDir -Filter "ch*" -Directory -ErrorAction SilentlyContinue | Sort-Object Name)
                            foreach ($chDir in $ChDirs) {
                                $chSpec = Join-Path $chDir.FullName "spec.md"
                                if (-not (Test-Path -LiteralPath $chSpec -PathType Leaf)) { continue }
                                $chLines = @(Get-Content -LiteralPath $chSpec -Encoding UTF8)
                                $chState = ""
                                $chRev = ""
                                if ($chLines.Count -gt 0 -and $chLines[0].Trim() -eq "---") {
                                    for ($ci = 1; $ci -lt $chLines.Count; $ci++) {
                                        $cln = $chLines[$ci]
                                        if ($cln.Trim() -eq "---") { break }
                                        if ($cln -match '^state:\s*(.+)$') {
                                            $chState = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                                        } elseif ($cln -match '^last_reviewed_commit:\s*(.+)$') {
                                            $chRev = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                                        } elseif ($cln -match '^planning_quality:\s*(.+)$') {
                                            $cpq = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                                            if ($cpq -eq "degraded") { $PlanQual = "degraded" }
                                        }
                                    }
                                }
                                if (([string]::IsNullOrEmpty($CurrentChapter) -or $CurrentChapter -eq "null") -and ($chState -notin @("completed", "deferred", "skipped"))) {
                                    $CurrentChapter = $chDir.Name
                                }
                                $chTasksDir = Join-Path $chDir.FullName "tasks"
                                if (Test-Path -LiteralPath $chTasksDir -PathType Container) {
                                    $tTot = 0
                                    $tDone = 0
                                    $tFiles = @(Get-ChildItem -LiteralPath $chTasksDir -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name)
                                    foreach ($tf in $tFiles) {
                                        if ($tf.Name -eq "index.md") { continue }
                                        $tTot++
                                        $tLines = @(Get-Content -LiteralPath $tf.FullName -Encoding UTF8)
                                        $tSt = ""
                                        if ($tLines.Count -gt 0 -and $tLines[0].Trim() -eq "---") {
                                            for ($ti = 1; $ti -lt $tLines.Count; $ti++) {
                                                $tln = $tLines[$ti]
                                                if ($tln.Trim() -eq "---") { break }
                                                if ($tln -match '^state:\s*(.+)$') {
                                                    $tSt = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                                                    break
                                                }
                                            }
                                        }
                                        if ($tSt -in @("completed", "closed", "deferred", "skipped")) { $tDone++ }
                                    }
                                    if ($chState -ne "paused" -and (($tTot -gt 0 -and $tDone -eq $tTot -and ($chState -notin @("completed", "deferred", "skipped"))) -or
                                        ($chState -eq "completed" -and ([string]::IsNullOrEmpty($chRev) -or $chRev -eq "null")))) {
                                        $PendingSyncList.Add("$FlowId/$($chDir.Name)")
                                    }
                                }
                            }
                        }

                        if (-not [string]::IsNullOrEmpty($FlowId) -and $State -ne "completed" -and $State -ne "archived") {
                            $HasCh = (-not [string]::IsNullOrEmpty($CurrentChapter)) -and ($CurrentChapter -ne "null")
                            $HasTk = (-not [string]::IsNullOrEmpty($CurrentTask)) -and ($CurrentTask -ne "null")
                            if ($HasCh -and $HasTk) {
                                $ActiveSpecsList.Add("$FlowId($State, chapter=$CurrentChapter, task=$CurrentTask)")
                            } elseif ($HasCh) {
                                $ActiveSpecsList.Add("$FlowId($State, chapter=$CurrentChapter)")
                            } elseif ($HasTk) {
                                $ActiveSpecsList.Add("$FlowId($State, task=$CurrentTask)")
                            } else {
                                $ActiveSpecsList.Add("$FlowId($State)")
                            }
                            if ($PlanQual -eq "degraded") {
                                $DegradedList.Add($FlowId)
                            }
                        }
                    }
                } catch {}
            }
        }
    }

    $ActiveSpecs = $ActiveSpecsList -join ", "
    $PendingSync = $PendingSyncList -join ", "
    $DegradedPlans = $DegradedList -join ", "
    $AgentsDir = Join-Path $EffectiveRoot ".agents"
    if (Test-Path -LiteralPath $AgentsDir -PathType Container) {
        $BaseMsg = "Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity."
        $BaseMsg = "$BaseMsg Workspace bundle root: $BundleRel."
        if (-not [string]::IsNullOrEmpty($WorktreeNote)) {
            $BaseMsg = "$BaseMsg $WorktreeNote"
        }
        $SkillsIndex = Join-Path $EffectiveRoot ".agents/skills/index.md"
        if (Test-Path -LiteralPath $SkillsIndex -PathType Leaf) {
            $BaseMsg = "$BaseMsg Project-local domain and review skills index: .agents/skills/index.md."
        }
        if (-not [string]::IsNullOrEmpty($ActiveSpecs)) {
            $BaseMsg = "$BaseMsg Active specs: $ActiveSpecs."
        }
        if (-not [string]::IsNullOrEmpty($DegradedPlans)) {
            $BaseMsg = "$BaseMsg Degraded planning quality warning (planning_quality=degraded — not planned with optimal primary frontier thinking model): $DegradedPlans."
        }
        if (-not [string]::IsNullOrEmpty($PendingSync)) {
            $BaseMsg = "$BaseMsg Pending chapter review/Markdown sync: $PendingSync."
        }
        if ($Harness -match '^(agy|antigravity)$') {
            $BaseMsg = "$BaseMsg Flow Studio UI: [Open Flow Studio](sidecar://flow/studio/dashboard)."
        } else {
            $BaseMsg = "$BaseMsg Flow Studio UI: npx --yes --package github:cofin/flow flow-studio."
        }
    } else {
        $BaseMsg = "Flow plugin loaded (no .agents/ bundle in this workspace; run /flow:setup to initialize)."
    }
}

$OpenCodeConfigRoot = if (-not [string]::IsNullOrEmpty($env:XDG_CONFIG_HOME)) {
    $env:XDG_CONFIG_HOME
} elseif (-not [string]::IsNullOrEmpty($env:HOME)) {
    Join-Path $env:HOME ".config"
} else {
    Join-Path ([Environment]::GetFolderPath("UserProfile")) ".config"
}
$OpenCodeLegacyPlugin = Join-Path $OpenCodeConfigRoot "opencode/plugins/flow.js"
try {
    if (Test-Path -LiteralPath $OpenCodeLegacyPlugin -PathType Leaf) {
        $LegacyRaw = Get-Content -LiteralPath $OpenCodeLegacyPlugin -Raw -Encoding UTF8
        if ($LegacyRaw -match 'flow-rule-adapter:start' -or $LegacyRaw -match 'export default async') {
            $BaseMsg = "$BaseMsg Stale pre-0.26 OpenCode Flow plugin at ${OpenCodeLegacyPlugin}: OpenCode V2 rejects it; delete it and run: opencode plugin add github:cofin/flow."
        }
    }
} catch {
    # Ignore unreadable OpenCode config during startup priming.
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
