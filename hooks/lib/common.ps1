# Shared PowerShell utilities for Flow runtime hooks.
# Dot-sourced by hooks/*.ps1; avoids unary-comma array returns (`return ,$arr`).

function Parse-FlowHookArgs {
    param(
        [string[]]$RawArgs,
        [string]$DefaultHarness = "claude"
    )
    $harness = $DefaultHarness
    $projectDir = ""
    for ($i = 0; $i -lt $RawArgs.Count; $i++) {
        $arg = [string]$RawArgs[$i]
        if ($arg -eq "--harness" -or $arg -eq "-Harness") {
            if ($i + 1 -lt $RawArgs.Count) {
                $harness = [string]$RawArgs[$i + 1]
                $i++
            }
        } elseif ($arg -like "--harness=*") {
            $harness = $arg.Substring(10)
        } elseif ($arg -like "-Harness=*") {
            $harness = $arg.Substring(9)
        } elseif ($arg -eq "--project" -or $arg -eq "-Project") {
            if ($i + 1 -lt $RawArgs.Count) {
                $projectDir = [string]$RawArgs[$i + 1]
                $i++
            }
        } elseif ($arg -like "--project=*") {
            $projectDir = $arg.Substring(10)
        } elseif ($arg -like "-Project=*") {
            $projectDir = $arg.Substring(9)
        }
    }
    return @{ Harness = $harness; ProjectDir = $projectDir }
}

function Read-FlowStdinPayload {
    $payload = ""
    try {
        if ([Console]::IsInputRedirected) {
            $payload = [Console]::In.ReadToEnd()
        }
    } catch {
        $payload = ""
    }
    return $payload
}

function Strip-FlowXmlTags {
    param([string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return "" }
    return [regex]::Replace($Text, '<[^>]+>', '')
}

function Escape-FlowJsonString {
    param([string]$Value)
    if ($null -eq $Value) { return "" }
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $Value.ToCharArray()) {
        switch ($ch) {
            '\' { [void]$sb.Append('\\') }
            '"' { [void]$sb.Append('\"') }
            "`n" { [void]$sb.Append('\n') }
            "`r" { }
            "`t" { [void]$sb.Append('\t') }
            default {
                if ([int][char]$ch -ge 32) { [void]$sb.Append($ch) }
            }
        }
    }
    return $sb.ToString()
}

function Resolve-FlowProjectDir {
    param(
        [string]$ExplicitProjectDir,
        [string]$StdinPayload
    )
    $projectDir = $ExplicitProjectDir
    if ([string]::IsNullOrEmpty($projectDir) -and -not [string]::IsNullOrWhiteSpace($StdinPayload)) {
        foreach ($pattern in @(
            '"workspacePaths"\s*:\s*\[\s*"([^"]+)"',
            '"workspace_roots"\s*:\s*\[\s*"([^"]+)"',
            '"cwd"\s*:\s*"([^"]+)"',
            '"workspaceRoot"\s*:\s*"([^"]+)"'
        )) {
            $m = [regex]::Match($StdinPayload, $pattern)
            if ($m.Success) {
                $projectDir = ($m.Groups[1].Value -replace '\\\\', '/')
                break
            }
        }
    }
    if ([string]::IsNullOrEmpty($projectDir)) {
        if (-not [string]::IsNullOrEmpty($env:CURSOR_PROJECT_DIR)) {
            $projectDir = $env:CURSOR_PROJECT_DIR
        } elseif (-not [string]::IsNullOrEmpty($env:CLAUDE_PROJECT_DIR)) {
            $projectDir = $env:CLAUDE_PROJECT_DIR
        } else {
            $projectDir = (Get-Location).Path
        }
    }
    return $projectDir
}

function Read-FlowSetupField {
    param([string]$JsonFile, [string]$FieldName)
    if (-not (Test-Path -LiteralPath $JsonFile -PathType Leaf)) { return "" }
    $raw = Get-Content -LiteralPath $JsonFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ([string]::IsNullOrWhiteSpace($raw)) { return "" }
    $m = [regex]::Match($raw, '"' + [regex]::Escape($FieldName) + '"\s*:\s*"([^"]+)"')
    if ($m.Success) { return $m.Groups[1].Value }
    return ""
}

