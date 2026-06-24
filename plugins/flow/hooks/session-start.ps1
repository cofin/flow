# Flow SessionStart Hook Wrapper (PowerShell)
# Mirrors hooks/session-start.sh env-var dispatch so native Windows harnesses
# (Antigravity / Claude Code / OpenCode / Codex / Cursor) all get the right JSON schema.

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
    # Mirror session-start.sh dispatch. Codex exports PLUGIN_ROOT (canonical) and
    # CLAUDE_PLUGIN_ROOT (compat alias), so check the Codex-specific markers BEFORE
    # the Claude branch.
    $harness = 'unknown'
    if ($env:FLOW_HARNESS) {
        # Explicit override set by a harness hook command (e.g. Codex sets
        # FLOW_HARNESS=codex) is authoritative when the harness exports no plugin-root var.
        $harness = $env:FLOW_HARNESS
    } elseif ($env:ANTIGRAVITY_PLUGIN_ROOT -or $env:AGY_PLUGIN_ROOT) {
        $harness = 'antigravity'
    } elseif ($env:CODEX_PLUGIN_ROOT -or $env:PLUGIN_ROOT) {
        $harness = 'codex'
    } elseif ($env:CLAUDE_PLUGIN_ROOT) {
        $harness = 'claude'
    } elseif ($env:OPENCODE_PLUGIN_ROOT -or $env:FLOW_PLUGIN_ROOT) {
        $harness = 'opencode'
    } elseif ($env:CURSOR_PLUGIN_ROOT) {
        $harness = 'cursor'
    }

    switch ($harness) {
        { $_ -in 'antigravity','claude','opencode','codex' } {
            $payload = @{
                hookSpecificOutput = @{
                    hookEventName     = 'SessionStart'
                    additionalContext = $context
                }
            }
        }
        default {
            $payload = @{ additional_context = $context }
        }
    }

    Write-Output ($payload | ConvertTo-Json -Compress -Depth 5)
}

Write-Schema (Invoke-Detection)
