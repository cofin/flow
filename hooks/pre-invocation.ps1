#!/usr/bin/env pwsh
# Portable PowerShell PreInvocation refresh hook for Flow Studio.
$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "lib/common.ps1")

$parsedArgs = Parse-FlowHookArgs -RawArgs $args -DefaultHarness "agy"
$Harness = $parsedArgs.Harness
$ProjectDir = $parsedArgs.ProjectDir
$StdinPayload = Read-FlowStdinPayload

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    $invMatch = [regex]::Match($StdinPayload, '"invocationNum"\s*:\s*(\d+)')
    if ($invMatch.Success -and ([int]$invMatch.Groups[1].Value) -gt 0) {
        [Console]::Out.WriteLine('{}')
        exit 0
    }
}

$ProjectDir = Resolve-FlowProjectDir -ExplicitProjectDir $ProjectDir -StdinPayload $StdinPayload
$AgentsDir = Join-Path $ProjectDir ".agents"
if (-not (Test-Path -LiteralPath $AgentsDir)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

if (Test-FlowWorkerInvocation -StdinPayload $StdinPayload) {
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

$digestParts = New-Object System.Collections.Generic.List[string]
$specsRoot = Join-Path (Join-Path $EffectiveRoot $BundleRel) "specs"
if (Test-Path -LiteralPath $specsRoot -PathType Container) {
    foreach ($sf in (Get-ChildItem -LiteralPath $specsRoot -Directory -ErrorAction SilentlyContinue | Sort-Object Name)) {
        $sp = Join-Path $sf.FullName "spec.md"
        if (Test-Path -LiteralPath $sp -PathType Leaf) {
            $bytes = [System.IO.File]::ReadAllBytes($sp)
            $sha = [System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash($bytes)).Replace("-", "").ToLowerInvariant()
            $digestParts.Add("${sp}=${sha}")
        }
        $fbDir = Join-Path $sf.FullName "feedback"
        if (Test-Path -LiteralPath $fbDir -PathType Container) {
            foreach ($ff in (Get-ChildItem -LiteralPath $fbDir -Filter "*.json" -File -ErrorAction SilentlyContinue | Sort-Object Name)) {
                $fbBytes = [System.IO.File]::ReadAllBytes($ff.FullName)
                $fsha = [System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash($fbBytes)).Replace("-", "").ToLowerInvariant()
                $digestParts.Add("$($ff.FullName)=${fsha}")
            }
        }
    }
}
$commentsFile = Join-Path $EffectiveRoot ".agents/studio-comments.json"
if (Test-Path -LiteralPath $commentsFile -PathType Leaf) {
    $cbytes = [System.IO.File]::ReadAllBytes($commentsFile)
    $csha = [System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash($cbytes)).Replace("-", "").ToLowerInvariant()
    $digestParts.Add("comments=${csha}")
}

$FinalDigest = ""
if ($digestParts.Count -gt 0) {
    $accBytes = [System.Text.Encoding]::UTF8.GetBytes(($digestParts -join ";"))
    $FinalDigest = [System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash($accBytes)).Replace("-", "").ToLowerInvariant().Substring(0, 16)
}

$PrevDigest = ""
$ActiveTurn = $false
$PrevConv = ""
$PrevRole = "coordinator"
$PrevFlow = ""
$PrevChapter = ""
$PrevTasks = @()
$PrevActivity = ""
$PrevTool = ""
$PrevFile = ""

if (Test-Path -LiteralPath $ReadStateFile -PathType Leaf) {
    try {
        $prevObj = Get-Content -LiteralPath $ReadStateFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prevObj.specDigest) { $PrevDigest = [string]$prevObj.specDigest }
        if ($prevObj.activeTurn -eq $true) { $ActiveTurn = $true }
        if ($prevObj.conversationId) { $PrevConv = [string]$prevObj.conversationId }
        if ($prevObj.role) { $PrevRole = [string]$prevObj.role }
        if ($prevObj.flowId) { $PrevFlow = [string]$prevObj.flowId }
        if ($prevObj.chapterId) { $PrevChapter = [string]$prevObj.chapterId }
        if ($prevObj.taskIds) { $PrevTasks = @($prevObj.taskIds) }
        if ($prevObj.activity) { $PrevActivity = [string]$prevObj.activity }
        if ($prevObj.lastTool) { $PrevTool = [string]$prevObj.lastTool }
        if ($prevObj.lastFilePath) { $PrevFile = [string]$prevObj.lastFilePath }
    } catch {}
}

$LastUserText = ""
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    foreach ($convPat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"')) {
        $cm = [regex]::Match($StdinPayload, $convPat)
        if ($cm.Success) { $PrevConv = $cm.Groups[1].Value; break }
    }
    $lm = [regex]::Match($StdinPayload, '"lastUserInput"\s*:\s*"((?:[^"\\]|\\.)*)"')
    if ($lm.Success) {
        $LastUserText = $lm.Groups[1].Value
    } else {
        $tpMatch = [regex]::Match($StdinPayload, '"transcriptPath"\s*:\s*"([^"]+)"')
        if ($tpMatch.Success) {
            $tp = ($tpMatch.Groups[1].Value -replace '\\\\', '/')
            if (Test-Path -LiteralPath $tp -PathType Leaf) {
                $LastUserText = (Get-Content -LiteralPath $tp -Encoding UTF8 -ErrorAction SilentlyContinue | Where-Object { $_ -match '"type"\s*:\s*"USER_INPUT"' } | Select-Object -Last 1)
            }
        }
    }
}

