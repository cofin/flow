#!/usr/bin/env pwsh
# Portable PowerShell PreToolUse safety guard for Flow.
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
    } elseif ($arg -eq "--project" -or $arg -eq "-Project") {
        if ($i + 1 -lt $args.Count) {
            $ProjectDir = [string]$args[$i + 1]
            $i++
        }
    } elseif ($arg -like "--project=*") {
        $ProjectDir = $arg.Substring(10)
    }
}

if ($Harness -eq "claude" -and -not [string]::IsNullOrEmpty($env:CURSOR_VERSION)) {
    [Console]::Out.WriteLine('{}')
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

$ToolName = ""
$AgentId = ""
$CmdLine = ""
$TargetPath = ""

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pattern in @(
            '"workspacePaths"\s*:\s*\[\s*"([^"]+)"',
            '"workspace_roots"\s*:\s*\[\s*"([^"]+)"',
            '"cwd"\s*:\s*"([^"]+)"',
            '"workspaceRoot"\s*:\s*"([^"]+)"'
        )) {
            $mp = [regex]::Match($StdinPayload, $pattern)
            if ($mp.Success) {
                $ProjectDir = $mp.Groups[1].Value -replace '\\\\', '/'
                break
            }
        }
    }

    $mTool = [regex]::Match($StdinPayload, '"toolCall"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"')
    if (-not $mTool.Success) {
        $mTool = [regex]::Match($StdinPayload, '"tool_name"\s*:\s*"([^"]+)"')
    }
    if ($mTool.Success) { $ToolName = $mTool.Groups[1].Value }

    $mCmd = [regex]::Match($StdinPayload, '"CommandLine"\s*:\s*"((?:[^"\\]|\\.)*)"')
    if (-not $mCmd.Success) {
        $mCmd = [regex]::Match($StdinPayload, '"command"\s*:\s*"((?:[^"\\]|\\.)*)"')
    }
    if ($mCmd.Success) { $CmdLine = $mCmd.Groups[1].Value }

    foreach ($pPat in @('"Path"\s*:\s*"([^"]+)"', '"file_path"\s*:\s*"([^"]+)"', '"TargetFile"\s*:\s*"([^"]+)"')) {
        $mTp = [regex]::Match($StdinPayload, $pPat)
        if ($mTp.Success) {
            $TargetPath = $mTp.Groups[1].Value -replace '\\\\', '/'
            break
        }
    }

    foreach ($pat in @('"agentName"\s*:\s*"([^"]+)"', '"agent_type"\s*:\s*"([^"]+)"', '"subagent_type"\s*:\s*"([^"]+)"')) {
        $mAg = [regex]::Match($StdinPayload, $pat)
        if ($mAg.Success) {
            $AgentId = $mAg.Groups[1].Value
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

function Test-IncompleteFlowSpec([string]$FlowId) {
    if ([string]::IsNullOrEmpty($FlowId)) { return $false }
    $specRoot = Join-Path $ProjectDir ".agents/bundles/specs/$FlowId"
    if (-not (Test-Path -LiteralPath (Join-Path $specRoot "spec.md") -PathType Leaf)) {
        if ((Test-Path -LiteralPath (Join-Path $ProjectDir ".git") -PathType Leaf) -and (Get-Command git -ErrorAction SilentlyContinue)) {
            try {
                $gcom = (& git -C $ProjectDir rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1)
                if (-not [string]::IsNullOrWhiteSpace($gcom)) {
                    $cmain = Split-Path -Parent $gcom.Trim()
                    $candRoot = Join-Path $cmain ".agents/bundles/specs/$FlowId"
                    if (Test-Path -LiteralPath (Join-Path $candRoot "spec.md") -PathType Leaf) {
                        $specRoot = $candRoot
                    }
                }
            } catch {}
        }
    }
    $rootSpec = Join-Path $specRoot "spec.md"
    if (-not (Test-Path -LiteralPath $rootSpec -PathType Leaf)) { return $false }
    $lines = @(Get-Content -LiteralPath $rootSpec -Encoding UTF8)
    $st = ""
    $lrc = ""
    if ($lines.Count -gt 0 -and $lines[0].Trim() -eq "---") {
        for ($idx = 1; $idx -lt $lines.Count; $idx++) {
            $ln = $lines[$idx]
            if ($ln.Trim() -eq "---") { break }
            if ($ln -match '^state:\s*(.+)$') { $st = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
            if ($ln -match '^last_reviewed_commit:\s*(.+)$') { $lrc = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
        }
    }
    if ($st -ne "completed" -or [string]::IsNullOrEmpty($lrc) -or $lrc -eq "null") { return $true }
    $chDirRoot = Join-Path $specRoot "chapters"
    if (Test-Path -LiteralPath $chDirRoot -PathType Container) {
        $chDirs = Get-ChildItem -LiteralPath $chDirRoot -Filter "ch*" -Directory -ErrorAction SilentlyContinue
        foreach ($cd in $chDirs) {
            $cs = Join-Path $cd.FullName "spec.md"
            if (-not (Test-Path -LiteralPath $cs -PathType Leaf)) { return $true }
            $cLines = @(Get-Content -LiteralPath $cs -Encoding UTF8)
            $cst = ""
            if ($cLines.Count -gt 0 -and $cLines[0].Trim() -eq "---") {
                for ($ci = 1; $ci -lt $cLines.Count; $ci++) {
                    if ($cLines[$ci].Trim() -eq "---") { break }
                    if ($cLines[$ci] -match '^state:\s*(.+)$') { $cst = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
                }
            }
            if ($cst -notin @("completed", "deferred", "skipped")) { return $true }
        }
    }
    $taskCandidates = @()
    $flatTasks = Join-Path $specRoot "tasks"
    if (Test-Path -LiteralPath $flatTasks -PathType Container) {
        $taskCandidates += @(Get-ChildItem -LiteralPath $flatTasks -Filter "*.md" -File -ErrorAction SilentlyContinue)
    }
    if (Test-Path -LiteralPath $chDirRoot -PathType Container) {
        foreach ($cd in (Get-ChildItem -LiteralPath $chDirRoot -Filter "ch*" -Directory -ErrorAction SilentlyContinue)) {
            $ct = Join-Path $cd.FullName "tasks"
            if (Test-Path -LiteralPath $ct -PathType Container) {
                $taskCandidates += @(Get-ChildItem -LiteralPath $ct -Filter "*.md" -File -ErrorAction SilentlyContinue)
            }
        }
    }
    foreach ($tf in $taskCandidates) {
        if ($tf.Name -eq "index.md") { continue }
        $tLines = @(Get-Content -LiteralPath $tf.FullName -Encoding UTF8)
        $tst = ""
        if ($tLines.Count -gt 0 -and $tLines[0].Trim() -eq "---") {
            for ($ti = 1; $ti -lt $tLines.Count; $ti++) {
                if ($tLines[$ti].Trim() -eq "---") { break }
                if ($tLines[$ti] -match '^state:\s*(.+)$') { $tst = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
            }
        }
        if ($tst -notin @("completed", "closed", "deferred", "skipped")) { return $true }
    }
    return $false
}

$Decision = "allow"
$Reason = ""

$ReadOnlyAgents = @("code-reviewer", "quality-reviewer", "researcher")
$ShortAgent = ($AgentId -split ':')[-1]
$MutatingTools = @("write_file", "write_to_file", "edit_file", "replace_file_content", "multi_replace_file_content", "delete_file", "notebook_edit", "Write", "Edit", "MultiEdit", "NotebookEdit")

if ($ShortAgent -in $ReadOnlyAgents -and $ToolName -in $MutatingTools) {
    $Decision = "deny"
    $Reason = "Flow safety guard: read-only agent '$AgentId' is forbidden from mutating repository files."
}

if ($Decision -eq "allow" -and $ToolName -eq "delete_file" -and -not [string]::IsNullOrWhiteSpace($TargetPath)) {
    $mDel = [regex]::Match($TargetPath, '\.agents/bundles/specs/([A-Za-z0-9_-]+)(?:/spec\.md|/)?$')
    if ($mDel.Success -and (Test-IncompleteFlowSpec $mDel.Groups[1].Value)) {
        $Decision = "deny"
        $Reason = "Flow safety guard: cannot delete or archive specs/$($mDel.Groups[1].Value) while chapters or tasks remain incomplete or unreviewed."
    }
}

if ($Decision -eq "allow" -and -not [string]::IsNullOrWhiteSpace($CmdLine)) {
    if ($CmdLine -match '(^|[;&|\s])(git\s+rm|rm|rmdir|Remove-Item)(\s|$)') {
        $mRm = [regex]::Match($CmdLine, '\.agents/bundles/specs/([A-Za-z0-9_-]+)(?:/spec\.md|/)?(?=[\s"''\;&|]|$)')
        if ($mRm.Success -and (Test-IncompleteFlowSpec $mRm.Groups[1].Value)) {
            $Decision = "deny"
            $Reason = "Flow safety guard: cannot delete or archive specs/$($mRm.Groups[1].Value) while chapters or tasks remain incomplete or unreviewed."
        }
    }
}

if ($Decision -eq "allow" -and -not [string]::IsNullOrWhiteSpace($CmdLine)) {
    if ($CmdLine -match '(^|[;&|\s])git\s+push(\s+[^;&|]*)?\s+--tags([\s;&|]|$)') {
        $Decision = "deny"
        $Reason = "Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+tag(\s+([^;&|]*))?([;&|]|$)') {
        $Tail = if ($Matches[3]) { $Matches[3].Trim() } else { "" }
        if ($Tail -ne "" -and $Tail -notmatch '^(-l|--list|--contains|--points-at|-v|--verify)(\s|$)') {
            $Decision = "deny"
            $Reason = "Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        }
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+push(\s+[^;&|]*)?\s+(-f|--force|--force-with-lease)([\s;&|]|$)') {
        $Decision = "ask"
        $Reason = "Flow safety guard: destructive Git force-push requires explicit user confirmation."
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+reset\s+--hard([\s;&|]|$)') {
        $Decision = "ask"
        $Reason = "Flow safety guard: destructive git reset --hard requires explicit user confirmation."
    }
}

$EscReason = $Reason.Replace('\', '\\').Replace('"', '\"').Replace("`r", "").Replace("`n", " ")

switch -Regex ($Harness) {
    '^(agy|antigravity)$' {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"decision`":`"deny`",`"reason`":`"$EscReason`"}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"decision`":`"force_ask`",`"reason`":`"$EscReason`"}")
        } else {
            [Console]::Out.WriteLine('{"decision":"allow"}')
        }
    }
    '^cursor$' {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"permission`":`"deny`",`"user_message`":`"$EscReason`"}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"permission`":`"ask`",`"user_message`":`"$EscReason`"}")
        } else {
            [Console]::Out.WriteLine('{"permission":"allow"}')
        }
    }
    default {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"hookSpecificOutput`":{`"hookEventName`":`"PreToolUse`",`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"$EscReason`"}}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"hookSpecificOutput`":{`"hookEventName`":`"PreToolUse`",`"permissionDecision`":`"ask`",`"permissionDecisionReason`":`"$EscReason`"}}")
        } else {
            [Console]::Out.WriteLine('{}')
        }
    }
}
