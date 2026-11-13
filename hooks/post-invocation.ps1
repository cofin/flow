#!/usr/bin/env pwsh
# Portable PowerShell PostInvocation hook for Flow Studio.
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

$ConvId = ""
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pat in @('"workspacePaths"\s*:\s*\[\s*"([^"]+)"', '"cwd"\s*:\s*"([^"]+)"')) {
            $m = [regex]::Match($StdinPayload, $pat)
            if ($m.Success) { $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'; break }
        }
    }
    $mConv = [regex]::Match($StdinPayload, '"conversationId"\s*:\s*"([^"]+)"')
    if ($mConv.Success) { $ConvId = $mConv.Groups[1].Value }
}

if ([string]::IsNullOrEmpty($ProjectDir)) { $ProjectDir = (Get-Location).Path }

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
                $ign = Get-SetupField (Join-Path $ProjectDir ".agents/setup-state.json") "ignore_policy"
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

$tmpRaw = if (-not [string]::IsNullOrEmpty($env:TMPDIR)) { $env:TMPDIR.TrimEnd('/', '\') } else { [IO.Path]::GetTempPath().TrimEnd('/', '\') }
$rtBase = if (-not [string]::IsNullOrEmpty($env:FLOW_RUNTIME_DIR)) { $env:FLOW_RUNTIME_DIR.TrimEnd('/', '\') } else { Join-Path $tmpRaw "flow-runtime" }
$normRoot = ($EffectiveRoot -replace '\\', '/').TrimEnd('/')
$wsId = [regex]::Replace($normRoot, '[^A-Za-z0-9._-]', '_')
if ($wsId.Length -gt 120) { $wsId = $wsId.Substring($wsId.Length - 120) }
if ([string]::IsNullOrEmpty($wsId)) { $wsId = "default" }
$RuntimeWsDir = Join-Path $rtBase $wsId
$StateFile = Join-Path $RuntimeWsDir "studio-live-state.json"
$LegacyStateFile = Join-Path $ProjectDir ".agents/studio-live-state.json"
$ReadStateFile = if (Test-Path -LiteralPath $StateFile -PathType Leaf) { $StateFile } elseif (Test-Path -LiteralPath $LegacyStateFile -PathType Leaf) { $LegacyStateFile } else { "" }
if ([string]::IsNullOrEmpty($ReadStateFile)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}
if (-not (Test-Path -LiteralPath $RuntimeWsDir -PathType Container)) {
    New-Item -ItemType Directory -Path $RuntimeWsDir -Force | Out-Null
}

$PrevDigest = ""
$LastTool = ""
$LastFile = ""
$Role = "coordinator"
$FlowId = $null
$ChapterId = $null
$TaskIds = @()
$Activity = ""
try {
    $prev = Get-Content -LiteralPath $ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($prev.specDigest) { $PrevDigest = [string]$prev.specDigest }
    if ($prev.lastTool) { $LastTool = [string]$prev.lastTool }
    if ($prev.lastFilePath) { $LastFile = [string]$prev.lastFilePath }
    if ($prev.role) { $Role = [string]$prev.role }
    if ($prev.flowId) { $FlowId = [string]$prev.flowId }
    if ($prev.chapterId) { $ChapterId = [string]$prev.chapterId }
    if ($prev.taskIds) { $TaskIds = @($prev.taskIds | ForEach-Object { [string]$_ }) }
    if ($prev.activity) { $Activity = [string]$prev.activity }
} catch {}

$WorktreeNorm = ($ProjectDir -replace '\\', '/').TrimEnd('/')
$StateObj = [ordered]@{
    v = 1
    updatedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness = $Harness
    conversationId = $ConvId
    role = $Role
    flowId = $FlowId
    chapterId = $ChapterId
    taskIds = @($TaskIds)
    worktree = $WorktreeNorm
    activity = $Activity
    activeTurn = $false
    lastTool = $LastTool
    lastFilePath = $LastFile
    specDigest = $PrevDigest
} | ConvertTo-Json -Compress

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($StateFile, "$StateObj`n", $utf8NoBom)
[Console]::Out.WriteLine('{}')
