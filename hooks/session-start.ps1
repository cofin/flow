# Gemini CLI SessionStart Hook Wrapper (PowerShell)
# Receives JSON on stdin, returns JSON on stdout

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Main {
    $detectScript = Join-Path $PSScriptRoot "detect-env.ps1"
    $context = ""

    if (Test-Path $detectScript) {
        try {
            # Capture output from the detection script
            $context = & $detectScript
        } catch {
            $context = "Error during environment detection: $($_.Exception.Message)"
        }
    } else {
        $context = "Error: Environment detection script not found at $detectScript"
    }

    # Extract the context and escape for JSON
    # We use ConvertTo-Json which handles the escaping correctly
    $output = @{
        systemMessage = ($context | Out-String)
    }

    Write-Output ($output | ConvertTo-Json -Compress)
}

Main

