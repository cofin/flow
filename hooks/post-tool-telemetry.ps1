#!/usr/bin/env pwsh
# Portable PowerShell PostToolUse live telemetry writer for Flow Studio.
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
$ParentConvId = ""
$ToolName = ""
$FilePath = ""

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pat in @('"workspacePaths"\s*:\s*\[\s*"([^"]+)"', '"cwd"\s*:\s*"([^"]+)"', '"workspace_roots"\s*:\s*\[\s*"([^"]+)"')) {
            $m = [regex]::Match($StdinPayload, $pat)
            if ($m.Success) { $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'; break }
        }
    }
    foreach ($pat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"', '"conversation_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ConvId = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"parentConversationId"\s*:\s*"([^"]+)"', '"parent_conversation_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ParentConvId = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"toolCall"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', '"tool_name"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ToolName = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"Path"\s*:\s*"([^"]+)"', '"file_path"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $FilePath = ($m.Groups[1].Value -replace '\\\\', '/'); break }
    }
}

if ([string]::IsNullOrEmpty($ProjectDir)) { $ProjectDir = (Get-Location).Path }
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
$Role = "coordinator"
$FlowId = $null
$ChapterId = $null
$TaskIds = @()
if (-not [string]::IsNullOrEmpty($ReadStateFile)) {
    try {
        $prev = Get-Content -LiteralPath $ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prev.specDigest) { $PrevDigest = [string]$prev.specDigest }
        if ($prev.role) { $Role = [string]$prev.role }
        if ($prev.flowId) { $FlowId = [string]$prev.flowId }
        if ($prev.chapterId) { $ChapterId = [string]$prev.chapterId }
        if ($prev.taskIds) { $TaskIds = @($prev.taskIds | ForEach-Object { [string]$_ }) }
    } catch {}
}
if (-not [string]::IsNullOrEmpty($ParentConvId)) { $Role = "flow-subagent" }

if (-not [string]::IsNullOrEmpty($FilePath)) {
    $mFl = [regex]::Match($FilePath, '/specs/([^/]+)')
    if ($mFl.Success) { $FlowId = $mFl.Groups[1].Value }
    $mCh = [regex]::Match($FilePath, '/chapters/([^/]+)')
    if ($mCh.Success) { $ChapterId = $mCh.Groups[1].Value }
    $mTk = [regex]::Match($FilePath, '/tasks/([^/]+)\.md$')
    if ($mTk.Success -and $mTk.Groups[1].Value -ne "index") {
        $tk = ($mTk.Groups[1].Value -replace '-.*$', '')
        if ($tk) { $TaskIds = @($tk) }
    }
}

if ([string]::IsNullOrEmpty($FlowId)) {
    $BundleRel = Get-SetupField (Join-Path $EffectiveRoot ".agents/setup-state.json") "bundle_root"
    if ([string]::IsNullOrEmpty($BundleRel)) { $BundleRel = ".agents/bundles" }
    $SpecsScanDir = Join-Path $EffectiveRoot "$BundleRel/specs"
    if (Test-Path -LiteralPath $SpecsScanDir -PathType Container) {
        foreach ($sDir in @(Get-ChildItem -LiteralPath $SpecsScanDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
            $sf = Join-Path $sDir.FullName "spec.md"
            if (-not (Test-Path -LiteralPath $sf -PathType Leaf)) { continue }
            $rawSf = Get-Content -LiteralPath $sf -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            if ($rawSf -match '(?m)^state:\s*(active|in_progress)\b') {
                $mFid = [regex]::Match($rawSf, '(?m)^flow_id:\s*["'']?([^"''\r\n]+)')
                $FlowId = if ($mFid.Success) { $mFid.Groups[1].Value.Trim() } else { $sDir.Name }
                if ([string]::IsNullOrEmpty($ChapterId)) {
                    $mCh = [regex]::Match($rawSf, '(?m)^current_chapter:\s*["'']?([^"''\r\n#]+)')
                    if ($mCh.Success -and $mCh.Groups[1].Value.Trim() -ne "null") {
                        $ChapterId = $mCh.Groups[1].Value.Trim()
                    }
                }
                break
            }
        }
    }
}

$Activity = ""
if (-not [string]::IsNullOrEmpty($ToolName) -and -not [string]::IsNullOrEmpty($FilePath)) {
    $Activity = "$ToolName $FilePath"
} elseif (-not [string]::IsNullOrEmpty($ToolName)) {
    $Activity = "Running $ToolName"
}

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
    activeTurn = $true
    lastTool = $ToolName
    lastFilePath = $FilePath
    specDigest = $PrevDigest
} | ConvertTo-Json -Compress

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($StateFile, "$StateObj`n", $utf8NoBom)
[Console]::Out.WriteLine('{}')
