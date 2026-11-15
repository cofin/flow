#!/usr/bin/env pwsh
# Portable PowerShell PreToolUse safety guard for Flow.
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
    } elseif ($arg -eq "--project" -or $arg -eq "-Project") {
        if ($i + 1 -lt $args.Count) {
            $ProjectDir = [string]$args[$i + 1]
            $i++
        }
    } elseif ($arg -like "--project=*") {
        $ProjectDir = $arg.Substring(10)
    }
}

if ($Harness -eq "claude" -and -not [string]::IsNullOrEmpty($env:CURSOR_VERSION)) {
    [Console]::Out.WriteLine('{}')
    exit 0
}

$StdinPayload = ""
try {
    if ([Console]::IsInputRedirected) {
        $StdinPayload = [Console]::In.ReadToEnd()
    }
} catch {
    $StdinPayload = ""
}

$PayloadCwd = ""
$ToolName = ""
$AgentId = ""
$CmdLine = ""
$TargetPath = ""

if (-not [string]::IsNullOrWhiteSpace($StdinPayload)) {
    if ([string]::IsNullOrEmpty($ProjectDir)) {
        foreach ($pattern in @(
            '"workspacePaths"\s*:\s*\[\s*"([^"]+)"',
            '"workspace_roots"\s*:\s*\[\s*"([^"]+)"',
            '"cwd"\s*:\s*"([^"]+)"',
            '"workspaceRoot"\s*:\s*"([^"]+)"'
        )) {
            $mp = [regex]::Match($StdinPayload, $pattern)
            if ($mp.Success) {
                $ProjectDir = $mp.Groups[1].Value -replace '\\\\', '/'
                break
            }
        }
    }

    $mCwd = [regex]::Match($StdinPayload, '"cwd"\s*:\s*"([^"]+)"')
    if ($mCwd.Success) {
        $PayloadCwd = $mCwd.Groups[1].Value -replace '\\\\', '/'
    }

    $mTool = [regex]::Match($StdinPayload, '"toolCall"\s*:\s*\{\s*"name"\s*:\s*"([^"]+)"')
    if (-not $mTool.Success) {
        $mTool = [regex]::Match($StdinPayload, '"tool_name"\s*:\s*"([^"]+)"')
    }
    if ($mTool.Success) { $ToolName = $mTool.Groups[1].Value }

    $mCmd = [regex]::Match($StdinPayload, '"CommandLine"\s*:\s*"((?:[^"\\]|\\.)*)"')
    if (-not $mCmd.Success) {
        $mCmd = [regex]::Match($StdinPayload, '"command"\s*:\s*"((?:[^"\\]|\\.)*)"')
    }
    if ($mCmd.Success) {
        $CmdLine = [regex]::Replace($mCmd.Groups[1].Value, '\\(["\\/ntr])', {
            param($m)
            switch ($m.Groups[1].Value) {
                '\' { '\' }
                '/' { '/' }
                '"' { '"' }
                'n' { "`n" }
                'r' { '' }
                't' { ' ' }
                default { $m.Groups[1].Value }
            }
        })
    }

    foreach ($pPat in @('"TargetPath"\s*:\s*"([^"]+)"', '"Path"\s*:\s*"([^"]+)"', '"file_path"\s*:\s*"([^"]+)"', '"TargetFile"\s*:\s*"([^"]+)"')) {
        $mTp = [regex]::Match($StdinPayload, $pPat)
        if ($mTp.Success) {
            $TargetPath = ($mTp.Groups[1].Value -replace '\\\\', '/' -replace '\\', '/')
            break
        }
    }

    foreach ($pat in @('"agentName"\s*:\s*"([^"]+)"', '"agent_type"\s*:\s*"([^"]+)"', '"subagent_type"\s*:\s*"([^"]+)"')) {
        $mAg = [regex]::Match($StdinPayload, $pat)
        if ($mAg.Success) {
            $AgentId = $mAg.Groups[1].Value
            break
        }
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

$BaseDir = if (-not [string]::IsNullOrWhiteSpace($PayloadCwd)) { $PayloadCwd } else { $ProjectDir }

function Resolve-TargetDir([string]$RawDir, [string]$RelBase) {
    $norm = if ($null -eq $RawDir) { "" } else { ($RawDir -replace '\\', '/').Trim() }
    while ($norm.Length -gt 1 -and ($norm -notmatch '^[A-Za-z]:/$') -and $norm.EndsWith('/')) {
        $norm = $norm.Substring(0, $norm.Length - 1)
    }
    if ([string]::IsNullOrEmpty($norm) -or $norm -eq ".") {
        return $RelBase
    }
    $joined = ""
    if ($norm.StartsWith('/') -or ($norm -match '^[A-Za-z]:(?:/|$)')) {
        $joined = $norm
    } elseif ($RelBase -eq "/") {
        $joined = "/$norm"
    } elseif (-not [string]::IsNullOrWhiteSpace($RelBase)) {
        $joined = "$($RelBase.TrimEnd('/'))/$norm"
    } else {
        $joined = $norm
    }
    if (Test-Path -LiteralPath $joined -PathType Container) {
        try {
            return ((Resolve-Path -LiteralPath $joined).Path -replace '\\', '/')
        } catch {
            return $joined
        }
    }
    return $joined
}

function Test-IncompleteFlowSpec([string]$FlowId, [string]$RawTargetDir = "") {
    if ([string]::IsNullOrEmpty($FlowId)) { return $false }
    $anchor = if ([string]::IsNullOrWhiteSpace($RawTargetDir)) { $BaseDir } else { $RawTargetDir }
    $targetDir = Resolve-TargetDir $anchor $BaseDir
    $specRoot = Join-Path $targetDir ".agents/bundles/specs/$FlowId"
    $localAgents = Join-Path $targetDir ".agents"
    if ((-not (Test-Path -LiteralPath (Join-Path $specRoot "spec.md") -PathType Leaf)) -and (-not (Test-Path -LiteralPath $localAgents -PathType Container))) {
        if ((Test-Path -LiteralPath (Join-Path $targetDir ".git") -PathType Leaf) -and (Get-Command git -ErrorAction SilentlyContinue)) {
            try {
                $gcom = (& git -C $targetDir rev-parse --path-format=absolute --git-common-dir 2>$null | Select-Object -First 1)
                if (-not [string]::IsNullOrWhiteSpace($gcom)) {
                    $cmain = Split-Path -Parent $gcom.Trim()
                    $candRoot = Join-Path $cmain ".agents/bundles/specs/$FlowId"
                    if (Test-Path -LiteralPath (Join-Path $candRoot "spec.md") -PathType Leaf) {
                        $specRoot = $candRoot
                    }
                }
            } catch {}
        }
    }
    $rootSpec = Join-Path $specRoot "spec.md"
    if (-not (Test-Path -LiteralPath $rootSpec -PathType Leaf)) { return $false }
    $lines = @(Get-Content -LiteralPath $rootSpec -Encoding UTF8)
    $st = ""
    $lrc = ""
    if ($lines.Count -gt 0 -and $lines[0].Trim() -eq "---") {
        for ($idx = 1; $idx -lt $lines.Count; $idx++) {
            $ln = $lines[$idx]
            if ($ln.Trim() -eq "---") { break }
            if ($ln -match '^state:\s*(.+)$') { $st = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
            if ($ln -match '^last_reviewed_commit:\s*(.+)$') { $lrc = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
        }
    }
    if ($st -ne "completed" -or [string]::IsNullOrEmpty($lrc) -or $lrc -eq "null") { return $true }
    $chDirRoot = Join-Path $specRoot "chapters"
    if (Test-Path -LiteralPath $chDirRoot -PathType Container) {
        $chDirs = Get-ChildItem -LiteralPath $chDirRoot -Filter "ch*" -Directory -ErrorAction SilentlyContinue
        foreach ($cd in $chDirs) {
            $cs = Join-Path $cd.FullName "spec.md"
            if (-not (Test-Path -LiteralPath $cs -PathType Leaf)) { return $true }
            $cLines = @(Get-Content -LiteralPath $cs -Encoding UTF8)
            $cst = ""
            if ($cLines.Count -gt 0 -and $cLines[0].Trim() -eq "---") {
                for ($ci = 1; $ci -lt $cLines.Count; $ci++) {
                    if ($cLines[$ci].Trim() -eq "---") { break }
                    if ($cLines[$ci] -match '^state:\s*(.+)$') { $cst = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
                }
            }
            if ($cst -notin @("completed", "deferred", "skipped")) { return $true }
        }
    }
    $taskCandidates = @()
    $flatTasks = Join-Path $specRoot "tasks"
    if (Test-Path -LiteralPath $flatTasks -PathType Container) {
        $taskCandidates += @(Get-ChildItem -LiteralPath $flatTasks -Filter "*.md" -File -ErrorAction SilentlyContinue)
    }
    if (Test-Path -LiteralPath $chDirRoot -PathType Container) {
        foreach ($cd in (Get-ChildItem -LiteralPath $chDirRoot -Filter "ch*" -Directory -ErrorAction SilentlyContinue)) {
            $ct = Join-Path $cd.FullName "tasks"
            if (Test-Path -LiteralPath $ct -PathType Container) {
                $taskCandidates += @(Get-ChildItem -LiteralPath $ct -Filter "*.md" -File -ErrorAction SilentlyContinue)
            }
        }
    }
    foreach ($tf in $taskCandidates) {
        if ($tf.Name -eq "index.md") { continue }
        $tLines = @(Get-Content -LiteralPath $tf.FullName -Encoding UTF8)
        $tst = ""
        if ($tLines.Count -gt 0 -and $tLines[0].Trim() -eq "---") {
            for ($ti = 1; $ti -lt $tLines.Count; $ti++) {
                if ($tLines[$ti].Trim() -eq "---") { break }
                if ($tLines[$ti] -match '^state:\s*(.+)$') { $tst = ($Matches[1] -replace '\s+#.*$', '').Trim().Trim('"').Trim("'") }
            }
        }
        if ($tst -notin @("completed", "closed", "deferred", "skipped")) { return $true }
    }
    return $false
}

$Decision = "allow"
$Reason = ""

$ReadOnlyAgents = @("code-reviewer", "quality-reviewer", "researcher")
$ShortAgent = ($AgentId -split ':')[-1]
$MutatingTools = @("write_file", "write_to_file", "edit_file", "replace_file_content", "multi_replace_file_content", "delete_file", "notebook_edit", "Write", "Edit", "MultiEdit", "NotebookEdit")

if ($ShortAgent -in $ReadOnlyAgents -and $ToolName -in $MutatingTools) {
    $Decision = "deny"
    $Reason = "Flow safety guard: read-only agent '$AgentId' is forbidden from mutating repository files."
}

function Combine-GuardPath([string]$Base, [string]$SubPath) {
    $p = if ($null -eq $SubPath) { "" } else { ($SubPath -replace '\\', '/').Trim() }
    while ($p.Length -gt 1 -and ($p -notmatch '^[A-Za-z]:/$') -and $p.EndsWith('/')) {
        $p = $p.Substring(0, $p.Length - 1)
    }
    if ([string]::IsNullOrEmpty($p) -or $p -eq ".") { return $Base }
    if ($p.StartsWith('/') -or ($p -match '^[A-Za-z]:(?:/|$)') -or $p.StartsWith('~') -or [string]::IsNullOrEmpty($Base)) {
        return $p
    }
    $b = ($Base -replace '\\', '/').Trim()
    while ($b.Length -gt 1 -and ($b -notmatch '^[A-Za-z]:/$') -and $b.EndsWith('/')) {
        $b = $b.Substring(0, $b.Length - 1)
    }
    if ($b -eq "/" -or ($b -match '^[A-Za-z]:/$')) { return "$b$p" }
    return "$b/$p"
}

function Split-CommandSegments([string]$Cmd) {
    $segs = [System.Collections.Generic.List[string]]::new()
    $inSq = $false
    $inDq = $false
    $parenDepth = 0
    $sb = [System.Text.StringBuilder]::new()
    for ($i = 0; $i -lt $Cmd.Length; $i++) {
        $ch = $Cmd[$i]
        if ($ch -eq "'" -and -not $inDq) {
            $inSq = -not $inSq
            [void]$sb.Append($ch)
            continue
        }
        if ($ch -eq '"' -and -not $inSq) {
            if ($i -gt 0 -and $Cmd[$i - 1] -eq '\') {
                [void]$sb.Append($ch)
                continue
            }
            $inDq = -not $inDq
            [void]$sb.Append($ch)
            continue
        }
        if (-not $inSq -and -not $inDq) {
            if ($ch -eq '(' -and [string]::IsNullOrWhiteSpace($sb.ToString())) {
                $parenDepth++
                continue
            }
            if ($ch -eq ')' -and $parenDepth -gt 0) {
                $tail = $Cmd.Substring($i + 1)
                if ($tail -match '^[ \t\r]*(?:[;&|\n)]|$)') {
                    $parenDepth--
                    continue
                }
            }
            if ($ch -eq '&' -and $i -gt 0 -and $Cmd[$i - 1] -eq '>') {
                [void]$sb.Append($ch)
                continue
            }
            if ($ch -eq ';' -or $ch -eq '|' -or $ch -eq '&' -or $ch -eq "`n") {
                $trimmed = $sb.ToString().Trim()
                if ($trimmed.Length -gt 0) { $segs.Add($trimmed) }
                [void]$sb.Clear()
                continue
            }
        }
        [void]$sb.Append($ch)
    }
    $last = $sb.ToString().Trim()
    if ($last.Length -gt 0) { $segs.Add($last) }
    return ,$segs.ToArray()
}

function Split-SegmentTokens([string]$Seg) {
    $toks = [System.Collections.Generic.List[string]]::new()
    $inSq = $false
    $inDq = $false
    $hasTok = $false
    $sb = [System.Text.StringBuilder]::new()
    for ($i = 0; $i -lt $Seg.Length; $i++) {
        $ch = $Seg[$i]
        if ($inSq) {
            if ($ch -eq "'") { $inSq = $false } else { [void]$sb.Append($ch) }
            continue
        }
        if ($inDq) {
            if ($ch -eq '"') {
                $inDq = $false
            } elseif ($ch -eq '\' -and $i + 1 -lt $Seg.Length -and ($Seg[$i + 1] -eq '"' -or $Seg[$i + 1] -eq '\')) {
                [void]$sb.Append($Seg[$i + 1])
                $i++
            } else {
                [void]$sb.Append($ch)
            }
            continue
        }
        if ($ch -eq ' ' -or $ch -eq "`t" -or $ch -eq "`r" -or $ch -eq "`n") {
            if ($hasTok) {
                $toks.Add($sb.ToString())
                [void]$sb.Clear()
                $hasTok = $false
            }
            continue
        }
        if ($ch -eq "'") { $inSq = $true; $hasTok = $true; continue }
        if ($ch -eq '"') { $inDq = $true; $hasTok = $true; continue }
        if ($ch -eq '\' -and $i + 1 -lt $Seg.Length -and ($Seg[$i + 1] -in @(' ', "`t", '"', "'"))) {
            [void]$sb.Append($Seg[$i + 1])
            $hasTok = $true
            $i++
            continue
        }
        [void]$sb.Append($ch)
        $hasTok = $true
    }
    if ($hasTok) { $toks.Add($sb.ToString()) }
    return ,$toks.ToArray()
}

function Expand-GuardPath([string]$RawToken, [bool]$IsPsDelete) {
    $out = [System.Collections.Generic.List[string]]::new()
    $q = [System.Collections.Generic.Queue[string]]::new()
    $q.Enqueue(($RawToken -replace '\\', '/'))
    $seenCount = 1
    while ($q.Count -gt 0) {
        $cur = $q.Dequeue()
        $m = [regex]::Match($cur, '\{([^{}]*,[^{}]*)\}')
        if ($m.Success -and $seenCount -lt 64) {
            $pre = $cur.Substring(0, $m.Index)
            $post = $cur.Substring($m.Index + $m.Length)
            foreach ($opt in ($m.Groups[1].Value -split ',')) {
                if ($seenCount -ge 64) { break }
                $q.Enqueue("$pre$opt$post")
                $seenCount++
            }
        } elseif ($IsPsDelete -and $cur.Contains(',')) {
            foreach ($part in ($cur -split ',')) {
                if (-not [string]::IsNullOrEmpty($part)) { $out.Add($part) }
            }
        } else {
            $out.Add($cur)
        }
    }
    return ,$out.ToArray()
}

if ($Decision -eq "allow" -and $ToolName -eq "delete_file" -and -not [string]::IsNullOrWhiteSpace($TargetPath)) {
    $normDel = $TargetPath -replace '\\', '/'
    $mDel = [regex]::Match($normDel, '^(?:([A-Za-z]:/)|(.+?)/|(/))?\.agents/bundles/specs/([A-Za-z0-9_-]+)(?:/spec\.md|/)?$')
    if ($mDel.Success) {
        $delPrefix = if ($mDel.Groups[1].Success) { $mDel.Groups[1].Value } elseif ($mDel.Groups[3].Success) { "/" } elseif ($mDel.Groups[2].Success) { $mDel.Groups[2].Value } else { "" }
        $delFid = $mDel.Groups[4].Value
        if (Test-IncompleteFlowSpec $delFid $delPrefix) {
            $Decision = "deny"
            $Reason = "Flow safety guard: cannot delete or archive specs/$delFid while chapters or tasks remain incomplete or unreviewed."
        }
    }
}

if ($Decision -eq "allow" -and -not [string]::IsNullOrWhiteSpace($CmdLine) -and ($CmdLine -like "*specs*")) {
    $workQueue = [System.Collections.Generic.Queue[object]]::new()
    $workQueue.Enqueue(@{ Cmd = $CmdLine; Dir = "" })
    $workCount = 1
    while ($workQueue.Count -gt 0 -and $Decision -eq "allow") {
        $item = $workQueue.Dequeue()
        $curDir = [string]$item.Dir
        foreach ($seg in (Split-CommandSegments ([string]$item.Cmd))) {
            if ($Decision -ne "allow") { break }
            $toks = @(Split-SegmentTokens $seg)
            if ($toks.Count -eq 0) { continue }
            $cmdIdx = 0
            while ($cmdIdx -lt $toks.Count) {
                $tc = $toks[$cmdIdx]
                if ($tc -match '^[A-Za-z_][A-Za-z0-9_]*=.*$' -or $tc -in @("command", "env", "sudo")) {
                    $cmdIdx++
                    continue
                }
                break
            }
            if ($cmdIdx -ge $toks.Count) { continue }
            $cmdBase = ($toks[$cmdIdx] -replace '\\', '/').Split('/')[-1].ToLowerInvariant()

            if ($cmdBase -in @("sh", "bash", "zsh", "dash", "ksh", "pwsh", "powershell")) {
                for ($ki = $cmdIdx + 1; $ki -lt $toks.Count - 1; $ki++) {
                    if ($toks[$ki].ToLowerInvariant() -in @("-c", "-command", "-lc") -and $workCount -lt 16) {
                        $workQueue.Enqueue(@{ Cmd = $toks[$ki + 1]; Dir = $curDir })
                        $workCount++
                        break
                    }
                }
                continue
            }

            if ($cmdBase -in @("cd", "pushd", "set-location", "sl")) {
                $isSl = ($cmdBase -in @("set-location", "sl"))
                for ($ki = $cmdIdx + 1; $ki -lt $toks.Count; $ki++) {
                    $kt = $toks[$ki]
                    $klc = $kt.ToLowerInvariant()
                    if ($kt -eq "--" -and $ki + 1 -lt $toks.Count) {
                        $curDir = Combine-GuardPath $curDir $toks[$ki + 1]
                        break
                    }
                    if ($isSl -and $klc -eq "-stackname") { $ki++; continue }
                    if ($isSl -and $klc -match '^-path=(.+)$') { $curDir = Combine-GuardPath $curDir $kt.Substring(6); break }
                    if ($isSl -and $klc -match '^-literalpath=(.+)$') { $curDir = Combine-GuardPath $curDir $kt.Substring(13); break }
                    if ($kt.StartsWith('-')) { continue }
                    $curDir = Combine-GuardPath $curDir $kt
                    break
                }
                continue
            }

            $isDel = $false
            $isPsDel = $false
            $argStart = $cmdIdx + 1
            $segDir = $curDir
            if ($cmdBase -in @("rm", "rmdir")) {
                $isDel = $true
            } elseif ($cmdBase -in @("remove-item", "ri", "del", "rd")) {
                $isDel = $true
                $isPsDel = $true
            } elseif ($cmdBase -eq "git") {
                for ($ki = $cmdIdx + 1; $ki -lt $toks.Count; $ki++) {
                    $gt = $toks[$ki]
                    if ($gt -eq "-C" -and $ki + 1 -lt $toks.Count) {
                        $segDir = Combine-GuardPath $segDir $toks[$ki + 1]
                        $ki++
                    } elseif ($gt -match '^-C(.+)$') {
                        $segDir = Combine-GuardPath $segDir $gt.Substring(2)
                    } elseif ($gt -eq "--work-tree" -and $ki + 1 -lt $toks.Count) {
                        $segDir = Combine-GuardPath $segDir $toks[$ki + 1]
                        $ki++
                    } elseif ($gt -match '^--work-tree=(.+)$') {
                        $segDir = Combine-GuardPath $segDir $gt.Substring(12)
                    } elseif ($gt -in @("-c", "--git-dir", "--namespace", "--super-prefix", "--config-env")) {
                        $ki++
                    } elseif ($gt.StartsWith('-')) {
                        continue
                    } else {
                        if ($gt.ToLowerInvariant() -eq "rm") {
                            $isDel = $true
                            $argStart = $ki + 1
                        }
                        break
                    }
                }
            }

            if (-not $isDel) { continue }
            for ($ai = $argStart; $ai -lt $toks.Count; $ai++) {
                $at = $toks[$ai]
                if ($isPsDel) {
                    $alc = $at.ToLowerInvariant()
                    if ($alc -match '^-path=.+$') { $at = $at.Substring(6) }
                    elseif ($alc -match '^-literalpath=.+$') { $at = $at.Substring(13) }
                }
                if ($at.StartsWith('-')) { continue }
                foreach ($cand in (Expand-GuardPath $at $isPsDel)) {
                    $mc = [regex]::Match($cand, '^(?:([A-Za-z]:/)|(.+?)/|(/))?\.agents/bundles/specs/([A-Za-z0-9_-]+)(?:/spec\.md|/)?$')
                    if ($mc.Success) {
                        $tokPrefix = if ($mc.Groups[1].Success) { $mc.Groups[1].Value } elseif ($mc.Groups[3].Success) { "/" } elseif ($mc.Groups[2].Success) { $mc.Groups[2].Value } else { "" }
                        $rmFid = $mc.Groups[4].Value
                        $targetRoot = if (-not [string]::IsNullOrEmpty($tokPrefix)) { Combine-GuardPath $segDir $tokPrefix } else { $segDir }
                        if (Test-IncompleteFlowSpec $rmFid $targetRoot) {
                            $Decision = "deny"
                            $Reason = "Flow safety guard: cannot delete or archive specs/$rmFid while chapters or tasks remain incomplete or unreviewed."
                            break
                        }
                    }
                }
                if ($Decision -ne "allow") { break }
            }
        }
    }
}

if ($Decision -eq "allow" -and -not [string]::IsNullOrWhiteSpace($CmdLine)) {
    if ($CmdLine -match '(^|[;&|\s])git\s+push(\s+[^;&|]*)?\s+--tags([\s;&|]|$)') {
        $Decision = "deny"
        $Reason = "Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+tag(\s+([^;&|]*))?([;&|]|$)') {
        $Tail = if ($Matches[3]) { $Matches[3].Trim() } else { "" }
        if ($Tail -ne "" -and $Tail -notmatch '^(-l|--list|--contains|--points-at|-v|--verify)(\s|$)') {
            $Decision = "deny"
            $Reason = "Flow safety guard: creating, deleting, or pushing Git tags is forbidden by Flow discipline."
        }
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+push(\s+[^;&|]*)?\s+(-f|--force|--force-with-lease)([\s;&|]|$)') {
        $Decision = "ask"
        $Reason = "Flow safety guard: destructive Git force-push requires explicit user confirmation."
    } elseif ($CmdLine -match '(^|[;&|\s])git\s+reset\s+--hard([\s;&|]|$)') {
        $Decision = "ask"
        $Reason = "Flow safety guard: destructive git reset --hard requires explicit user confirmation."
    }
}

$EscReason = $Reason.Replace('\', '\\').Replace('"', '\"').Replace("`r", "").Replace("`n", " ")

switch -Regex ($Harness) {
    '^(agy|antigravity)$' {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"decision`":`"deny`",`"reason`":`"$EscReason`"}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"decision`":`"force_ask`",`"reason`":`"$EscReason`"}")
        } else {
            [Console]::Out.WriteLine('{"decision":"allow"}')
        }
    }
    '^cursor$' {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"permission`":`"deny`",`"user_message`":`"$EscReason`"}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"permission`":`"ask`",`"user_message`":`"$EscReason`"}")
        } else {
            [Console]::Out.WriteLine('{"permission":"allow"}')
        }
    }
    default {
        if ($Decision -eq "deny") {
            [Console]::Out.WriteLine("{`"hookSpecificOutput`":{`"hookEventName`":`"PreToolUse`",`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"$EscReason`"}}")
        } elseif ($Decision -eq "ask") {
            [Console]::Out.WriteLine("{`"hookSpecificOutput`":{`"hookEventName`":`"PreToolUse`",`"permissionDecision`":`"ask`",`"permissionDecisionReason`":`"$EscReason`"}}")
        } else {
            [Console]::Out.WriteLine('{}')
        }
    }
}
