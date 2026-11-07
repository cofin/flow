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
$StateFile = Join-Path $ProjectDir ".agents/studio-live-state.json"
if (-not (Test-Path -LiteralPath $StateFile -PathType Leaf)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$sRaw = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8
$PrevDigest = ""
$LastTool = ""
$LastFile = ""
$mDig = [regex]::Match($sRaw, '"specDigest"\s*:\s*"([^"]*)"')
if ($mDig.Success) { $PrevDigest = $mDig.Groups[1].Value }
$mTl = [regex]::Match($sRaw, '"lastTool"\s*:\s*"([^"]*)"')
if ($mTl.Success) { $LastTool = $mTl.Groups[1].Value }
$mFl = [regex]::Match($sRaw, '"lastFilePath"\s*:\s*"([^"]*)"')
if ($mFl.Success) { $LastFile = $mFl.Groups[1].Value }

$StateObj = @{
    updatedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness = $Harness
    conversationId = $ConvId
    activeTurn = $false
    lastTool = $LastTool
    lastFilePath = $LastFile
    specDigest = $PrevDigest
} | ConvertTo-Json -Compress

Set-Content -LiteralPath $StateFile -Value $StateObj -Encoding UTF8
[Console]::Out.WriteLine('{}')
