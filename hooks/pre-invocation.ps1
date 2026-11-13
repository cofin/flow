#!/usr/bin/env pwsh
# Portable PowerShell PreInvocation refresh hook for Flow Studio.
$ErrorActionPreference = "Stop"

$Harness = "agy"
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

$StdinPayload = ""
try {
    if ([Console]::IsInputRedirected) {
        $StdinPayload = [Console]::In.ReadToEnd()
    }
} catch {
    $StdinPayload = ""
}

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    $mInv = [regex]::Match($StdinPayload, '"invocationNum"\s*:\s*([0-9]+)')
    if ($mInv.Success -and ([int]$mInv.Groups[1].Value -gt 0)) {
        [Console]::Out.WriteLine('{}')
        exit 0
    }
}

if ([string]::IsNullOrEmpty($ProjectDir) -and -not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    foreach ($pat in @('"workspacePaths"\s*:\s*\[\s*"([^"]+)"', '"cwd"\s*:\s*"([^"]+)"', '"workspace_roots"\s*:\s*\[\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) {
            $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'
            break
        }
    }
}
if ([string]::IsNullOrEmpty($ProjectDir)) {
    $ProjectDir = (Get-Location).Path
}

$AgentsDir = Join-Path $ProjectDir ".agents"
if (-not (Test-Path -LiteralPath $AgentsDir)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

function Get-SetupField([string]$PathArg, [string]$Key) {
    if (-not (Test-Path -LiteralPath $PathArg -PathType Leaf)) { return "" }
    try {
        $raw = Get-Content -LiteralPath $PathArg -Raw -Encoding UTF8
        $m = [regex]::Match($raw, "`"$Key`"\s*:\s*`"([^`"]+)`"")
        if ($m.Success) { return $m.Groups[1].Value.Trim() }
    } catch {}
    return ""
}

$EffectiveRoot = $ProjectDir
if ((Test-Path -LiteralPath (Join-Path $ProjectDir ".git") -PathType Leaf) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    try {
        $commonDir = (& git -C $ProjectDir rev-parse --path-format=absolute --git-common-dir 2>$null)
        if (-not [string]::IsNullOrWhiteSpace($commonDir)) {
            $candMain = Split-Path -Parent $commonDir.Trim()
            if (-not [string]::IsNullOrWhiteSpace($candMain) -and (Test-Path -LiteralPath (Join-Path $candMain ".agents") -PathType Container)) {
                $ign = Get-SetupField (Join-Path $AgentsDir "setup-state.json") "ignore_policy"
                if ([string]::IsNullOrEmpty($ign)) {
                    $ign = Get-SetupField (Join-Path $candMain ".agents/setup-state.json") "ignore_policy"
                }
                if ($ign -ne "shared") {
                    $EffectiveRoot = $candMain
                }
            }
        }
    } catch {}
}

$BundleRel = Get-SetupField (Join-Path $EffectiveRoot ".agents/setup-state.json") "bundle_root"
if ([string]::IsNullOrEmpty($BundleRel)) { $BundleRel = ".agents/bundles" }

$Acc = New-Object System.Collections.Generic.List[string]
$SpecsDir = Join-Path $EffectiveRoot "$BundleRel/specs"
if (Test-Path -LiteralPath $SpecsDir -PathType Container) {
    $Dirs = Get-ChildItem -LiteralPath $SpecsDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name
    foreach ($d in $Dirs) {
        $sf = Join-Path $d.FullName "spec.md"
        if (Test-Path -LiteralPath $sf -PathType Leaf) {
            $hash = (Get-FileHash -LiteralPath $sf -Algorithm SHA256).Hash.Substring(0, 16)
            $Acc.Add("$($d.Name)=$hash")
        }
    }
}
$CommentsFile = Join-Path $EffectiveRoot ".agents/studio-comments.json"
if (Test-Path -LiteralPath $CommentsFile -PathType Leaf) {
    $chash = (Get-FileHash -LiteralPath $CommentsFile -Algorithm SHA256).Hash.Substring(0, 16)
    $Acc.Add("comments=$chash")
}

if ($Acc.Count -eq 0) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$FinalDigest = ($Acc -join ";")
$tmpRaw = if (-not [string]::IsNullOrEmpty($env:TMPDIR)) { $env:TMPDIR.TrimEnd('/', '\') } else { [IO.Path]::GetTempPath().TrimEnd('/', '\') }
$rtBase = if (-not [string]::IsNullOrEmpty($env:FLOW_RUNTIME_DIR)) { $env:FLOW_RUNTIME_DIR.TrimEnd('/', '\') } else { Join-Path $tmpRaw "flow-runtime" }
$normRoot = ($EffectiveRoot -replace '\\', '/').TrimEnd('/')
$wsId = [regex]::Replace($normRoot, '[^A-Za-z0-9._-]', '_')
if ($wsId.Length -gt 120) { $wsId = $wsId.Substring($wsId.Length - 120) }
if ([string]::IsNullOrEmpty($wsId)) { $wsId = "default" }
$RuntimeWsDir = Join-Path $rtBase $wsId
if (-not (Test-Path -LiteralPath $RuntimeWsDir -PathType Container)) {
    New-Item -ItemType Directory -Path $RuntimeWsDir -Force | Out-Null
}
$StateFile = Join-Path $RuntimeWsDir "studio-live-state.json"
$LegacyStateFile = Join-Path $AgentsDir "studio-live-state.json"
$ReadStateFile = if (Test-Path -LiteralPath $StateFile -PathType Leaf) { $StateFile } elseif (Test-Path -LiteralPath $LegacyStateFile -PathType Leaf) { $LegacyStateFile } else { "" }

$PrevDigest = ""
$ActiveTurn = $false
$ConvId = ""
$Role = "coordinator"
$FlowId = $null
$ChapterId = $null
$TaskIds = @()
$Activity = ""
$LastTool = ""
$LastFile = ""
if (-not [string]::IsNullOrEmpty($ReadStateFile)) {
    try {
        $prev = Get-Content -LiteralPath $ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prev.specDigest) { $PrevDigest = [string]$prev.specDigest }
        if ($prev.activeTurn -eq $true) { $ActiveTurn = $true }
        if ($prev.conversationId) { $ConvId = [string]$prev.conversationId }
        if ($prev.role) { $Role = [string]$prev.role }
        if ($prev.flowId) { $FlowId = [string]$prev.flowId }
        if ($prev.chapterId) { $ChapterId = [string]$prev.chapterId }
        if ($prev.taskIds) { $TaskIds = @($prev.taskIds | ForEach-Object { [string]$_ }) }
        if ($prev.activity) { $Activity = [string]$prev.activity }
        if ($prev.lastTool) { $LastTool = [string]$prev.lastTool }
        if ($prev.lastFilePath) { $LastFile = [string]$prev.lastFilePath }
    } catch {}
}
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    foreach ($pat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ConvId = $m.Groups[1].Value; break }
    }
    if ([regex]::IsMatch($StdinPayload, '"parentConversationId"\s*:\s*"[^"]+"')) {
        $Role = "flow-subagent"
    }
}

$WorktreeNorm = ($ProjectDir -replace '\\', '/').TrimEnd('/')
$NowIso = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$StateObj = [ordered]@{
    v = 1
    updatedAt = $NowIso
    harness = $Harness
    conversationId = $ConvId
    role = $Role
    flowId = $FlowId
    chapterId = $ChapterId
    taskIds = @($TaskIds)
    worktree = $WorktreeNorm
    activity = $Activity
    activeTurn = $ActiveTurn
    lastTool = $LastTool
    lastFilePath = $LastFile
    specDigest = $FinalDigest
} | ConvertTo-Json -Compress

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
if ([string]::IsNullOrEmpty($PrevDigest) -or $PrevDigest -eq $FinalDigest -or $ActiveTurn) {
    [System.IO.File]::WriteAllText($StateFile, "$StateObj`n", $utf8NoBom)
    [Console]::Out.WriteLine('{}')
    exit 0
}

[System.IO.File]::WriteAllText($StateFile, "$StateObj`n", $utf8NoBom)
$Notice = "Flow Studio notice: Active spec.md or Studio review comments changed on disk since the previous turn. Re-read the active spec.md and .agents/studio-comments.json before mutating code."

switch -Regex ($Harness) {
    '^(agy|antigravity)$' {
        [Console]::Out.WriteLine("{`"injectSteps`":[{`"systemMessage`":{`"systemMessage`":`"$Notice`"}}]}")
    }
    '^cursor$' {
        [Console]::Out.WriteLine("{`"continue`":true,`"additional_context`":`"$Notice`"}")
    }
    default {
        [Console]::Out.WriteLine("{`"continue`":true,`"hookSpecificOutput`":{`"hookEventName`":`"UserPromptSubmit`",`"additionalContext`":`"$Notice`"}}")
    }
}
