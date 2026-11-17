/**
 * Micro-slice compiler and deterministic Context-Pack builder.
 *
 * Replaces coarse fixed batch chunks with size-bounded (`<= 250` LOC, `<= 3` files,
 * `<= 4` disjoint parallel slices per wave) execution waves paired with pre-extracted
 * `< 4k`-token symbol/line windows and compact upstream delta receipts.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { isClosedState, readTextSafe, resolveConfinedPath } from "../core/fs-io.mjs";
import { SpecEngine, resolveTaskDependency } from "./spec-engine.mjs";

export const DEFAULT_MAX_SLICE_LOC = 250;
export const DEFAULT_MAX_SLICE_FILES = 3;
export const DEFAULT_MAX_WAVE_WORKERS = 4;
export const MAX_WORKERS_CAP = 12;
export const DEFAULT_MAX_TASKS_PER_SLICE = 4;
export const DEFAULT_WINDOW_LINES = 120;
export const DEFAULT_CONTEXT_PACK_CHARS = 14000;

const SYMBOL_DEF_RE = /(?:^|\s)(?:async\s+)?(?:def|class|function|export\s+(?:async\s+)?(?:function|class|const))\s+([A-Za-z_][A-Za-z0-9_]*)/;

/**
 * Extract bounded line windows and delta receipts deterministically (`0` LLM tokens).
 */
export class ContextPackBuilder {
  /**
   * @param {string} workspaceRoot
   * @param {{ windowLines?: number, maxChars?: number }} [options]
   */
  constructor(workspaceRoot, { windowLines = DEFAULT_WINDOW_LINES, maxChars = DEFAULT_CONTEXT_PACK_CHARS } = {}) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.windowLines = windowLines;
    this.maxChars = maxChars;
  }

  /**
   * Build a bounded Context Pack for one slice without reading whole files unnecessarily.
   *
   * @param {{
   *   flow_id: string,
   *   slice_id: string,
   *   title: string,
   *   files: string[],
   *   tests: string[],
   *   read_set: string[],
   *   symbol_refs?: string[],
   *   depends_on?: string[],
   *   verification_hint?: string | null,
   *   upstream_commits?: string[],
   * }} slice
   */
  build(slice) {
    const snippets = [];
    const seenKeys = new Set();
    let totalChars = 0;

    const addSnippet = (relPath, startLine, endLine, text, symbol = null) => {
      const key = `${relPath}:${startLine}-${endLine}`;
      if (seenKeys.has(key) || totalChars >= this.maxChars) return;
      seenKeys.add(key);
      const budgetLeft = this.maxChars - totalChars;
      const body = text.length > budgetLeft ? `${text.slice(0, Math.max(200, budgetLeft - 40))}\n// ... truncated` : text;
      totalChars += body.length;
      snippets.push({
        path: relPath,
        symbol,
        start_line: startLine,
        end_line: endLine,
        content: body,
      });
    };

    const targets = [...new Set([...(slice.read_set || []), ...(slice.files || []), ...(slice.tests || []), ...(slice.symbol_refs || [])])];
    for (const ref of targets) {
      if (totalChars >= this.maxChars) break;
      const [rawPathPart, symName] = String(ref).split("::");
      const lineMatch = rawPathPart.match(/^(.*?):(\d+)(?:-(\d+))?$/);
      const cleanRel = (lineMatch ? lineMatch[1] : rawPathPart).split("#")[0].trim().replace(/^\.\//, "");
      if (!cleanRel || /^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(cleanRel)) continue;

      let absFile;
      try {
        absFile = resolveConfinedPath(this.workspaceRoot, cleanRel);
      } catch {
        continue;
      }
      if (!fs.existsSync(absFile) || !fs.statSync(absFile).isFile()) continue;
      const raw = readTextSafe(absFile);
      if (raw === null) continue;
      const lines = raw.split("\n");

      let startIdx = 0;
      let endIdx = Math.min(lines.length, this.windowLines);
      if (lineMatch) {
        const s = Math.max(1, Number(lineMatch[2]) || 1);
        const e = Math.min(lines.length, Number(lineMatch[3]) || s + this.windowLines - 1);
        startIdx = s - 1;
        endIdx = Math.min(e, startIdx + this.windowLines);
      } else if (symName) {
        const cleanSym = symName.split(".")[0].trim();
        const foundIdx = lines.findIndex((l) => {
          const m = l.match(SYMBOL_DEF_RE);
          return (m && m[1] === cleanSym) || l.includes(cleanSym);
        });
        if (foundIdx >= 0) {
          startIdx = Math.max(0, foundIdx - 8);
          endIdx = Math.min(lines.length, startIdx + this.windowLines);
        }
      }

      const sliceText = lines
        .slice(startIdx, endIdx)
        .map((l, idx) => `${startIdx + idx + 1}: ${l}`)
        .join("\n");
      addSnippet(cleanRel, startIdx + 1, endIdx, sliceText, symName || null);
    }

    const upstreamDeltaReceipt = this.#buildUpstreamDelta(slice.upstream_commits || []);
    return {
      flow_id: slice.flow_id,
      slice_id: slice.slice_id,
      title: slice.title,
      files: slice.files || [],
      tests: slice.tests || [],
      verification_commands: slice.verification_commands || [],
      verification_hint: slice.verification_hint || null,
      upstream_delta_receipt: upstreamDeltaReceipt,
      snippets,
      approx_tokens: Math.ceil((totalChars + upstreamDeltaReceipt.join("\n").length) / 4),
    };
  }

  /**
   * Format up to 15 compact lines summarizing recent upstream task commits.
   *
   * @param {string[]} commits
   * @returns {string[]}
   */
  #buildUpstreamDelta(commits) {
    const out = [];
    for (const sha of (commits || []).slice(-3)) {
      if (!/^[0-9a-fA-F]{7,40}$/.test(String(sha || ""))) continue;
      try {
        const stat = execFileSync("git", ["-C", this.workspaceRoot, "show", "--stat", "--oneline", sha], {
          encoding: "utf8",
          timeout: 1500,
          stdio: ["ignore", "pipe", "ignore"],
        });
        for (const line of stat.trim().split("\n").slice(0, 5)) {
          out.push(line.trim());
          if (out.length >= 15) return out;
        }
      } catch {
        // Ignore unavailable commits in shallow clones.
      }
    }
    return out;
  }
}

