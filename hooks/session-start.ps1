# Gemini CLI SessionStart Hook Wrapper (PowerShell)
# Receives JSON on stdin, returns JSON on stdout

try {
    $context = & "$PSScriptRoot/detect-env.ps1"
} catch {
    $context = "Error during environment detection."
}

# Extract the context and escape for JSON
$escaped_context = $context | Out-String | ConvertTo-Json

# Return the systemMessage to Gemini CLI
Write-Output "{`"systemMessage`": $escaped_context}"
