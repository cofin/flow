# detect-env.ps1 - Emit Flow priming context from the OKF bundles as markdown.
#
# Windows twin of detect-env.sh; output mirrors `tools/priming.py --markdown`.
# Runtime dependency policy: PowerShell only — no Python at runtime.

$ErrorActionPreference = 'Stop'

function Find-ProjectRoot {
    $dir = (Get-Location).Path
    while ($dir) {
        if (Test-Path (Join-Path $dir '.agents') -PathType Container) {
            return $dir
        }
        $parent = Split-Path -Parent $dir
        if (-not $parent -or $parent -eq $dir) { break }
        $dir = $parent
    }
    return (Get-Location).Path
}

function Get-ConfigValue {
    param([string]$File, [string]$Key)
    if (-not (Test-Path $File -PathType Leaf)) { return $null }
    try {
        $data = Get-Content -Raw -Path $File | ConvertFrom-Json
        return $data.$Key
    } catch {
        return $null
    }
}

function Get-Frontmatter {
    param([string]$File)
    $fm = @{}
    if (-not (Test-Path $File -PathType Leaf)) { return $fm }
    $lines = Get-Content -Path $File
    if ($lines.Count -eq 0 -or $lines[0] -ne '---') { return $fm }
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq '---') { break }
        $idx = $lines[$i].IndexOf(':')
        if ($idx -gt 0) {
            $key = $lines[$i].Substring(0, $idx).Trim()
            $value = $lines[$i].Substring($idx + 1).Trim().Trim('"').Trim("'")
            if (-not $fm.ContainsKey($key)) { $fm[$key] = $value }
        }
    }
    return $fm
}

function Get-Body {
    param([string]$File)
    if (-not (Test-Path $File -PathType Leaf)) { return @() }
    $lines = @(Get-Content -Path $File)
    if ($lines.Count -eq 0 -or $lines[0] -ne '---') { return $lines }
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq '---') {
            if ($i + 1 -ge $lines.Count) { return @() }
            return $lines[($i + 1)..($lines.Count - 1)]
        }
    }
    return $lines
}

function Get-StateOf {
    param([hashtable]$Frontmatter, [string]$Fallback)
    if ($Frontmatter['state']) { return $Frontmatter['state'] }
    if ($Frontmatter['status']) { return $Frontmatter['status'] }
    return $Fallback
}

function Get-Identity {
    param([string]$File)
    $out = @()
    foreach ($line in (Get-Body $File)) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) { continue }
        $out += $trimmed
        if ($out.Count -eq 5) { break }
    }
    return ($out -join "`n")
}

function Get-Truths {
    param([string]$File)
    $body = Get-Body $File
    if ($body.Count -eq 0) { return '' }

    $text = $body -join "`n"
    $startMark = '<!-- truth: start -->'
    $endMark = '<!-- truth: end -->'
    $start = $text.IndexOf($startMark)
    $end = $text.IndexOf($endMark)
    if ($start -ge 0 -and $end -gt $start) {
        return $text.Substring($start + $startMark.Length, $end - $start - $startMark.Length).Trim()
    }

    $items = @()
    foreach ($line in $body) {
        $trimmed = $line.Trim()
        if ($trimmed -match '^(- |\* |1\. )') {
            $items += $trimmed
            if ($items.Count -eq 10) { break }
        }
    }
    if ($items.Count -gt 0) { return ($items -join "`n") }

    $plain = ($body | Where-Object { -not $_.Trim().StartsWith('#') }) -join "`n"
    $plain = $plain.Trim()
    if ($plain.Length -gt 200) { $plain = $plain.Substring(0, 200) }
    return $plain
}

