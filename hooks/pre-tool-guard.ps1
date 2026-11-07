#!/usr/bin/env pwsh
# Portable PowerShell PreToolUse safety guard for Flow.
$ErrorActionPreference = "Stop"

$Harness = "claude"
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
        if ($i + 1 -lt $args.Count) { $i++ }
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

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
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

    foreach ($pat in @('"agentName"\s*:\s*"([^"]+)"', '"agent_type"\s*:\s*"([^"]+)"', '"subagent_type"\s*:\s*"([^"]+)"')) {
        $mAg = [regex]::Match($StdinPayload, $pat)
        if ($mAg.Success) {
            $AgentId = $mAg.Groups[1].Value
            break
        }
    }
}

$Decision = "allow"
$Reason = ""

$ReadOnlyAgents = @("code-reviewer", "quality-reviewer", "researcher")
$ShortAgent = ($AgentId -split ':')[-1]
$MutatingTools = @("write_file", "edit_file", "replace_file_content", "multi_replace_file_content", "delete_file", "Write", "Edit", "MultiEdit", "NotebookEdit")

if ($ShortAgent -in $ReadOnlyAgents -and $ToolName -in $MutatingTools) {
    $Decision = "deny"
    $Reason = "Flow safety guard: read-only agent '$AgentId' is forbidden from mutating repository files."
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
