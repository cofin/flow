#!/usr/bin/env pwsh
# Portable PowerShell PostToolUse live telemetry writer for Flow Studio.
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "lib/common.ps1")

$parsedArgs = Parse-FlowHookArgs -RawArgs $args -DefaultHarness "agy"
$Harness = $parsedArgs.Harness
$ProjectDir = $parsedArgs.ProjectDir
$StdinPayload = Read-FlowStdinPayload
$ProjectDir = Resolve-FlowProjectDir -ExplicitProjectDir $ProjectDir -StdinPayload $StdinPayload

$PConv = ""
$PParent = ""
$PTool = ""
$PFile = ""
$PStep = ""
$PTranscript = ""
$PArtifactDir = ""

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    foreach ($pat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $PConv = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"parentConversationId"\s*:\s*"([^"]+)"', '"parent_conversation_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $PParent = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"toolCall"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', '"tool_name"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $PTool = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"Path"\s*:\s*"([^"]+)"', '"file_path"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $PFile = ($m.Groups[1].Value -replace '\\\\', '/'); break }
    }
    $mStep = [regex]::Match($StdinPayload, '"stepIdx"\s*:\s*(\d+)')
    if ($mStep.Success) { $PStep = $mStep.Groups[1].Value }
    $mTp = [regex]::Match($StdinPayload, '"transcriptPath"\s*:\s*"([^"]+)"')
    if ($mTp.Success) { $PTranscript = ($mTp.Groups[1].Value -replace '\\\\', '/') }
    $mArt = [regex]::Match($StdinPayload, '"artifactDirectoryPath"\s*:\s*"([^"]+)"')
    if ($mArt.Success) { $PArtifactDir = ($mArt.Groups[1].Value -replace '\\\\', '/') }
}

if (([string]::IsNullOrEmpty($PTool) -or [string]::IsNullOrEmpty($PFile)) -and -not [string]::IsNullOrEmpty($PTranscript) -and (Test-Path -LiteralPath $PTranscript -PathType Leaf)) {
    $lines = Get-Content -LiteralPath $PTranscript -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($PStep) {
        $lines = $lines | Where-Object { $_ -match ('"step_index"\s*:\s*' + [regex]::Escape($PStep) + '\b') }
    }
    $lastLine = $lines | Select-Object -Last 1
    if ($lastLine) {
        if (-not $PTool) {
            $mt = [regex]::Match($lastLine, '"name"\s*:\s*"([^"]+)"')
            if ($mt.Success) { $PTool = $mt.Groups[1].Value }
        }
        if (-not $PFile) {
            $mf = [regex]::Match($lastLine, '"Path"\s*:\s*"([^"]+)"')
            if ($mf.Success) { $PFile = ($mf.Groups[1].Value -replace '\\\\', '/') }
        }
    }
}

$AgentsDir = Join-Path $ProjectDir ".agents"
if (-not (Test-Path -LiteralPath $AgentsDir)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$wtCtx = Resolve-FlowWorktreeContext -ProjectDir $ProjectDir
$EffectiveRoot = $wtCtx.EffectiveRoot
$BundleRel = $wtCtx.BundleRel
$rtPaths = Get-FlowRuntimePaths -EffectiveRoot $EffectiveRoot -ProjectDir $ProjectDir
$RuntimeWsDir = $rtPaths.RuntimeWsDir
$StateFile = $rtPaths.StateFile
$ReadStateFile = $rtPaths.ReadStateFile

New-Item -ItemType Directory -Path $RuntimeWsDir -Force -ErrorAction SilentlyContinue | Out-Null

$PrevDigest = ""; $Role = "coordinator"; $FlowId = ""; $ChapterId = ""; $TaskIds = @()
if (Test-Path -LiteralPath $ReadStateFile -PathType Leaf) {
    try {
        $prevObj = Get-Content -LiteralPath $ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prevObj.specDigest) { $PrevDigest = [string]$prevObj.specDigest }
        if ($prevObj.role) { $Role = [string]$prevObj.role }
        if ($prevObj.flowId) { $FlowId = [string]$prevObj.flowId }
        if ($prevObj.chapterId) { $ChapterId = [string]$prevObj.chapterId }
        if ($prevObj.taskIds) { $TaskIds = @($prevObj.taskIds) }
    } catch {}
}

if (-not [string]::IsNullOrEmpty($PParent)) { $Role = "flow-subagent" }

if (-not [string]::IsNullOrEmpty($PFile)) {
    $normFile = $PFile -replace '\\', '/'
    $mf = [regex]::Match($normFile, '/specs/([^/]+)')
    if ($mf.Success) { $FlowId = $mf.Groups[1].Value }
    $mc = [regex]::Match($normFile, '/chapters/([^/]+)')
    if ($mc.Success) { $ChapterId = $mc.Groups[1].Value }
    $mt = [regex]::Match($normFile, '/tasks/([^/]+)\.md$')
    if ($mt.Success -and $mt.Groups[1].Value -ne "index") {
        $tid = ($mt.Groups[1].Value -replace '-.*$', '')
        if ($tid) { $TaskIds = @($tid) }
    }
}

$ProceedGuard = ""
if (-not [string]::IsNullOrEmpty($PArtifactDir) -and -not [string]::IsNullOrEmpty($PFile)) {
    if ($PFile -eq "$PArtifactDir/implementation_plan.md" -or $PFile -eq "$PArtifactDir/learning_proposal.md") {
        if (-not (Test-Path -LiteralPath "${PFile}.metadata.json" -PathType Leaf)) {
            $ProceedGuard = "missing_artifact_metadata"
        }
    }
}

$Activity = if ($PTool -and $PFile) { "$PTool $PFile" } elseif ($PTool) { "Running $PTool" } else { "" }

$payload = [ordered]@{
    v              = 1
    updatedAt      = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness        = $Harness
    conversationId = $PConv
    role           = $Role
    flowId         = if ($FlowId) { $FlowId } else { $null }
    chapterId      = if ($ChapterId) { $ChapterId } else { $null }
    taskIds        = $TaskIds
    worktree       = ($ProjectDir -replace '\\', '/').TrimEnd('/')
    activity       = $Activity
    activeTurn     = $true
    lastTool       = $PTool
    lastFilePath   = $PFile
    proceedGuard   = $ProceedGuard
    specDigest     = $PrevDigest
}

($payload | ConvertTo-Json -Compress) | Set-Content -LiteralPath $StateFile -Encoding UTF8

if (-not [string]::IsNullOrEmpty($PFile) -and -not [string]::IsNullOrEmpty($PConv)) {
    $specsCheckDir = Join-Path $EffectiveRoot "$BundleRel/specs"
    $flowCliBin = Join-Path (Split-Path -Parent $PSScriptRoot) "bin/flow.mjs"
    if ((Test-Path -LiteralPath $specsCheckDir -PathType Container) -and (Test-Path -LiteralPath $flowCliBin -PathType Leaf) -and (Get-Command node -ErrorAction SilentlyContinue)) {
        try {
            $actArgs = @($flowCliBin, "spec", "activity", "--ws", $ProjectDir, "--conv", $PConv, "--parent-conv", $PParent, "--file", $PFile, "--tool", $(if ($PTool) { $PTool } else { "edit_file" }), "--json")
            if ($Role -eq "flow-subagent") { $actArgs += "--worker" }
            & node @actArgs 2>$null | Out-Null
        } catch {}
    }
}

[Console]::Out.WriteLine('{}')