function Resolve-FlowWorktreeContext {
    param([string]$ProjectDir)
    $isLinked = $false
    $mainWt = ""
    $effectiveRoot = $ProjectDir
    $ignorePolicy = ""

    $dotGit = Join-Path $ProjectDir ".git"
    if ((Test-Path -LiteralPath $dotGit -PathType Leaf) -and (Get-Command git -ErrorAction SilentlyContinue)) {
        try {
            $gitCommon = (& git -C $ProjectDir rev-parse --path-format=absolute --git-common-dir 2>$null)
            if ([string]::IsNullOrWhiteSpace($gitCommon)) {
                $gitCommon = (& git -C $ProjectDir rev-parse --git-common-dir 2>$null)
            }
            if (-not [string]::IsNullOrWhiteSpace($gitCommon)) {
                $commonAbs = if ([System.IO.Path]::IsPathRooted($gitCommon.Trim())) {
                    [System.IO.Path]::GetFullPath($gitCommon.Trim())
                } else {
                    [System.IO.Path]::GetFullPath((Join-Path $ProjectDir $gitCommon.Trim()))
                }
                $candMain = Split-Path -Parent $commonAbs
                $projAbs = [System.IO.Path]::GetFullPath($ProjectDir)
                if ($candMain -and ($candMain -ne $projAbs)) {
                    $isLinked = $true
                    $mainWt = $candMain
                }
            }
        } catch {
            $isLinked = $false
        }
    }

    if ($isLinked -and $mainWt) {
        $ignorePolicy = Read-FlowSetupField -JsonFile (Join-Path $ProjectDir ".agents/setup-state.json") -FieldName "ignore_policy"
        if ([string]::IsNullOrEmpty($ignorePolicy)) {
            $ignorePolicy = Read-FlowSetupField -JsonFile (Join-Path $mainWt ".agents/setup-state.json") -FieldName "ignore_policy"
        }
        if ([string]::IsNullOrEmpty($ignorePolicy)) {
            if (Test-Path -LiteralPath (Join-Path $mainWt ".agents")) {
                $ignorePolicy = "local-only"
            } else {
                $ignorePolicy = "shared"
            }
        }
        if ($ignorePolicy -eq "local-only" -and (Test-Path -LiteralPath (Join-Path $mainWt ".agents"))) {
            $effectiveRoot = $mainWt
        }
    }

    $bundleRel = ".agents/bundles"
    $detectedRoot = Read-FlowSetupField -JsonFile (Join-Path $effectiveRoot ".agents/setup-state.json") -FieldName "bundle_root"
    if (-not [string]::IsNullOrEmpty($detectedRoot)) { $bundleRel = $detectedRoot }

    return @{
        IsLinkedWorktree = $isLinked
        MainWorktree = $mainWt
        IgnorePolicy = $ignorePolicy
        EffectiveRoot = $effectiveRoot
        BundleRel = $bundleRel
    }
}

function Get-FlowRuntimePaths {
    param([string]$EffectiveRoot, [string]$ProjectDir)
    $rtBase = if (-not [string]::IsNullOrEmpty($env:FLOW_RUNTIME_DIR)) { $env:FLOW_RUNTIME_DIR.TrimEnd('/', '\') } else { Join-Path ([System.IO.Path]::GetTempPath()) "flow-runtime" }
    $norm = ($EffectiveRoot -replace '\\', '/').TrimEnd('/')
    $san = [regex]::Replace($norm, '[^A-Za-z0-9._-]', '_')
    $wsId = if ($san.Length -gt 120) { $san.Substring($san.Length - 120) } elseif ($san) { $san } else { "default" }
    $rtWsDir = Join-Path $rtBase $wsId
    $stateFile = Join-Path $rtWsDir "studio-live-state.json"
    $readState = $stateFile
    if (-not (Test-Path -LiteralPath $readState)) {
        $legacyState = Join-Path $ProjectDir ".agents/studio-live-state.json"
        if (Test-Path -LiteralPath $legacyState) { $readState = $legacyState }
    }
    return @{ RuntimeWsDir = $rtWsDir; StateFile = $stateFile; ReadStateFile = $readState }
}

function Test-FlowWorkerInvocation {
    param([string]$StdinPayload)
    if ($env:FLOW_SWARM_WORKER -eq "1" -or $env:BB_SWARM_WORKER -eq "1") { return $true }
    if ([string]::IsNullOrWhiteSpace($StdinPayload)) { return $false }

    if ([regex]::IsMatch($StdinPayload, '"(parentConversationId|parent_conversation_id|parentSessionId|parent_session_id)"\s*:\s*"[^"]+"')) {
        return $true
    }
    if ([regex]::IsMatch($StdinPayload, '"(agentName|agent_type|subagent_type)"\s*:\s*"(flow-|bb-|runtime-)[^"]*"')) {
        return $true
    }
    if ([regex]::IsMatch($StdinPayload, '"lastUserInput"\s*:\s*"[^"]*(agents/(executor|researcher|code-reviewer|quality-reviewer|plan-generator)\.md|templates/agent/(plan|executor)-schema-card\.md|\.agents/agents/|\[Flow Swarm Worker\]|swarm-worker)')) {
        return $true
    }

    $tpMatch = [regex]::Match($StdinPayload, '"transcriptPath"\s*:\s*"([^"]+)"')
    if ($tpMatch.Success) {
        $tp = ($tpMatch.Groups[1].Value -replace '\\\\', '/')
        if (Test-Path -LiteralPath $tp -PathType Leaf) {
            $rawT = Get-Content -LiteralPath $tp -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if (-not [string]::IsNullOrWhiteSpace($rawT)) {
                $hasUser = [regex]::IsMatch($rawT, '"type"\s*:\s*"USER_INPUT"')
                $hasSys = [regex]::IsMatch($rawT, '"type"\s*:\s*"SYSTEM_MESSAGE"')
                if ($hasSys -and -not $hasUser) { return $true }
            }
        }
    }
    return $false
}

function Test-FlowSiblingPluginPresent {
    param([string]$EffectiveRoot)
    if ($env:FLOW_SIBLING_PLUGIN_PRESENT -eq "1") { return $true }
    if ($env:FLOW_SIBLING_PLUGIN_PRESENT -eq "0") { return $false }
    $homeDir = if ($env:HOME) { $env:HOME } else { $env:USERPROFILE }
    $candidates = @(
        (Join-Path $homeDir ".gemini/config/plugins/bb"),
        (Join-Path $homeDir ".gemini/jetski/plugins/bb"),
        (Join-Path $EffectiveRoot ".agents/plugins/bb")
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c -PathType Container) { return $true }
    }
    return $false
}
