#!/usr/bin/env pwsh
# Portable PowerShell Stop review & present-tense Markdown sync hook for Flow.
# Requires zero Python, Node.js, or external modules on Windows/Linux/macOS.
$ErrorActionPreference = "Stop"

$Harness = "claude"
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
    } elseif ($arg -like "-Harness=*") {
        $Harness = $arg.Substring(9)
    } elseif ($arg -eq "--project" -or $arg -eq "-Project") {
        if ($i + 1 -lt $args.Count) {
            $ProjectDir = [string]$args[$i + 1]
            $i++
        }
    } elseif ($arg -like "--project=*") {
        $ProjectDir = $arg.Substring(10)
    } elseif ($arg -like "-Project=*") {
        $ProjectDir = $arg.Substring(9)
    }
}

function Emit-Allow {
    if ($Harness -eq "json") {
        [Console]::Out.WriteLine('{"blocked":false,"reason":""}')
    } else {
        [Console]::Out.WriteLine('{}')
    }
    exit 0
}

function ConvertTo-JsonEscaped([string]$Text) {
    if ($null -eq $Text) { return "" }
    return $Text.Replace('\', '\\').Replace('"', '\"').Replace("`r", "").Replace("`t", " ").Replace("`n", "\n")
}

if ($Harness -eq "claude" -and -not [string]::IsNullOrEmpty($env:CURSOR_VERSION)) {
    Emit-Allow
}

$StopGateEnv = if (-not [string]::IsNullOrEmpty($env:FLOW_STOP_GATE)) { $env:FLOW_STOP_GATE.Trim().ToLowerInvariant() } else { "" }
if ($StopGateEnv -in @("off", "0", "false", "no", "advisory", "warn")) {
    Emit-Allow
}

$StdinPayload = ""
try {
    if ([Console]::IsInputRedirected) {
        $StdinPayload = [Console]::In.ReadToEnd()
    }
} catch {
    $StdinPayload = ""
}

$IsLeafSubagent = $false
$ConvId = ""
if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pattern in @(
            '"workspacePaths"\s*:\s*\[\s*"([^"]+)"',
            '"workspace_roots"\s*:\s*\[\s*"([^"]+)"',
            '"cwd"\s*:\s*"([^"]+)"',
            '"workspaceRoot"\s*:\s*"([^"]+)"'
        )) {
            $m = [regex]::Match($StdinPayload, $pattern)
            if ($m.Success) {
                $ProjectDir = $m.Groups[1].Value -replace '\\\\', '/'
                break
            }
        }
    }

    foreach ($convPat in @('"conversationId"\s*:\s*"([^"]+)"', '"session_id"\s*:\s*"([^"]+)"', '"conversation_id"\s*:\s*"([^"]+)"')) {
        $cm = [regex]::Match($StdinPayload, $convPat)
        if ($cm.Success) {
            $ConvId = $cm.Groups[1].Value
            break
        }
    }

    if ($Harness -match '^(agy|antigravity)$') {
        $trMatch = [regex]::Match($StdinPayload, '"terminationReason"\s*:\s*"([^"]*)"')
        if ($trMatch.Success -and $trMatch.Groups[1].Value -ne "" -and $trMatch.Groups[1].Value -ne "model_stop") {
            Emit-Allow
        }
        $errMatch = [regex]::Match($StdinPayload, '"error"\s*:\s*"([^"]+)"')
        if ($errMatch.Success) {
            Emit-Allow
        }
        $execMatch = [regex]::Match($StdinPayload, '"executionNum"\s*:\s*(\d+)')
        if ($execMatch.Success -and ([int]$execMatch.Groups[1].Value) -ge 2) {
            Emit-Allow
        }
    } elseif ($Harness -eq "cursor") {
        $stMatch = [regex]::Match($StdinPayload, '"status"\s*:\s*"([^"]*)"')
        if ($stMatch.Success -and $stMatch.Groups[1].Value -ne "" -and $stMatch.Groups[1].Value -ne "completed") {
            Emit-Allow
        }
        $lcMatch = [regex]::Match($StdinPayload, '"loop_count"\s*:\s*(\d+)')
        if ($lcMatch.Success -and ([int]$lcMatch.Groups[1].Value) -ge 1) {
            Emit-Allow
        }
    } else {
        if ([regex]::IsMatch($StdinPayload, '"stop_hook_active"\s*:\s*true')) {
            Emit-Allow
        }
    }

    if ([regex]::IsMatch($StdinPayload, '"parentConversationId"\s*:\s*"[^"]+"') -or
        [regex]::IsMatch($StdinPayload, '"lastUserInput"\s*:\s*"[^"]*(agents/(executor|researcher|code-reviewer|quality-reviewer|plan-generator)\.md|templates/agent/(plan|executor)-schema-card\.md|\.agents/agents/)')) {
        $IsLeafSubagent = $true
    }
}

if ([string]::IsNullOrEmpty($ProjectDir)) {
    if (-not [string]::IsNullOrEmpty($env:CURSOR_PROJECT_DIR)) {
        $ProjectDir = $env:CURSOR_PROJECT_DIR
    } elseif (-not [string]::IsNullOrEmpty($env:CLAUDE_PROJECT_DIR)) {
        $ProjectDir = $env:CLAUDE_PROJECT_DIR
    } else {
        $ProjectDir = (Get-Location).Path
    }
}

$EffectiveRoot = $ProjectDir
if ((-not (Test-Path -LiteralPath (Join-Path $ProjectDir ".agents") -PathType Container)) -and
    (Test-Path -LiteralPath (Join-Path $ProjectDir ".git") -PathType Leaf) -and
    (Get-Command git -ErrorAction SilentlyContinue)) {
    try {
        $commonDir = (& git -C $ProjectDir rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1)
        if (-not [string]::IsNullOrWhiteSpace($commonDir)) {
            $candMain = Split-Path -Parent $commonDir.Trim()
            if (-not [string]::IsNullOrWhiteSpace($candMain) -and (Test-Path -LiteralPath (Join-Path $candMain ".agents") -PathType Container)) {
                $EffectiveRoot = $candMain
            }
        }
    } catch {}
}

$tmpRaw = if (-not [string]::IsNullOrEmpty($env:TMPDIR)) { $env:TMPDIR.TrimEnd('/', '\') } else { [IO.Path]::GetTempPath().TrimEnd('/', '\') }
$rtBase = if (-not [string]::IsNullOrEmpty($env:FLOW_RUNTIME_DIR)) { $env:FLOW_RUNTIME_DIR.TrimEnd('/', '\') } else { Join-Path $tmpRaw "flow-runtime" }
$normRoot = ($EffectiveRoot -replace '\\', '/').TrimEnd('/')
$wsId = [regex]::Replace($normRoot, '[^A-Za-z0-9._-]', '_')
if ($wsId.Length -gt 120) { $wsId = $wsId.Substring($wsId.Length - 120) }
if ([string]::IsNullOrEmpty($wsId)) { $wsId = "default" }
$SubagentLeaseDir = Join-Path (Join-Path $rtBase $wsId) "subagents"
$SafeConv = if (-not [string]::IsNullOrEmpty($ConvId)) { [regex]::Replace($ConvId, '[^A-Za-z0-9._-]', '_') } else { "" }

if ($IsLeafSubagent) {
    if (-not [string]::IsNullOrEmpty($SafeConv)) {
        $leaseFile = Join-Path $SubagentLeaseDir "$SafeConv.lease"
        if (Test-Path -LiteralPath $leaseFile -PathType Leaf) {
            Remove-Item -LiteralPath $leaseFile -Force -ErrorAction SilentlyContinue
        }
    }
    Emit-Allow
}

$BundleRel = ".agents/bundles"
$StopGateCfg = "enforce"
$ShaTracking = "strict"
$SetupStateFile = Join-Path $EffectiveRoot ".agents/setup-state.json"
if (Test-Path -LiteralPath $SetupStateFile -PathType Leaf) {
    try {
        $SetupRaw = Get-Content -LiteralPath $SetupStateFile -Raw -Encoding UTF8
        $m = [regex]::Match($SetupRaw, '"bundle_root"\s*:\s*"([^"]+)"')
        if ($m.Success -and -not [string]::IsNullOrWhiteSpace($m.Groups[1].Value)) {
            $BundleRel = $m.Groups[1].Value.Trim()
        }
        $gm = [regex]::Match($SetupRaw, '"stop_gate"\s*:\s*"([^"]+)"')
        if ($gm.Success -and -not [string]::IsNullOrWhiteSpace($gm.Groups[1].Value)) {
            $StopGateCfg = $gm.Groups[1].Value.Trim().ToLowerInvariant()
        }
        $sm = [regex]::Match($SetupRaw, '"sha_tracking"\s*:\s*"([^"]+)"')
        if ($sm.Success -and -not [string]::IsNullOrWhiteSpace($sm.Groups[1].Value)) {
            $ShaTracking = $sm.Groups[1].Value.Trim().ToLowerInvariant()
        }
    } catch {
        $BundleRel = ".agents/bundles"
    }
}

if ($StopGateCfg -in @("off", "0", "false", "no", "advisory", "warn")) {
    Emit-Allow
}
if ($ShaTracking -notin @("strict", "advisory", "off")) {
    $ShaTracking = "strict"
}

if (Test-Path -LiteralPath $SubagentLeaseDir -PathType Container) {
    $nowEpoch = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    foreach ($lf in @(Get-ChildItem -LiteralPath $SubagentLeaseDir -Filter "*.lease" -File -ErrorAction SilentlyContinue)) {
        $lfBase = [IO.Path]::GetFileNameWithoutExtension($lf.Name)
        $lfTs = 0L
        $rawTs = (Get-Content -LiteralPath $lf.FullName -TotalCount 1 -ErrorAction SilentlyContinue)
        if (-not [long]::TryParse(([string]$rawTs).Trim(), [ref]$lfTs) -or ($nowEpoch - $lfTs) -gt 900) {
            Remove-Item -LiteralPath $lf.FullName -Force -ErrorAction SilentlyContinue
            continue
        }
        if ([string]::IsNullOrEmpty($SafeConv) -or $lfBase -ne $SafeConv) {
            Emit-Allow
        }
    }
}

if (-not [string]::IsNullOrEmpty($ConvId)) {
    foreach ($liveCand in @((Join-Path $EffectiveRoot ".agents/studio-live-state.json"), (Join-Path $ProjectDir ".agents/studio-live-state.json"))) {
        if (Test-Path -LiteralPath $liveCand -PathType Leaf) {
            try {
                $item = Get-Item -LiteralPath $liveCand
                if (([DateTime]::UtcNow - $item.LastWriteTimeUtc).TotalSeconds -le 900) {
                    $liveRaw = Get-Content -LiteralPath $liveCand -Raw -Encoding UTF8
                    $isAct = [regex]::IsMatch($liveRaw, '"activeTurn"\s*:\s*true')
                    $cm = [regex]::Match($liveRaw, '"conversationId"\s*:\s*"([^"]*)"')
                    $liveConv = if ($cm.Success) { $cm.Groups[1].Value } else { "" }
                    if ($isAct -and (-not [string]::IsNullOrEmpty($liveConv)) -and $liveConv -ne $ConvId) {
                        Emit-Allow
                    }
                }
            } catch {}
            break
        }
    }
}

$SpecsDir = Join-Path $EffectiveRoot "$BundleRel/specs"
if (-not (Test-Path -LiteralPath $SpecsDir -PathType Container)) {
    Emit-Allow
}

$HasGit = $false
$GitCmd = Get-Command git -ErrorAction SilentlyContinue
if ($null -ne $GitCmd) {
    try {
        $null = & git -C $ProjectDir rev-parse --is-inside-work-tree 2>$null
        if ($LASTEXITCODE -eq 0) {
            $HasGit = $true
        }
    } catch {
        $HasGit = $false
    }
}

$Violations = New-Object System.Collections.Generic.List[string]

function Get-FrontmatterMap([string[]]$Lines) {
    $map = @{}
    if ($Lines.Count -eq 0 -or $Lines[0].Trim() -ne "---") {
        return $map
    }
    for ($i = 1; $i -lt $Lines.Count; $i++) {
        $ln = $Lines[$i]
        if ($ln.Trim() -eq "---") { break }
        if ($ln -match '^([A-Za-z0-9_-]+):\s*(.*)$') {
            $k = $Matches[1]
            $v = ($Matches[2] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
            $map[$k] = $v
        }
    }
    return $map
}

function Get-OwnedPaths([string[]]$Lines) {
    $items = New-Object System.Collections.Generic.List[string]
    if ($Lines.Count -eq 0 -or $Lines[0].Trim() -ne "---") { return $items }
    $inOwned = $false
    for ($i = 1; $i -lt $Lines.Count; $i++) {
        $ln = $Lines[$i]
        if ($ln.Trim() -eq "---") { break }
        if ($ln -match '^(files|tests):\s*(.*)$') {
            $rest = ($Matches[2] -replace '\s+#.*$', '').Trim()
            if ([string]::IsNullOrEmpty($rest)) {
                $inOwned = $true
            } else {
                $inOwned = $false
                $trimmed = $rest.TrimStart('[').TrimEnd(']')
                foreach ($part in ($trimmed -split ',')) {
                    $clean = (($part.Trim().Trim('"').Trim("'")) -replace '::.*$', '') -replace '^\./', ''
                    if ($clean -and $clean -notin @("null", "~")) { $items.Add($clean) }
                }
            }
            continue
        }
        if ($ln -match '^[^\s-]') { $inOwned = $false }
        if ($inOwned -and $ln -match '^\s*-\s+(.+)$') {
            $clean = ((($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")) -replace '::.*$', '') -replace '^\./', ''
            if ($clean -and $clean -notin @("null", "~")) { $items.Add($clean) }
        }
    }
    return $items
}

function Test-LivingDocHygiene([string]$FilePath, [string]$RelLabel, [bool]$IsIndex) {
    $lines = @(Get-Content -LiteralPath $FilePath -Encoding UTF8)
    $inFm = $false
    $inSrc = $false
    $inFence = $false
    $srcIds = New-Object System.Collections.Generic.List[string]
    $fnDefs = @{}
    $pq = ""
    $pdr = ""
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $ln = $lines[$i]
        if ($i -eq 0 -and $ln.Trim() -eq "---") {
            if ($IsIndex) {
                $Violations.Add("${RelLabel}: subdirectory index.md must not contain YAML frontmatter")
                return
            }
            $inFm = $true
            continue
        }
        if ($inFm) {
            if ($ln.Trim() -eq "---") { $inFm = $false; $inSrc = $false; continue }
            if ($ln -match '^status:\s*(.+)$') {
                $sv = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                if ($sv -and $sv -notin @("draft", "stable", "deprecated")) {
                    $Violations.Add("${RelLabel}: invalid OKF status '$sv' (expected draft, stable, or deprecated; use state for workflow lifecycle)")
                    return
                }
            }
            if ($ln -match '^planning_quality:\s*(.+)$') {
                $pq = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
            }
            if ($ln -match '^planning_degraded_reason:\s*(.+)$') {
                $pdr = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
            }
            if ($ln -match '^sources:\s*$') { $inSrc = $true; continue }
            if ($inSrc -and $ln -match '^[^\s-]') { $inSrc = $false }
            if ($inSrc -and $ln -match '^\s*-?\s*id:\s*(.+)$') {
                $sid = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'")
                if ($sid) { $srcIds.Add($sid) }
            }
            continue
        }
        if ($ln -match '^\s*(```|~~~)') {
            $inFence = -not $inFence
            continue
        }
        if ($inFence) { continue }
        if ($ln -match '^\[\^([^\]]+)\]:') {
            $fnDefs[$Matches[1]] = $true
        }
        if ($ln -match '^\s*---\s*$') {
            $Violations.Add("${RelLabel}: standalone --- horizontal rule forbidden in bundle Markdown body")
            return
        }
        if ($ln -match '(?i)^\s*#+\s*(revision history|change history|changelog|decision history)(\s|:|$)') {
            $Violations.Add("${RelLabel}: historical changelog/revision section forbidden in present-tense living spec")
            return
        }
        if ($ln -match '^\s*-\s*\[[^\]]*\]\s*~~') {
            $Violations.Add("${RelLabel}: struck-through obsolete checklist item forbidden; rewrite in place in present tense")
            return
        }
    }
    if ($pq -eq "degraded" -and ([string]::IsNullOrEmpty($pdr) -or $pdr -in @("null", "~"))) {
        $Violations.Add("${RelLabel}: planning_quality is degraded without non-empty planning_degraded_reason")
        return
    }
    foreach ($sid in $srcIds) {
        if (-not $fnDefs.ContainsKey($sid)) {
            $Violations.Add("${RelLabel}: source id '$sid' missing matching [^$sid]: footnote in body")
            return
        }
    }
}