function Get-RelPath {
    param([string]$Path, [string]$Root)
    $rel = $Path.Substring($Root.Length).TrimStart('\', '/')
    return ($rel -replace '\\', '/')
}

$projectRoot = Find-ProjectRoot
$configFile = Join-Path $projectRoot '.agents/config.json'

$bundlesDir = Join-Path $projectRoot '.agents/bundles'
$cfgBundles = Get-ConfigValue -File $configFile -Key 'bundles_dir'
if ($cfgBundles) { $bundlesDir = Join-Path $projectRoot $cfgBundles }
$knowledgeDir = Join-Path $bundlesDir 'knowledge'
$cfgKnowledge = Get-ConfigValue -File $configFile -Key 'knowledge_dir'
if ($cfgKnowledge) { $knowledgeDir = Join-Path $projectRoot $cfgKnowledge }

$blocks = @()

# --- Project Purpose ---
$identity = Get-Identity (Join-Path $knowledgeDir 'product/product.md')
if ($identity) {
    $blocks += "## Project Purpose`n$identity"
}

# --- Core Project Invariants ---
$truthSections = @()
foreach ($filename in @('tech-stack.md', 'workflow.md', 'patterns.md')) {
    $sub = switch ($filename) {
        'tech-stack.md' { 'product' }
        'patterns.md' { 'patterns' }
        default { 'workflow' }
    }
    $truths = Get-Truths (Join-Path $knowledgeDir "$sub/$filename")
    if ($truths) {
        $heading = $filename.Substring(0, 1).ToUpper() + $filename.Substring(1)
        $truthSections += "### $heading Invariants`n$truths"
    }
}
if ($truthSections.Count -gt 0) {
    $blocks += "## Core Project Invariants`n" + ($truthSections -join "`n`n")
}

# --- Active Flows & Tasks ---
$specsDir = Join-Path $bundlesDir 'specs'
$flowLines = @()
if (Test-Path $specsDir -PathType Container) {
    foreach ($specDir in (Get-ChildItem -Path $specsDir -Directory | Sort-Object Name)) {
        $specFile = Join-Path $specDir.FullName 'spec.md'
        if (-not (Test-Path $specFile -PathType Leaf)) { continue }
        $fm = Get-Frontmatter $specFile
        $state = Get-StateOf -Frontmatter $fm -Fallback 'planned'
        if ($state -notin @('planned', 'active')) { continue }

        $flowId = if ($fm['flow_id']) { $fm['flow_id'] } elseif ($fm['id']) { $fm['id'] } else { $specDir.Name }
        $title = if ($fm['title']) { $fm['title'] } else { $flowId }
        $relSpec = Get-RelPath -Path $specFile -Root $projectRoot

        $flowLines += "### Flow: [$title]($relSpec) ($state)"
        if ($fm['description']) { $flowLines += "*$($fm['description'])*" }

        $taskLines = @()
        $tasksDir = Join-Path $specDir.FullName 'tasks'
        if (Test-Path $tasksDir -PathType Container) {
            foreach ($taskFile in (Get-ChildItem -Path $tasksDir -Filter '*.md' -File | Sort-Object Name)) {
                $tfm = Get-Frontmatter $taskFile.FullName
                $tstate = Get-StateOf -Frontmatter $tfm -Fallback 'open'
                if ($tstate -notin @('open', 'in_progress', 'blocked')) { continue }
                $ttitle = if ($tfm['title']) { $tfm['title'] } else { $taskFile.BaseName }
                $tpriority = if ($tfm['priority']) { $tfm['priority'] } else { 'P2' }
                $relTask = Get-RelPath -Path $taskFile.FullName -Root $projectRoot
                $taskLines += "- [$tpriority] [$ttitle]($relTask) ($tstate)"
            }
        }
        if ($taskLines.Count -gt 0) {
            $flowLines += 'Pending Tasks:'
            $flowLines += $taskLines
        } else {
            $flowLines += 'No active tasks.'
        }
    }
}
if ($flowLines.Count -gt 0) {
    $blocks += "## Active Flows & Tasks`n" + ($flowLines -join "`n")
}

# --- Custom Project Skills ---
$skillLines = @()
$seen = @{}
foreach ($skillRoot in @((Join-Path $projectRoot '.agents/skills'), (Join-Path $bundlesDir 'skills'))) {
    if (-not (Test-Path $skillRoot -PathType Container)) { continue }
    foreach ($skillDir in (Get-ChildItem -Path $skillRoot -Directory | Sort-Object Name)) {
        if ($seen.ContainsKey($skillDir.Name)) { continue }
        $skillFile = Join-Path $skillDir.FullName 'SKILL.md'
        if (-not (Test-Path $skillFile -PathType Leaf)) { continue }
        $sfm = Get-Frontmatter $skillFile
        $name = if ($sfm['name']) { $sfm['name'] } else { $skillDir.Name }
        $desc = if ($sfm['description']) { $sfm['description'] } else { '' }
        $relSkill = Get-RelPath -Path $skillFile -Root $projectRoot
        $skillLines += "- **[$name]($relSkill)**: $desc"
        $seen[$skillDir.Name] = $true
    }
}
if ($skillLines.Count -gt 0) {
    $blocks += "## Custom Project Skills`n" + ($skillLines -join "`n")
}

# --- Emit ---
if ($blocks.Count -eq 0) {
    Write-Output 'No project context resolved.'
} else {
    Write-Output ($blocks -join "`n`n")
}
