# Flow SessionStart Hook Wrapper (PowerShell)
# Mirrors hooks/session-start.sh env-var dispatch so native Windows hosts
# (Claude Code / OpenCode / Codex / Cursor / Gemini) all get the right JSON schema.

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Detection {
    $detectScript = Join-Path $PSScriptRoot "detect-env.ps1"
    if (-not (Test-Path $detectScript)) {
        return "Error: Environment detection script not found at $detectScript"
    }
    try {
        $output = & $detectScript *>&1 | Out-String
        return $output
    } catch {
        return "Error during environment detection: $($_.Exception.Message)"
    }
}

function Write-Schema([string]$context) {
    $claude = $env:CLAUDE_PLUGIN_ROOT
    $opencode = $env:OPENCODE_PLUGIN_ROOT
    $codex = $env:CODEX_PLUGIN_ROOT
    $cursor = $env:CURSOR_PLUGIN_ROOT

    if ($claude -or $opencode) {
        $payload = @{
            hookSpecificOutput = @{
                hookEventName     = "SessionStart"
                additionalContext = $context
            }
        }
    } elseif ($codex) {
        $payload = @{ additional_context = $context }
    } elseif ($cursor) {
        $payload = @{ additional_context = $context }
    } else {
        $payload = @{ systemMessage = $context }
    }

    Write-Output ($payload | ConvertTo-Json -Compress -Depth 5)
}

Write-Schema (Invoke-Detection)