function Test-TasksAgainstSpec([string]$OwnerSpec, [string]$TasksDir, [string]$ScopeLabel) {
    $res = @{ Total = 0; Done = 0; Shas = (New-Object System.Collections.Generic.List[string]) }
    if (-not (Test-Path -LiteralPath $TasksDir -PathType Container)) {
        return $res
    }
    $specLines = @(Get-Content -LiteralPath $OwnerSpec -Encoding UTF8)
    $checklistLines = New-Object System.Collections.Generic.List[string]
    $inFm = $false
    $inFence = $false
    for ($i = 0; $i -lt $specLines.Count; $i++) {
        $ln = $specLines[$i]
        if ($i -eq 0 -and $ln.Trim() -eq "---") { $inFm = $true; continue }
        if ($inFm) { if ($ln.Trim() -eq "---") { $inFm = $false }; continue }
        if ($ln -match '^\s*(```|~~~)') { $inFence = -not $inFence; continue }
        if ($inFence) { continue }
        if ($ln -match '^\s*-\s*\[[ xX~!>-]\]') {
            $checklistLines.Add($ln)
        }
    }

    $taskFiles = Get-ChildItem -LiteralPath $TasksDir -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name
    foreach ($tf in $taskFiles) {
        if ($tf.Name -eq "index.md") { continue }
        $res.Total++
        $tLines = @(Get-Content -LiteralPath $tf.FullName -Encoding UTF8)
        $tfm = Get-FrontmatterMap $tLines
        $tStem = ($tf.Name -split '-')[0]
        $tId = if ($tfm.ContainsKey("id") -and $tfm["id"]) { $tfm["id"] } else { $tStem }
        $tState = if ($tfm.ContainsKey("state")) { $tfm["state"] } else { "pending" }
        $tCommit = if ($tfm.ContainsKey("commit")) { $tfm["commit"] } else { "" }

        $expMark = " "
        switch -Regex ($tState) {
            '^(completed|closed)$' {
                $expMark = "x"
                $res.Done++
                if ([string]::IsNullOrEmpty($tCommit) -or $tCommit -eq "null" -or $tCommit -eq "~") {
                    $Violations.Add("$ScopeLabel/$($tf.Name): state is $tState but commit SHA is missing")
                } elseif ($tCommit -notmatch '^[0-9a-fA-F]{7,40}$') {
                    $Violations.Add("$ScopeLabel/$($tf.Name): invalid hex commit SHA '$tCommit'")
                } else {
                    $res.Shas.Add($tCommit)
                    $ownedPaths = Get-OwnedPaths $tLines
                    if ($ShaTracking -ne "off" -and $HasGit -and $ownedPaths.Count -gt 0) {
                        $null = & git -C $ProjectDir cat-file -e "$tCommit^{commit}" 2>$null
                        if ($LASTEXITCODE -eq 0) {
                            $diffPaths = @(& git -C $ProjectDir diff-tree --no-commit-id --name-only -r --root $tCommit 2>$null)
                            $ownedOk = $false
                            foreach ($dp in $diffPaths) {
                                $cleanDp = $dp.Trim()
                                if (-not $cleanDp) { continue }
                                foreach ($op in $ownedPaths) {
                                    if ($cleanDp -eq $op -or $cleanDp.StartsWith("$op/") -or $op.StartsWith("$cleanDp/")) {
                                        $ownedOk = $true
                                        break
                                    }
                                }
                                if ($ownedOk) { break }
                            }
                            if (-not $ownedOk) {
                                $nonIgnoredOwned = New-Object System.Collections.Generic.List[string]
                                foreach ($op in $ownedPaths) {
                                    $null = & git -C $ProjectDir check-ignore -q -- $op 2>$null
                                    if ($LASTEXITCODE -ne 0) {
                                        $nonIgnoredOwned.Add($op)
                                    }
                                }
                                if ($nonIgnoredOwned.Count -gt 0) {
                                    $Violations.Add("$ScopeLabel/$($tf.Name): commit $tCommit did not modify any declared files or tests ($($nonIgnoredOwned -join ';'))")
                                }
                            }
                        }
                    }
                }
            }
            '^(deferred|skipped)$' {
                $expMark = "-"
                $res.Done++
                $dBy = if ($tfm.ContainsKey("deferred_by")) { $tfm["deferred_by"] } else { "" }
                $dRsn = if ($tfm.ContainsKey("deferred_reason")) { $tfm["deferred_reason"] } else { "" }
                if ($dBy -ne "user" -or [string]::IsNullOrEmpty($dRsn) -or $dRsn -in @("null", "~")) {
                    $Violations.Add("$ScopeLabel/$($tf.Name): state '$tState' requires deferred_by: user and a non-empty deferred_reason")
                }
            }
            '^in_progress$' { $expMark = "~" }
            '^blocked$' { $expMark = "!" }
            default { $expMark = " " }
        }

        $matchedLine = $null
        foreach ($cl in $checklistLines) {
            if ($cl.Contains("tasks/$($tf.Name)") -or $cl.Contains("($($tf.Name))") -or
                $cl.Contains("] $tId ") -or $cl.Contains("] ${tId}:") -or
                $cl.Contains("] $tStem ") -or $cl.Contains("] ${tStem}:")) {
                $matchedLine = $cl
                break
            }
        }
        if ($null -eq $matchedLine) {
            $Violations.Add("${ScopeLabel}: task worksheet $($tf.Name) is missing from owning spec.md checklist")
        } else {
            $mm = [regex]::Match($matchedLine, '^\s*-\s*\[([ xX~!>-])\]')
            $actualMark = $mm.Groups[1].Value.ToLowerInvariant()
            if ($actualMark -ne $expMark) {
                $Violations.Add("${ScopeLabel}: task $($tf.Name) has state marker [$actualMark] in spec.md but expected [$expMark]")
            } elseif ($expMark -eq "x" -and $ShaTracking -eq "strict" -and $tCommit -match '^[0-9a-fA-F]{7,40}$') {
                $sm = [regex]::Match($matchedLine, '\[([0-9a-fA-F]{7,40})\]')
                if ($sm.Success) {
                    $cSha = $sm.Groups[1].Value
                    if (-not ($tCommit.StartsWith($cSha) -or $cSha.StartsWith($tCommit))) {
                        $mmOk = $false
                        if ($HasGit) {
                            $null = & git -C $ProjectDir cat-file -e "$tCommit^{commit}" 2>$null
                            $tExists = ($LASTEXITCODE -eq 0)
                            $null = & git -C $ProjectDir cat-file -e "$cSha^{commit}" 2>$null
                            $cExists = ($LASTEXITCODE -eq 0)
                            if ($tExists -and $cExists) {
                                $pidT = Get-GitPatchId $tCommit
                                $pidC = Get-GitPatchId $cSha
                                if ($pidT -and ($pidT -eq $pidC)) {
                                    $mmOk = $true
                                }
                            } else {
                                $null = & git -C $ProjectDir merge-base --is-ancestor $tCommit HEAD 2>$null
                                $tOnHead = ($LASTEXITCODE -eq 0)
                                $null = & git -C $ProjectDir merge-base --is-ancestor $cSha HEAD 2>$null
                                $cOnHead = ($LASTEXITCODE -eq 0)
                                if ($tOnHead -ne $cOnHead) {
                                    $mmOk = $true
                                }
                            }
                        }
                        if (-not $mmOk) {
                            $Violations.Add("${ScopeLabel}: task $($tf.Name) commit $tCommit mismatches spec.md checklist SHA $cSha")
                        }
                    }
                }
            }
        }
    }
    return $res
}

