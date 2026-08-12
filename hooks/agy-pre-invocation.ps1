# agy-pre-invocation.ps1 - Antigravity PreInvocation hook for Flow priming.
#
# Windows twin of agy-pre-invocation.sh: injects priming context once per
# conversation via injectSteps. Always exits 0.

$ErrorActionPreference = 'SilentlyContinue'

$inputText = [Console]::In.ReadToEnd()
$conversationId = 'unknown'
$invocationNum = $null
$artifactDir = $null

try {
    $payload = $inputText | ConvertFrom-Json
    if ($payload.conversationId) { $conversationId = $payload.conversationId }
    if ($null -ne $payload.invocationNum) { $invocationNum = [int]$payload.invocationNum }
    if ($payload.artifactDirectoryPath) { $artifactDir = $payload.artifactDirectoryPath }
} catch {}

if ($null -ne $invocationNum -and $invocationNum -ne 0) {
    Write-Output '{"injectSteps": []}'
    exit 0
}

$markerDir = if ($artifactDir -and (Test-Path $artifactDir -PathType Container)) { $artifactDir } else { $env:TEMP }
$marker = Join-Path $markerDir ".flow-primed-$conversationId"
if (Test-Path $marker -PathType Leaf) {
    Write-Output '{"injectSteps": []}'
    exit 0
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$context = & (Join-Path $scriptDir 'detect-env.ps1')
if (-not $context) { $context = 'No project context resolved.' }
if ($context -is [array]) { $context = $context -join "`n" }

$step = @{ ephemeralMessage = "$context" }
$output = @{ injectSteps = @($step) } | ConvertTo-Json -Depth 4 -Compress
Write-Output $output

New-Item -ItemType File -Path $marker -Force | Out-Null
exit 0