$Turn0Notice = ""
if (-not (Test-FlowSiblingPluginPresent -EffectiveRoot $EffectiveRoot) -and -not [string]::IsNullOrWhiteSpace($LastUserText)) {
    if ($LastUserText -match '/plan\b') {
        $Turn0Notice = "Flow Turn-0 handoff: Keep plans outside the repository tree during /plan so Review remains active. Include concrete file path:line hints; after approval run node sidecars/studio/flow-cli.mjs spec import --from PLAN_PATH to create task worksheets."
    } elseif ($LastUserText -match '/learn\b') {
        $Turn0Notice = "Flow Turn-0 handoff: Route durable repository conventions to .agents/bundles/knowledge/ and keep user personal preferences outside repository files."
    }
}

$payload = [ordered]@{
    v              = 1
    updatedAt      = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness        = $Harness
    conversationId = $PrevConv
    role           = $PrevRole
    flowId         = if ($PrevFlow) { $PrevFlow } else { $null }
    chapterId      = if ($PrevChapter) { $PrevChapter } else { $null }
    taskIds        = $PrevTasks
    worktree       = ($ProjectDir -replace '\\', '/').TrimEnd('/')
    activity       = $PrevActivity
    activeTurn     = $ActiveTurn
    lastTool       = $PrevTool
    lastFilePath   = $PrevFile
    specDigest     = $FinalDigest
}

$DigestNotice = ""
if ($FinalDigest) {
    if ([string]::IsNullOrEmpty($PrevDigest)) {
        ($payload | ConvertTo-Json -Compress) | Set-Content -LiteralPath $StateFile -Encoding UTF8
    } elseif ($PrevDigest -ne $FinalDigest -and -not $ActiveTurn) {
        ($payload | ConvertTo-Json -Compress) | Set-Content -LiteralPath $StateFile -Encoding UTF8
        $DigestNotice = "Flow Studio notice: Active spec.md or Studio review feedback changed on disk since the previous turn. Re-read the active spec.md and feedback files before mutating code."
    } elseif ($PrevDigest -ne $FinalDigest) {
        ($payload | ConvertTo-Json -Compress) | Set-Content -LiteralPath $StateFile -Encoding UTF8
    }
}

$CombinedNotice = @($DigestNotice, $Turn0Notice) | Where-Object { -not [string]::IsNullOrEmpty($_) } | Join-String -Separator " "
if ([string]::IsNullOrWhiteSpace($CombinedNotice)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$CleanNotice = Strip-FlowXmlTags -Text $CombinedNotice
$EscapedNotice = Escape-FlowJsonString -Value $CleanNotice

switch -Regex ($Harness) {
    '^(agy|antigravity)$' { [Console]::Out.WriteLine("{`"injectSteps`":[{`"systemMessage`":{`"systemMessage`":`"$EscapedNotice`"}}]}") }
    '^cursor$' { [Console]::Out.WriteLine("{`"continue`":true,`"additional_context`":`"$EscapedNotice`"}") }
    default { [Console]::Out.WriteLine("{`"continue`":true,`"hookSpecificOutput`":{`"hookEventName`":`"UserPromptSubmit`",`"additionalContext`":`"$EscapedNotice`"}}") }
}