function Get-GitPatchId([string]$ShaArg) {
    try {
        $diffOut = (& git -C $ProjectDir diff-tree --no-ext-diff -p --root $ShaArg 2>$null) -join "`n"
        if ([string]::IsNullOrEmpty($diffOut)) { return "" }
        $pidOut = ($diffOut | & git patch-id --stable 2>$null | Select-Object -First 1)
        if ($pidOut) {
            return ($pidOut.Trim() -split '\s+')[0]
        }
    } catch {}
    return ""
}

function Test-PatchInHistory([string]$NeedleSha, [string]$HaystackRev) {
    $needlePid = Get-GitPatchId $NeedleSha
    if ([string]::IsNullOrEmpty($needlePid)) { return $false }
    try {
        $logOut = (& git -C $ProjectDir log -n 100 --no-ext-diff -p --root $HaystackRev 2>$null) -join "`n"
        if ([string]::IsNullOrEmpty($logOut)) { return $false }
        $pidLines = @($logOut | & git patch-id --stable 2>$null)
        foreach ($pln in $pidLines) {
            $parts = $pln.Trim() -split '\s+'
            if ($parts.Count -gt 0 -and $parts[0] -eq $needlePid) {
                return $true
            }
        }
    } catch {}
    return $false
}

function Test-ReviewStamp([string]$RevSha, [System.Collections.Generic.List[string]]$TaskShas, [string]$Label) {
    if ([string]::IsNullOrEmpty($RevSha) -or $RevSha -eq "null" -or ($RevSha -notmatch '^[0-9a-fA-F]{7,40}$')) {
        $Violations.Add("${Label}: missing hex last_reviewed_commit (sync present-tense docs and run Zero-Context Review before stopping)")
        return
    }
    if ($ShaTracking -eq "off") { return }
    if ($HasGit) {
        $null = & git -C $ProjectDir cat-file -e "$RevSha^{commit}" 2>$null
        if ($LASTEXITCODE -ne 0) {
            return
        }
        if ($ShaTracking -eq "advisory") { return }
        $null = & git -C $ProjectDir merge-base --is-ancestor $RevSha HEAD 2>$null
        if ($LASTEXITCODE -ne 0) {
            return
        }
        foreach ($tSha in $TaskShas) {
            $null = & git -C $ProjectDir cat-file -e "$tSha^{commit}" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $null = & git -C $ProjectDir merge-base --is-ancestor $tSha $RevSha 2>$null
                if ($LASTEXITCODE -ne 0) {
                    if (-not (Test-PatchInHistory $tSha $RevSha)) {
                        $Violations.Add("${Label}: task commit $tSha is newer than last_reviewed_commit $RevSha; re-run Zero-Context Review")
                        return
                    }
                }
            }
        }
    }
}

