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
if (-not (Test-Path -LiteralPath $AgentsDir -PathType Container)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$BundleRel = ".agents/bundles"
$SetupState = Join-Path $AgentsDir "setup-state.json"
if (Test-Path -LiteralPath $SetupState -PathType Leaf) {
    $raw = Get-Content -LiteralPath $SetupState -Raw -Encoding UTF8
    $m = [regex]::Match($raw, '"bundle_root"\s*:\s*"([^"]+)"')
    if ($m.Success) { $BundleRel = $m.Groups[1].Value.Trim() }
}

$Acc = New-Object System.Collections.Generic.List[string]
$SpecsDir = Join-Path $ProjectDir "$BundleRel/specs"
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
$CommentsFile = Join-Path $AgentsDir "studio-comments.json"
if (Test-Path -LiteralPath $CommentsFile -PathType Leaf) {
    $chash = (Get-FileHash -LiteralPath $CommentsFile -Algorithm SHA256).Hash.Substring(0, 16)
    $Acc.Add("comments=$chash")
}

if ($Acc.Count -eq 0) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$FinalDigest = ($Acc -join ";")
$StateFile = Join-Path $AgentsDir "studio-live-state.json"
$PrevDigest = ""
$ActiveTurn = $false
if (Test-Path -LiteralPath $StateFile -PathType Leaf) {
    $sRaw = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8
    $mDig = [regex]::Match($sRaw, '"specDigest"\s*:\s*"([^"]*)"')
    if ($mDig.Success) { $PrevDigest = $mDig.Groups[1].Value }
    if ($sRaw -match '"activeTurn"\s*:\s*true') { $ActiveTurn = $true }
}

$NowIso = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$StateObj = @{
    updatedAt = $NowIso
    harness = $Harness
    activeTurn = $ActiveTurn
    specDigest = $FinalDigest
} | ConvertTo-Json -Compress

if ([string]::IsNullOrEmpty($PrevDigest) -or $PrevDigest -eq $FinalDigest -or $ActiveTurn) {
    Set-Content -LiteralPath $StateFile -Value $StateObj -Encoding UTF8
    [Console]::Out.WriteLine('{}')
    exit 0
}

Set-Content -LiteralPath $StateFile -Value $StateObj -Encoding UTF8
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
