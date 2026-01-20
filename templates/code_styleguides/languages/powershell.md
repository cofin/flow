# PowerShell Scripting Guide

Modern PowerShell patterns for cross-platform scripting.

## File Conventions

### Script Structure
```powershell
#Requires -Version 7.0
<#
.SYNOPSIS
    Brief description of the script.

.DESCRIPTION
    Detailed description of what the script does.

.PARAMETER InputPath
    Path to the input file.

.PARAMETER Force
    Skip confirmation prompts.

.EXAMPLE
    .\Script.ps1 -InputPath "data.json" -Force

.NOTES
    Author: Name
    Version: 1.0.0
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateScript({ Test-Path $_ })]
    [string]$InputPath,

    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Script body
```

### File Extensions
- Scripts: `.ps1`
- Modules: `.psm1`
- Module manifests: `.psd1`
- Format files: `.ps1xml`

## Naming Conventions

### Cmdlet Naming (Verb-Noun)
```powershell
# Use approved verbs
function Get-UserData { }      # Retrieve data
function Set-Configuration { } # Modify settings
function New-Report { }        # Create something
function Remove-TempFiles { }  # Delete items
function Invoke-Build { }      # Execute action

# Get approved verbs
Get-Verb | Sort-Object Verb
```

### Variable Naming
```powershell
# PascalCase for parameters and public variables
$UserName = "John"
$FilePath = "C:\data"

# camelCase for private/local variables
$localCounter = 0
$tempResult = $null

# SCREAMING_SNAKE_CASE for constants
$script:MAX_RETRIES = 3
$script:DEFAULT_TIMEOUT = 30
```

## Parameters

### Advanced Parameter Attributes
```powershell
function Get-Data {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        # Mandatory with validation
        [Parameter(Mandatory, Position = 0)]
        [ValidateNotNullOrEmpty()]
        [string]$Name,

        # Pipeline input
        [Parameter(ValueFromPipeline)]
        [string[]]$InputObject,

        # Validated set
        [ValidateSet('Dev', 'Staging', 'Prod')]
        [string]$Environment = 'Dev',

        # Range validation
        [ValidateRange(1, 100)]
        [int]$Count = 10,

        # Pattern validation
        [ValidatePattern('^[a-z]+$')]
        [string]$Identifier,

        # Script validation
        [ValidateScript({ Test-Path $_ -PathType Container })]
        [string]$Directory,

        # Switch parameter
        [switch]$Force
    )

    process {
        foreach ($item in $InputObject) {
            if ($PSCmdlet.ShouldProcess($item, "Process")) {
                # Do work
            }
        }
    }
}
```

### Parameter Sets
```powershell
function Get-Item {
    [CmdletBinding(DefaultParameterSetName = 'ByName')]
    param(
        [Parameter(ParameterSetName = 'ByName', Mandatory)]
        [string]$Name,

        [Parameter(ParameterSetName = 'ById', Mandatory)]
        [int]$Id,

        [Parameter(ParameterSetName = 'All')]
        [switch]$All
    )

    switch ($PSCmdlet.ParameterSetName) {
        'ByName' { Get-ItemByName -Name $Name }
        'ById'   { Get-ItemById -Id $Id }
        'All'    { Get-AllItems }
    }
}
```

## Error Handling

### Try/Catch/Finally
```powershell
try {
    $result = Invoke-RiskyOperation
    if (-not $result) {
        throw "Operation returned null"
    }
}
catch [System.IO.FileNotFoundException] {
    Write-Error "File not found: $_"
}
catch [System.UnauthorizedAccessException] {
    Write-Error "Access denied: $_"
}
catch {
    Write-Error "Unexpected error: $($_.Exception.Message)"
    throw  # Re-throw if needed
}
finally {
    # Cleanup always runs
    Remove-TempFiles
}
```

### Error Action and Terminating Errors
```powershell
# Make all errors terminating
$ErrorActionPreference = 'Stop'

# Per-command error action
Get-Content $path -ErrorAction Stop

# Ignore errors (use sparingly)
Remove-Item $path -ErrorAction SilentlyContinue

# Custom error records
$errorRecord = [System.Management.Automation.ErrorRecord]::new(
    [System.Exception]::new("Custom error message"),
    "CustomErrorId",
    [System.Management.Automation.ErrorCategory]::InvalidOperation,
    $targetObject
)
$PSCmdlet.WriteError($errorRecord)
```

## Output Handling

### Proper Output Patterns
```powershell
function Get-ProcessInfo {
    [CmdletBinding()]
    param([string]$Name)

    # Output objects, not text
    Get-Process -Name $Name | ForEach-Object {
        [PSCustomObject]@{
            Name       = $_.Name
            Id         = $_.Id
            Memory     = $_.WorkingSet64
            StartTime  = $_.StartTime
        }
    }
}

# Don't use Write-Host for data (it bypasses pipeline)
# Write-Host "Result: $value"  # Bad

# Use Write-Output or implicit output
Write-Output $result  # Explicit
$result               # Implicit (preferred)

# Use Write-Verbose for diagnostic info
Write-Verbose "Processing item: $item"

# Use Write-Debug for debugging
Write-Debug "Variable state: $($variable | ConvertTo-Json)"
```