$FlowDirs = Get-ChildItem -LiteralPath $SpecsDir -Directory -ErrorAction SilentlyContinue | Sort-Object Name
foreach ($fDir in $FlowDirs) {
    $rootSpec = Join-Path $fDir.FullName "spec.md"
    if (-not (Test-Path -LiteralPath $rootSpec -PathType Leaf)) { continue }
    $rootRaw = Get-Content -LiteralPath $rootSpec -Raw -Encoding UTF8
    $rootLines = @(Get-Content -LiteralPath $rootSpec -Encoding UTF8)
    $rfm = Get-FrontmatterMap $rootLines
    $rType = if ($rfm.ContainsKey("type")) { $rfm["type"] } else { "" }
    $rState = if ($rfm.ContainsKey("state")) { $rfm["state"] } else { "" }
    $rGate = if ($rfm.ContainsKey("gate")) { $rfm["gate"].ToLowerInvariant() } else { "" }
    $rPaused = if ($rfm.ContainsKey("paused")) { $rfm["paused"].ToLowerInvariant() } else { "" }
    $rHandoff = if ($rfm.ContainsKey("handoff")) { $rfm["handoff"].ToLowerInvariant() } else { "" }
    if ($rState -eq "archived" -or $rType -eq "flow") { continue }
    if ($rGate -in @("off", "advisory")) { continue }
    if ($rState -eq "paused" -or $rPaused -eq "true" -or $rHandoff -eq "true") { continue }

    $rHasCh = ($rfm.ContainsKey("has_chapters") -and $rfm["has_chapters"] -eq "true")
    $rCurrCh = if ($rfm.ContainsKey("current_chapter")) { $rfm["current_chapter"] } else { "" }
    $rRevSha = if ($rfm.ContainsKey("last_reviewed_commit")) { $rfm["last_reviewed_commit"] } else { "" }

    Test-LivingDocHygiene $rootSpec "specs/$($fDir.Name)/spec.md" $false

    $rootTasksDir = Join-Path $fDir.FullName "tasks"
    if (Test-Path -LiteralPath $rootTasksDir -PathType Container) {
        $rtFiles = Get-ChildItem -LiteralPath $rootTasksDir -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name
        foreach ($rtf in $rtFiles) {
            Test-LivingDocHygiene $rtf.FullName "specs/$($fDir.Name)/tasks/$($rtf.Name)" ($rtf.Name -eq "index.md")
        }
    }

    $chaptersDir = Join-Path $fDir.FullName "chapters"
    if ((Test-Path -LiteralPath $chaptersDir -PathType Container) -or $rHasCh) {
        $chIndex = Join-Path $chaptersDir "index.md"
        $chIndexRaw = ""
        if (-not (Test-Path -LiteralPath $chIndex -PathType Leaf)) {
            if (-not $IsLeafSubagent) {
                $Violations.Add("specs/$($fDir.Name)/chapters/index.md: missing chapter catalog index.md")
            }
        } else {
            Test-LivingDocHygiene $chIndex "specs/$($fDir.Name)/chapters/index.md" $true
            $chIndexRaw = Get-Content -LiteralPath $chIndex -Raw -Encoding UTF8
        }

        $chDirs = @()
        if (Test-Path -LiteralPath $chaptersDir -PathType Container) {
            $chDirs = @(Get-ChildItem -LiteralPath $chaptersDir -Filter "ch*" -Directory -ErrorAction SilentlyContinue | Sort-Object Name)
        }
        $chTotal = $chDirs.Count
        $chClosed = 0
        $currChFound = $false
        $currChCompleted = $false

        foreach ($cDir in $chDirs) {
            $chId = $cDir.Name
            $chSpec = Join-Path $cDir.FullName "spec.md"
            if (-not (Test-Path -LiteralPath $chSpec -PathType Leaf)) {
                $Violations.Add("specs/$($fDir.Name)/chapters/${chId}: missing spec.md")
                continue
            }
            Test-LivingDocHygiene $chSpec "specs/$($fDir.Name)/chapters/$chId/spec.md" $false

            $chTasksDir = Join-Path $cDir.FullName "tasks"
            if (Test-Path -LiteralPath $chTasksDir -PathType Container) {
                $ctFiles = Get-ChildItem -LiteralPath $chTasksDir -Filter "*.md" -File -ErrorAction SilentlyContinue | Sort-Object Name
                foreach ($ctf in $ctFiles) {
                    Test-LivingDocHygiene $ctf.FullName "specs/$($fDir.Name)/chapters/$chId/tasks/$($ctf.Name)" ($ctf.Name -eq "index.md")
                }
            }

            if (-not $IsLeafSubagent) {
                if ((Test-Path -LiteralPath $chIndex -PathType Leaf) -and (-not $chIndexRaw.Contains($chId))) {
                    $Violations.Add("specs/$($fDir.Name)/chapters/index.md: missing entry for chapter $chId")
                }
                if (-not $rootRaw.Contains($chId)) {
                    $Violations.Add("specs/$($fDir.Name)/spec.md: full-plan roadmap is missing chapter $chId")
                }
            }

            $cLines = @(Get-Content -LiteralPath $chSpec -Encoding UTF8)
            $cfm = Get-FrontmatterMap $cLines
            $cState = if ($cfm.ContainsKey("state")) { $cfm["state"] } else { "" }
            $cRevSha = if ($cfm.ContainsKey("last_reviewed_commit")) { $cfm["last_reviewed_commit"] } else { "" }
            $cPaused = if ($cfm.ContainsKey("paused")) { $cfm["paused"].ToLowerInvariant() } else { "" }
            $cHandoff = if ($cfm.ContainsKey("handoff")) { $cfm["handoff"].ToLowerInvariant() } else { "" }

            if ($chId -eq $rCurrCh) {
                $currChFound = $true
                if ($cState -in @("completed", "deferred", "skipped")) {
                    $currChCompleted = $true
                }
            }

            if ($cState -eq "paused" -or $cPaused -eq "true" -or $cHandoff -eq "true") {
                continue
            }

            $taskCheck = Test-TasksAgainstSpec $chSpec $chTasksDir "specs/$($fDir.Name)/chapters/$chId"
            if ($cState -in @("deferred", "skipped")) {
                $cDefBy = if ($cfm.ContainsKey("deferred_by")) { $cfm["deferred_by"] } else { "" }
                $cDefRsn = if ($cfm.ContainsKey("deferred_reason")) { $cfm["deferred_reason"] } else { "" }
                if ($cDefBy -ne "user" -or [string]::IsNullOrEmpty($cDefRsn) -or $cDefRsn -in @("null", "~")) {
                    $Violations.Add("specs/$($fDir.Name)/chapters/${chId}: state '$cState' requires deferred_by: user and a non-empty deferred_reason")
                }
                $chClosed++
                continue
            }

            $needReview = $false
            if ($cState -eq "completed") {
                if ($taskCheck.Total -eq 0 -or $taskCheck.Done -lt $taskCheck.Total) {
                    $Violations.Add("specs/$($fDir.Name)/chapters/${chId}: chapter cannot be marked completed while $($taskCheck.Total - $taskCheck.Done) of $($taskCheck.Total) task(s) remain incomplete (or 0 tasks exist)")
                }
                $chClosed++
                $needReview = $true
            } elseif ((-not $IsLeafSubagent) -and $taskCheck.Total -gt 0 -and $taskCheck.Done -eq $taskCheck.Total) {
                if ($rState -in @("active", "completed") -or $cState -eq "active") {
                    $Violations.Add("specs/$($fDir.Name)/chapters/${chId}: all $($taskCheck.Total) task(s) are done, but chapter is not closed (sync present-tense docs/roadmap, run Zero-Context Review, and set state: completed)")
                    $needReview = $true
                }
            }

            if ($needReview) {
                Test-ReviewStamp $cRevSha $taskCheck.Shas "specs/$($fDir.Name)/chapters/$chId"
                if ((-not $IsLeafSubagent) -and $cState -eq "completed") {
                    $escapedId = [regex]::Escape($chId)
                    if (-not [regex]::IsMatch($rootRaw, "(?m)^\s*-\s*\[[xX]\].*$escapedId")) {
                        $Violations.Add("specs/$($fDir.Name)/spec.md: completed chapter $chId must be marked [x] in root Implementation Plan")
                    }
                }
            }
        }

        if ($rState -eq "completed" -and ($chTotal -eq 0 -or $chClosed -lt $chTotal)) {
            $Violations.Add("specs/$($fDir.Name)/spec.md: flow cannot be marked completed while $($chTotal - $chClosed) of $chTotal chapter(s) remain open (anti-skip guard)")
        }

        if ((-not $IsLeafSubagent) -and $chTotal -gt 0) {
            if ($chClosed -lt $chTotal) {
                if ($rState -ne "completed" -and ([string]::IsNullOrEmpty($rCurrCh) -or $rCurrCh -eq "null" -or (-not $currChFound) -or $currChCompleted)) {
                    $Violations.Add("specs/$($fDir.Name)/spec.md: current_chapter '$rCurrCh' must advance to an open remaining chapter")
                }
            } elseif ($rState -eq "completed") {
                $emptyShas = New-Object System.Collections.Generic.List[string]
                Test-ReviewStamp $rRevSha $emptyShas "specs/$($fDir.Name)/spec.md"
            }
        }
    } else {
        $taskCheck = Test-TasksAgainstSpec $rootSpec $rootTasksDir "specs/$($fDir.Name)"
        if ($rState -eq "completed") {
            if ($taskCheck.Total -eq 0 -or $taskCheck.Done -lt $taskCheck.Total) {
                $Violations.Add("specs/$($fDir.Name)/spec.md: single-chapter flow cannot be marked completed while $($taskCheck.Total - $taskCheck.Done) of $($taskCheck.Total) task(s) remain incomplete (or 0 tasks exist)")
            }
            Test-ReviewStamp $rRevSha $taskCheck.Shas "specs/$($fDir.Name)/spec.md"
        } elseif ((-not $IsLeafSubagent) -and $rState -eq "active" -and $taskCheck.Total -gt 0 -and $taskCheck.Done -eq $taskCheck.Total) {
            Test-ReviewStamp $rRevSha $taskCheck.Shas "specs/$($fDir.Name)/spec.md"
        }
    }
}

if ($Violations.Count -eq 0) {
    Emit-Allow
}

$Reason = "Flow Stop Gate blocked turn completion — synchronize present-tense Markdown and complete Zero-Context Chapter Review before stopping: " + ($Violations -join "; ")
$EscapedReason = ConvertTo-JsonEscaped $Reason

switch -Regex ($Harness) {
    '^(agy|antigravity)$' {
        [Console]::Out.WriteLine("{`"decision`":`"continue`",`"reason`":`"$EscapedReason`"}")
    }
    '^cursor$' {
        [Console]::Out.WriteLine("{`"followup_message`":`"$EscapedReason`"}")
    }
    '^json$' {
        [Console]::Out.WriteLine("{`"blocked`":true,`"reason`":`"$EscapedReason`"}")
    }
    default {
        [Console]::Out.WriteLine("{`"decision`":`"block`",`"reason`":`"$EscapedReason`"}")
    }
}
