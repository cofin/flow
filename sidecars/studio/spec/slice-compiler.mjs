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
   * @param {{ maxSliceLoc?: number, maxSliceFiles?: number, maxWaveWorkers?: number }} [options]
   */
  constructor(
    workspaceRoot,
    {
      maxSliceLoc = DEFAULT_MAX_SLICE_LOC,
      maxSliceFiles = DEFAULT_MAX_SLICE_FILES,
      maxWaveWorkers = DEFAULT_MAX_WAVE_WORKERS,
    } = {},
  ) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.maxSliceLoc = maxSliceLoc;
    this.maxSliceFiles = maxSliceFiles;
    this.maxWaveWorkers = Math.max(1, Math.min(4, maxWaveWorkers));
    this.engine = new SpecEngine(this.workspaceRoot);
    this.packBuilder = new ContextPackBuilder(this.workspaceRoot);
  }

  /**
   * Compile ready tasks for `flowId` / `chapterId` into micro-slices and disjoint parallel waves.
   *
   * @param {{ flowId: string, chapterId?: string | null, includeContextPacks?: boolean }} params
   */
  compile({ flowId, chapterId = null, includeContextPacks = false }) {
    const { spec } = this.engine.status(flowId);
    const allTasks = spec.has_chapters ? spec.chapters.flatMap((c) => c.tasks) : spec.tasks;
    const scopeTasks = spec.has_chapters
      ? (spec.chapters.find((c) => c.chapter_id === (chapterId || spec.current_chapter || spec.chapters.find((x) => !isClosedState(x.state))?.chapter_id))?.tasks || [])
      : spec.tasks;

    const readyTasks = scopeTasks.filter(
      (t) =>
        !isClosedState(t.state) &&
        t.state !== "blocked" &&
        t.depends_on.every((d) => {
          const dep = resolveTaskDependency(t, d, allTasks, spec.flow_id);
          return dep && isClosedState(dep.state);
        }),
    );

    const atomicSlices = [];
    for (const task of readyTasks) {
      atomicSlices.push(...this.#splitTaskIntoMicroSlices(spec.flow_id, task, allTasks));
    }

    const coalesced = this.#coalesceSmallSameFileSlices(atomicSlices);
    const waves = this.#packWaves(coalesced);

    if (includeContextPacks) {
      for (const wave of waves) {
        for (const slice of wave.slices) {
          slice.context_pack = this.packBuilder.build(slice);
        }
      }
    }

    const totalFiles = new Set(coalesced.flatMap((s) => [...s.files, ...s.tests])).size;
    const totalLoc = coalesced.reduce((sum, s) => sum + (s.estimated_loc || 0), 0);

    return {
      ok: true,
      flow_id: spec.flow_id,
      chapter_id: chapterId || null,
      ready_task_count: readyTasks.length,
      slice_count: coalesced.length,
      total_files: totalFiles,
      total_estimated_loc: totalLoc,
      inline_fast_path_eligible: totalFiles <= 5 && totalLoc <= 300,
      waves,
    };
  }

  #splitTaskIntoMicroSlices(flowId, task, allTasks) {
    const files = (task.files || []).map((f) => String(f).split("::")[0].trim().replace(/^\.\//, "")).filter(Boolean);
    const tests = (task.tests || []).map((f) => String(f).split("::")[0].trim().replace(/^\.\//, "")).filter(Boolean);
    const estLoc = Math.max(10, Number(task.estimated_loc) || files.length * 60 || 80);
    const upstreamCommits = task.depends_on
      .map((d) => resolveTaskDependency(task, d, allTasks, flowId)?.commit)
      .filter(Boolean);

    const needsSplit = files.length > this.maxSliceFiles || (estLoc > this.maxSliceLoc && files.length > 1);
    if (!needsSplit) {
      return [
        {
          slice_id: task.id,
          task_ids: [task.id],
          task_paths: [task.rel_path],
          flow_id: flowId,
          chapter_id: task.chapter_id,
          title: task.title,
          files,
          tests,
          read_set: task.read_set || [],
          symbol_refs: task.symbol_refs || [],
          estimated_loc: estLoc,
          upstream_commits: upstreamCommits,
        },
      ];
    }

    const chunks = [];
    for (let i = 0; i < files.length; i += this.maxSliceFiles) {
      chunks.push(files.slice(i, i + this.maxSliceFiles));
    }
    const locPerChunk = Math.max(20, Math.round(estLoc / Math.max(1, chunks.length)));
    return chunks.map((chunkFiles, idx) => ({
      slice_id: `${task.id}#s${idx + 1}`,
      task_ids: [task.id],
      task_paths: [task.rel_path],
      flow_id: flowId,
      chapter_id: task.chapter_id,
      title: `${task.title} (part ${idx + 1}/${chunks.length})`,
      files: chunkFiles,
      tests: idx === 0 ? tests : [],
      read_set: [...chunkFiles, ...(task.read_set || []).slice(0, 2)],
      symbol_refs: task.symbol_refs || [],
      estimated_loc: locPerChunk,
      upstream_commits: upstreamCommits,
    }));
  }

  #coalesceSmallSameFileSlices(slices) {
    const out = [];
    for (const slice of slices) {
      const prev = out[out.length - 1];
      const sameOwnerFile =
        prev &&
        slice.files.length === 1 &&
        prev.files.length === 1 &&
        prev.files[0] === slice.files[0] &&
        prev.estimated_loc + slice.estimated_loc <= this.maxSliceLoc;
      if (sameOwnerFile) {
        prev.task_ids = Array.from(new Set([...prev.task_ids, ...slice.task_ids]));
        prev.task_paths = Array.from(new Set([...prev.task_paths, ...slice.task_paths]));
        prev.tests = Array.from(new Set([...prev.tests, ...slice.tests]));
        prev.read_set = Array.from(new Set([...prev.read_set, ...slice.read_set]));
        prev.estimated_loc += slice.estimated_loc;
        prev.title = `${prev.title} + ${slice.title}`;
      } else {
        out.push({ ...slice });
      }
    }
    return out;
  }

  #packWaves(slices) {
    const waves = [];
    const remaining = [...slices];
    while (remaining.length > 0) {
      const waveSlices = [];
      const usedWritePaths = new Set();
      const testOwners = new Map();
      const sharedTestFiles = [];

      let idx = 0;
      while (idx < remaining.length && waveSlices.length < this.maxWaveWorkers) {
        const cand = remaining[idx];
        const conflict = cand.files.some((f) => usedWritePaths.has(f));
        if (conflict) {
          idx += 1;
          continue;
        }
        for (const f of cand.files) usedWritePaths.add(f);
        for (const t of cand.tests) {
          if (testOwners.has(t) && !sharedTestFiles.includes(t)) sharedTestFiles.push(t);
          else testOwners.set(t, cand.slice_id);
        }
        waveSlices.push(cand);
        remaining.splice(idx, 1);
      }

      if (waveSlices.length === 0 && remaining.length > 0) {
        waveSlices.push(remaining.shift());
      }
      waves.push({
        wave: waves.length + 1,
        parallel_count: waveSlices.length,
        shared_test_files: sharedTestFiles,
        slices: waveSlices,
      });
    }
    return waves;
  }
}
