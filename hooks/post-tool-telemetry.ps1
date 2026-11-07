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
$ToolName = ""
$FilePath = ""

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pat in @('"workspacePaths"\s*:\s*\[\s*"([^"]+)"', '"cwd"\s*:\s*"([^"]+)"')) {
            $m = [regex]::Match($StdinPayload, $pat)
            if ($m.Success) { $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'; break }
        }
    }
    foreach ($pat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ConvId = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"toolCall"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"', '"tool_name"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $ToolName = $m.Groups[1].Value; break }
    }
    foreach ($pat in @('"Path"\s*:\s*"([^"]+)"', '"file_path"\s*:\s*"([^"]+)"')) {
        $m = [regex]::Match($StdinPayload, $pat)
        if ($m.Success) { $FilePath = $m.Groups[1].Value; break }
    }
}

if ([string]::IsNullOrEmpty($ProjectDir)) { $ProjectDir = (Get-Location).Path }
$AgentsDir = Join-Path $ProjectDir ".agents"
if (-not (Test-Path -LiteralPath $AgentsDir -PathType Container)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$StateFile = Join-Path $AgentsDir "studio-live-state.json"
$PrevDigest = ""
if (Test-Path -LiteralPath $StateFile -PathType Leaf) {
    $sRaw = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8
    $mDig = [regex]::Match($sRaw, '"specDigest"\s*:\s*"([^"]*)"')
    if ($mDig.Success) { $PrevDigest = $mDig.Groups[1].Value }
}

$StateObj = @{
    updatedAt = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
    harness = $Harness
    conversationId = $ConvId
    activeTurn = $true
    lastTool = $ToolName
    lastFilePath = $FilePath
    specDigest = $PrevDigest
} | ConvertTo-Json -Compress

Set-Content -LiteralPath $StateFile -Value $StateObj -Encoding UTF8
[Console]::Out.WriteLine('{}')
