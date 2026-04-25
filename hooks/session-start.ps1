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
    # Mirror session-start.sh dispatch. Gemini also exports CLAUDE_PROJECT_DIR
    # as a compat alias, so check CLAUDE_PLUGIN_ROOT (which Gemini does NOT set)
    # to disambiguate Claude from Gemini.
    $host = 'unknown'
    if ($env:CLAUDE_PLUGIN_ROOT) {
        $host = 'claude'
    } elseif ($env:GEMINI_SESSION_ID -or $env:GEMINI_CWD -or $env:GEMINI_PROJECT_DIR) {
        $host = 'gemini'
    } elseif ($env:OPENCODE_PLUGIN_ROOT -or $env:FLOW_PLUGIN_ROOT) {
        $host = 'opencode'
    } elseif ($env:CODEX_PLUGIN_ROOT) {
        $host = 'codex'
    } elseif ($env:CURSOR_PLUGIN_ROOT) {
        $host = 'cursor'
    }

    switch ($host) {
        { $_ -in 'claude','opencode','codex' } {
            $payload = @{
                hookSpecificOutput = @{
                    hookEventName     = 'SessionStart'
                    additionalContext = $context
                }
            }
        }
        'gemini' {
            $payload = @{
                hookSpecificOutput = @{
                    hookEventName     = 'SessionStart'
                    additionalContext = $context
                }
                systemMessage      = $context
            }
        }
        default {
            $payload = @{ additional_context = $context }
        }
    }

    Write-Output ($payload | ConvertTo-Json -Compress -Depth 5)
}

Write-Schema (Invoke-Detection)