### Pipeline Design
```powershell
function Process-Item {
    [CmdletBinding()]
    param(
        [Parameter(ValueFromPipeline)]
        [object]$InputObject
    )

    begin {
        # Run once at start
        $results = [System.Collections.Generic.List[object]]::new()
    }

    process {
        # Run for each pipeline item
        $processed = Transform-Data $InputObject
        $results.Add($processed)
    }

    end {
        # Run once at end
        $results
    }
}
```

## Control Flow

### Conditionals
```powershell
# If/ElseIf/Else
if ($condition) {
    # ...
}
elseif ($otherCondition) {
    # ...
}
else {
    # ...
}

# Ternary operator (PS 7+)
$result = $condition ? 'Yes' : 'No'

# Null coalescing (PS 7+)
$value = $possiblyNull ?? 'default'

# Null conditional assignment (PS 7+)
$value ??= 'default'  # Assign if null
```

### Switch Statement
```powershell
switch -Regex ($input) {
    '^error' { Write-Error $_ }
    '^warn'  { Write-Warning $_ }
    { $_ -gt 100 } { Write-Output "Large: $_" }
    default { Write-Output $_ }
}

# File processing
switch -File $logPath {
    { $_ -match 'ERROR' } { $errors++ }
    { $_ -match 'WARN' }  { $warnings++ }
}
```

### Loops
```powershell
# ForEach-Object (pipeline)
$items | ForEach-Object { Process-Item $_ }

# foreach statement (faster for collections)
foreach ($item in $collection) {
    Process-Item $item
}

# For loop
for ($i = 0; $i -lt 10; $i++) {
    Write-Output $i
}

# While loop
while ($condition) {
    # ...
}

# Do-While/Do-Until
do {
    $result = Get-NextItem
} while ($result -ne $null)
```

## Working with Objects

### Creating Objects
```powershell
# PSCustomObject (preferred)
$user = [PSCustomObject]@{
    Name  = 'John'
    Email = 'john@example.com'
    Role  = 'Admin'
}

# Add type name for formatting
$user.PSObject.TypeNames.Insert(0, 'MyApp.User')

# Ordered hashtable
$config = [ordered]@{
    Server = 'localhost'
    Port   = 8080
}
```

### Object Manipulation
```powershell
# Select properties
$users | Select-Object Name, Email

# Add calculated properties
$users | Select-Object Name, @{
    Name = 'FullName'
    Expression = { "$($_.FirstName) $($_.LastName)" }
}

# Filter
$users | Where-Object { $_.Age -gt 18 }
$users | Where-Object Age -gt 18  # Simplified syntax

# Sort
$users | Sort-Object Name -Descending

# Group
$users | Group-Object Department
```

## Modules

### Module Structure
```
MyModule/
├── MyModule.psd1          # Manifest
├── MyModule.psm1          # Root module
├── Public/                # Exported functions
│   ├── Get-Something.ps1
│   └── Set-Something.ps1
├── Private/               # Internal functions
│   └── Helper.ps1
└── Tests/
    └── MyModule.Tests.ps1
```

### Module Manifest
```powershell
# MyModule.psd1
@{
    RootModule        = 'MyModule.psm1'
    ModuleVersion     = '1.0.0'
    GUID              = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
    Author            = 'Your Name'
    Description       = 'Module description'
    PowerShellVersion = '7.0'
    FunctionsToExport = @('Get-Something', 'Set-Something')
    CmdletsToExport   = @()
    VariablesToExport = @()
    AliasesToExport   = @()
    PrivateData       = @{
        PSData = @{
            Tags       = @('Tag1', 'Tag2')
            ProjectUri = 'https://github.com/...'
        }
    }
}
```

### Module Root File
```powershell
# MyModule.psm1
$Public = @(Get-ChildItem -Path "$PSScriptRoot/Public/*.ps1" -ErrorAction SilentlyContinue)
$Private = @(Get-ChildItem -Path "$PSScriptRoot/Private/*.ps1" -ErrorAction SilentlyContinue)

foreach ($file in @($Public + $Private)) {
    try {
        . $file.FullName
    }
    catch {
        Write-Error "Failed to import $($file.FullName): $_"
    }
}

Export-ModuleMember -Function $Public.BaseName
```

## Best Practices

- Use `Set-StrictMode -Version Latest` to catch common mistakes
- Use `[CmdletBinding()]` for advanced function features
- Return objects, not formatted strings
- Support `-WhatIf` and `-Confirm` for destructive operations
- Use approved verbs for function names
- Validate parameters at the boundary
- Use splatting for long parameter lists
- Write Pester tests for modules

## Anti-Patterns

```powershell
# Bad: Using aliases in scripts
ls | % { $_.Name }

# Good: Use full cmdlet names
Get-ChildItem | ForEach-Object { $_.Name }

# Bad: Write-Host for data output
Write-Host "User: $user"

# Good: Write-Output or return objects
[PSCustomObject]@{ User = $user }

# Bad: String concatenation for paths
$path = $dir + "\" + $file

# Good: Join-Path
$path = Join-Path $dir $file

# Bad: Backticks for line continuation
Get-Process | `
    Where-Object { $_.CPU -gt 10 }

# Good: Pipeline naturally continues
Get-Process |
    Where-Object { $_.CPU -gt 10 }

# Bad: Using $null on left side
if ($value -eq $null)

# Good: $null on left side (avoids array comparison issues)
if ($null -eq $value)
```