/**
 * Compile ready chapter/spec tasks into disjoint size-bounded execution waves paired with Context Packs.
 */
export class SliceCompiler {
  /**
   * @param {string} workspaceRoot
   * @param {{ maxSliceLoc?: number, maxSliceFiles?: number, maxWaveWorkers?: number, maxTasksPerSlice?: number }} [options]
   */
  constructor(
    workspaceRoot,
    {
      maxSliceLoc = DEFAULT_MAX_SLICE_LOC,
      maxSliceFiles = DEFAULT_MAX_SLICE_FILES,
      maxWaveWorkers = DEFAULT_MAX_WAVE_WORKERS,
      maxTasksPerSlice = DEFAULT_MAX_TASKS_PER_SLICE,
    } = {},
  ) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.maxSliceLoc = Math.max(40, Number(maxSliceLoc) || DEFAULT_MAX_SLICE_LOC);
    this.maxSliceFiles = Math.max(1, Number(maxSliceFiles) || DEFAULT_MAX_SLICE_FILES);
    this.maxWaveWorkers = Math.max(1, Math.min(MAX_WORKERS_CAP, Number(maxWaveWorkers) || DEFAULT_MAX_WAVE_WORKERS));
    this.maxTasksPerSlice = Math.max(1, Number(maxTasksPerSlice) || DEFAULT_MAX_TASKS_PER_SLICE);
    this.engine = new SpecEngine(this.workspaceRoot);
    this.packBuilder = new ContextPackBuilder(this.workspaceRoot);
  }

  /**
   * Normalize a relative file/test path for disjointness comparison.
   *
   * @param {string} raw
   * @returns {string}
   */
  static #cleanPath(raw) {
    return String(raw || "")
      .split("::")[0]
      .trim()
      .replace(/^\.\//, "");
  }

  /**
   * Compile ready tasks for `flowId` into micro-slices and disjoint parallel waves.
   *
   * @param {{
   *   flowId: string,
   *   chapterId?: string | null,
   *   allReadyChapters?: boolean,
   *   includeContextPacks?: boolean,
   *   excludeTaskIds?: string[],
   *   excludePaths?: string[],
   * }} params
   */
  compile({
    flowId,
    chapterId = null,
    allReadyChapters = false,
    includeContextPacks = false,
    excludeTaskIds = [],
    excludePaths = [],
    maxWorkers = null,
    maxSliceLoc = null,
    maxSliceFiles = null,
  }) {
    const effectiveMaxLoc = maxSliceLoc ? Math.max(40, Number(maxSliceLoc) || this.maxSliceLoc) : this.maxSliceLoc;
    const effectiveMaxFiles = maxSliceFiles ? Math.max(1, Number(maxSliceFiles) || this.maxSliceFiles) : this.maxSliceFiles;
    const effectiveMaxWorkers = maxWorkers
      ? Math.max(1, Math.min(MAX_WORKERS_CAP, Number(maxWorkers) || this.maxWaveWorkers))
      : this.maxWaveWorkers;
    const { spec } = this.engine.status(flowId);
    const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
    const closedChapters = new Set(spec.chapters.filter((c) => isClosedState(c.state)).map((c) => c.chapter_id));

    let scopeChapters = [];
    let scopeTasks = spec.tasks;
    if (spec.has_chapters) {
      if (chapterId && !allReadyChapters) {
        const target = spec.chapters.find((c) => c.chapter_id === chapterId) || null;
        scopeChapters = target ? [target] : [];
        scopeTasks = target?.tasks || [];
      } else if (allReadyChapters) {
        scopeChapters = spec.chapters.filter(
          (c) =>
            !isClosedState(c.state) &&
            c.planning_status !== "empirical_dependent" &&
            c.depends_on_chapters.every((dep) => closedChapters.has(dep)),
        );
        scopeTasks = scopeChapters.flatMap((c) => c.tasks);
      } else {
        const targetId =
          chapterId || spec.current_chapter || spec.chapters.find((x) => !isClosedState(x.state))?.chapter_id;
        const target = spec.chapters.find((c) => c.chapter_id === targetId) || null;
        scopeChapters = target ? [target] : [];
        scopeTasks = target?.tasks || [];
      }
    }

    const excludedIds = new Set((excludeTaskIds || []).map((id) => String(id || "").trim()).filter(Boolean));
    const excludedPaths = new Set((excludePaths || []).map((p) => SliceCompiler.#cleanPath(p)).filter(Boolean));
    for (const t of scopeTasks) {
      if (t.state === "in_progress" && t.claimed_by) {
        for (const p of [...(t.files || []), ...(t.tests || []), ...(t.lock_scopes || [])]) {
          const clean = SliceCompiler.#cleanPath(p);
          if (clean) excludedPaths.add(clean);
        }
      }
    }

    const readyTasks = scopeTasks.filter(
      (t) =>
        !isClosedState(t.state) &&
        t.state !== "blocked" &&
        !(t.state === "in_progress" && t.claimed_by) &&
        !excludedIds.has(t.id) &&
        !excludedIds.has(t.short_id) &&
        !excludedIds.has(t.rel_path) &&
        t.depends_on.every((d) => {
          const dep = resolveTaskDependency(t, d, allTasks, spec.flow_id);
          return dep && isClosedState(dep.state);
        }),
    );

    const atomicSlices = [];
    for (const task of readyTasks) {
      atomicSlices.push(...this.#splitTaskIntoMicroSlices(spec.flow_id, task, allTasks, effectiveMaxLoc, effectiveMaxFiles));
    }

    const coalesced = this.#coalesceSmallSameFileSlices(atomicSlices, effectiveMaxLoc);
    const waves = this.#packWaves(coalesced, excludedPaths, {
      maxWaveWorkers: effectiveMaxWorkers,
      maxSliceLoc: effectiveMaxLoc,
      maxSliceFiles: effectiveMaxFiles,
    });

    if (includeContextPacks) {
      for (const wave of waves) {
        for (const slice of wave.slices) {
          slice.context_pack = this.packBuilder.build(slice);
        }
      }
    }

    const totalFiles = new Set(coalesced.flatMap((s) => [...s.files, ...s.tests])).size;
    const totalLoc = coalesced.reduce((sum, s) => sum + (s.estimated_loc || 0), 0);
    const chapterIds = Array.from(
      new Set(
        (spec.has_chapters ? scopeChapters.map((c) => c.chapter_id) : []).concat(
          coalesced.flatMap((s) => s.chapter_ids || (s.chapter_id ? [s.chapter_id] : [])),
        ),
      ),
    );
    const dispatchableSlices = waves.length > 0 && !waves[0].waits_for_inflight ? waves[0].slices : [];

    return {
      ok: true,
      flow_id: spec.flow_id,
      chapter_id: allReadyChapters ? chapterIds[0] || null : chapterId || scopeChapters[0]?.chapter_id || null,
      chapter_ids: chapterIds,
      all_ready_chapters: Boolean(allReadyChapters),
      ready_task_count: readyTasks.length,
      slice_count: coalesced.length,
      total_files: totalFiles,
      total_estimated_loc: totalLoc,
      inline_fast_path_eligible: totalFiles <= 5 && totalLoc <= 300,
      dispatchable_slices: dispatchableSlices,
      waves,
    };
  }

  #splitTaskIntoMicroSlices(flowId, task, allTasks, maxSliceLoc = this.maxSliceLoc, maxSliceFiles = this.maxSliceFiles) {
    const files = (task.files || []).map((f) => SliceCompiler.#cleanPath(f)).filter(Boolean);
    const tests = (task.tests || []).map((f) => SliceCompiler.#cleanPath(f)).filter(Boolean);
    const estLoc = Math.max(10, Number(task.estimated_loc) || files.length * 60 || 80);
    const upstreamCommits = task.depends_on
      .map((d) => resolveTaskDependency(task, d, allTasks, flowId)?.commit)
      .filter(Boolean);
    const verificationCommands = Array.from(new Set(task.verification_commands || []));
    const verificationHint = verificationCommands[0] || null;
    const chapterIds = task.chapter_id ? [task.chapter_id] : [];

    const needsSplit = files.length > maxSliceFiles || (estLoc > maxSliceLoc && files.length > 1);
    if (!needsSplit) {
      return [
        {
          slice_id: task.id,
          task_ids: [task.id],
          task_paths: [task.rel_path],
          flow_id: flowId,
          chapter_id: task.chapter_id,
          chapter_ids: chapterIds,
          title: task.title,
          files,
          tests,
          read_set: task.read_set || [],
          symbol_refs: task.symbol_refs || [],
          estimated_loc: estLoc,
          upstream_commits: upstreamCommits,
          verification_commands: verificationCommands,
          verification_hint: verificationHint,
        },
      ];
    }

    const chunks = [];
    for (let i = 0; i < files.length; i += maxSliceFiles) {
      chunks.push(files.slice(i, i + maxSliceFiles));
    }
    const locPerChunk = Math.max(20, Math.round(estLoc / Math.max(1, chunks.length)));
    return chunks.map((chunkFiles, idx) => ({
      slice_id: `${task.id}#s${idx + 1}`,
      task_ids: [task.id],
      task_paths: [task.rel_path],
      flow_id: flowId,
      chapter_id: task.chapter_id,
      chapter_ids: chapterIds,
      title: `${task.title} (part ${idx + 1}/${chunks.length})`,
      files: chunkFiles,
      tests: idx === 0 ? tests : [],
      read_set: [...chunkFiles, ...(task.read_set || []).slice(0, 2)],
      symbol_refs: task.symbol_refs || [],
      estimated_loc: locPerChunk,
      upstream_commits: upstreamCommits,
      verification_commands: idx === 0 ? verificationCommands : [],
      verification_hint: idx === 0 ? verificationHint : null,
    }));
  }

  #mergeSlicesInto(target, src) {
    target.task_ids = Array.from(new Set([...target.task_ids, ...src.task_ids]));
    target.task_paths = Array.from(new Set([...target.task_paths, ...src.task_paths]));
    target.chapter_ids = Array.from(
      new Set([...(target.chapter_ids || []), ...(src.chapter_ids || []), ...(src.chapter_id ? [src.chapter_id] : [])]),
    );
    target.files = Array.from(new Set([...target.files, ...src.files]));
    target.tests = Array.from(new Set([...target.tests, ...src.tests]));
    target.read_set = Array.from(new Set([...target.read_set, ...src.read_set]));
    target.symbol_refs = Array.from(new Set([...(target.symbol_refs || []), ...(src.symbol_refs || [])]));
    target.upstream_commits = Array.from(new Set([...(target.upstream_commits || []), ...(src.upstream_commits || [])]));
    target.verification_commands = Array.from(
      new Set([...(target.verification_commands || []), ...(src.verification_commands || [])]),
    );
    target.verification_hint = target.verification_commands[0] || target.verification_hint || null;
    target.estimated_loc += src.estimated_loc;
    target.title = `${target.title} + ${src.title}`;
  }

  #coalesceSmallSameFileSlices(slices, maxSliceLoc = this.maxSliceLoc) {
    const out = [];
    for (const slice of slices) {
      const target =
        slice.files.length === 1
          ? out.find(
              (cand) =>
                cand.files.length === 1 &&
                cand.files[0] === slice.files[0] &&
                (!cand.chapter_id || !slice.chapter_id || cand.chapter_id === slice.chapter_id) &&
                cand.task_ids.length + slice.task_ids.length <= this.maxTasksPerSlice &&
                cand.estimated_loc + slice.estimated_loc <= maxSliceLoc,
            )
          : null;
      if (target) {
        this.#mergeSlicesInto(target, slice);
      } else {
        out.push({ ...slice, chapter_ids: [...(slice.chapter_ids || (slice.chapter_id ? [slice.chapter_id] : []))] });
      }
    }
    return out;
  }

  #packWaves(
    slices,
    excludedPaths = new Set(),
    { maxWaveWorkers = this.maxWaveWorkers, maxSliceLoc = this.maxSliceLoc, maxSliceFiles = this.maxSliceFiles } = {},
  ) {
    const waves = [];
    const remaining = slices.map((s) => ({ ...s }));
    let activeExcludedPaths = new Set(excludedPaths);
    let carryWaitForInflight = false;

    while (remaining.length > 0) {
      const waveSlices = [];
      const usedOwnedPaths = new Set();
      const waitsForInflight = carryWaitForInflight;
      carryWaitForInflight = false;

      let idx = 0;
      while (idx < remaining.length && waveSlices.length < maxWaveWorkers) {
        const cand = remaining[idx];
        const owned = [...cand.files, ...cand.tests];
        const conflict = owned.some((p) => usedOwnedPaths.has(p) || activeExcludedPaths.has(p));
        if (conflict) {
          idx += 1;
          continue;
        }
        for (const p of owned) usedOwnedPaths.add(p);
        waveSlices.push(cand);
        remaining.splice(idx, 1);
      }

      if (waveSlices.length > 0 && remaining.length > 0) {
        let remIdx = 0;
        while (remIdx < remaining.length) {
          const cand = remaining[remIdx];
          const owned = [...cand.files, ...cand.tests];
          if (owned.some((p) => activeExcludedPaths.has(p))) {
            remIdx += 1;
            continue;
          }
          const eligibleTargets = waveSlices
            .filter((target) => {
              if (cand.chapter_id && target.chapter_id && cand.chapter_id !== target.chapter_id) return false;
              const mergedFiles = new Set([...target.files, ...cand.files]);
              const mergedTasks = target.task_ids.length + cand.task_ids.length;
              if (mergedFiles.size > maxSliceFiles) return false;
              if (mergedTasks > this.maxTasksPerSlice) return false;
              if (target.estimated_loc + cand.estimated_loc > maxSliceLoc) return false;
              return !waveSlices.some(
                (other) => other !== target && owned.some((p) => other.files.includes(p) || other.tests.includes(p)),
              );
            })
            .sort((a, b) => a.estimated_loc - b.estimated_loc || a.task_ids.length - b.task_ids.length);
          if (eligibleTargets.length > 0) {
            this.#mergeSlicesInto(eligibleTargets[0], cand);
            for (const p of owned) usedOwnedPaths.add(p);
            remaining.splice(remIdx, 1);
          } else {
            remIdx += 1;
          }
        }
      }

      if (waveSlices.length === 0 && remaining.length > 0) {
        if (activeExcludedPaths.size > 0) {
          carryWaitForInflight = true;
          activeExcludedPaths = new Set();
          continue;
        }
        waveSlices.push(remaining.shift());
      }

      const waveChapterIds = Array.from(new Set(waveSlices.flatMap((s) => s.chapter_ids || [])));
      waves.push({
        wave: waves.length + 1,
        parallel_count: waveSlices.length,
        chapter_ids: waveChapterIds,
        shared_test_files: [],
        waits_for_inflight: waitsForInflight,
        slices: waveSlices,
      });
      activeExcludedPaths = new Set();
    }
    return waves;
  }
}
