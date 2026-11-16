#!/usr/bin/env pwsh
# Portable PowerShell PostInvocation hook for Flow Studio.
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "lib/common.ps1")

$parsedArgs = Parse-FlowHookArgs -RawArgs $args -DefaultHarness "agy"
$Harness = $parsedArgs.Harness
$ProjectDir = $parsedArgs.ProjectDir
$StdinPayload = Read-FlowStdinPayload
$ProjectDir = Resolve-FlowProjectDir -ExplicitProjectDir $ProjectDir -StdinPayload $StdinPayload

$PConv = ""
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    $mc = [regex]::Match($StdinPayload, '"conversationId"\s*:\s*"([^"]+)"')
    if ($mc.Success) { $PConv = $mc.Groups[1].Value }
}

$wtCtx = Resolve-FlowWorktreeContext -ProjectDir $ProjectDir
$rtPaths = Get-FlowRuntimePaths -EffectiveRoot $wtCtx.EffectiveRoot -ProjectDir $ProjectDir
if (-not (Test-Path -LiteralPath $rtPaths.ReadStateFile -PathType Leaf)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

New-Item -ItemType Directory -Path $rtPaths.RuntimeWsDir -Force -ErrorAction SilentlyContinue | Out-Null

$PrevDigest = ""; $PrevTool = ""; $PrevFile = ""; $PrevRole = "coordinator"; $PrevFlow = $null; $PrevChapter = $null; $PrevTasks = @(); $PrevActivity = ""
try {
    $prevObj = Get-Content -LiteralPath $rtPaths.ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($prevObj.specDigest) { $PrevDigest = [string]$prevObj.specDigest }
    if ($prevObj.lastTool) { $PrevTool = [string]$prevObj.lastTool }
    if ($prevObj.lastFilePath) { $PrevFile = [string]$prevObj.lastFilePath }
    if ($prevObj.role) { $PrevRole = [string]$prevObj.role }
    $PrevFlow = $prevObj.flowId
    $PrevChapter = $prevObj.chapterId
    if ($prevObj.taskIds) { $PrevTasks = @($prevObj.taskIds) }
    if ($prevObj.activity) { $PrevActivity = [string]$prevObj.activity }
} catch {}

$payload = [ordered]@{
    v              = 1
    updatedAt      = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness        = $Harness
    conversationId = $PConv
    role           = $PrevRole
    flowId         = $PrevFlow
    chapterId      = $PrevChapter
    taskIds        = $PrevTasks
    worktree       = ($ProjectDir -replace '\\', '/').TrimEnd('/')
    activity       = $PrevActivity
    activeTurn     = $false
    lastTool       = $PrevTool
    lastFilePath   = $PrevFile
    specDigest     = $PrevDigest
}

($payload | ConvertTo-Json -Compress) | Set-Content -LiteralPath $rtPaths.StateFile -Encoding UTF8
[Console]::Out.WriteLine('{}')
