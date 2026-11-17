/**
 * Task planner and brief builder for parallel Flow execution.
 *
 * Groups ready tasks into steps on separate files (up to 4 workers by default,
 * capped at 12) and builds short file-excerpt briefs so workers can start
 * editing without broad repository searches.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { isClosedState, readTextSafe, resolveConfinedPath } from "../core/fs-io.mjs";
import { SpecEngine, resolveTaskDependency } from "./spec-engine.mjs";

export const DEFAULT_MAX_TASK_LOC = 250;
export const DEFAULT_MAX_TASK_FILES = 3;
export const DEFAULT_MAX_WORKERS = 4;
export const MAX_WORKERS_CAP = 12;
export const DEFAULT_MAX_TASKS_PER_WORKER = 4;
export const DEFAULT_WINDOW_LINES = 120;
export const DEFAULT_BRIEF_CHARS = 14000;

const SYMBOL_DEF_RE = /(?:^|\s)(?:async\s+)?(?:def|class|function|export\s+(?:async\s+)?(?:function|class|const))\s+([A-Za-z_][A-Za-z0-9_]*)/;

/**
 * Extract line windows and recent upstream commit summaries for a task group.
 */
export class TaskBriefBuilder {
  /**
   * @param {string} workspaceRoot
   * @param {{ windowLines?: number, maxChars?: number }} [options]
   */
  constructor(workspaceRoot, { windowLines = DEFAULT_WINDOW_LINES, maxChars = DEFAULT_BRIEF_CHARS } = {}) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.windowLines = windowLines;
    this.maxChars = maxChars;
  }

  /**
   * Build a brief for one task group without reading whole files unnecessarily.
   *
   * @param {{
   *   flow_id: string,
   *   group_id: string,
   *   title: string,
   *   files: string[],
   *   tests: string[],
   *   read_set: string[],
   *   symbol_refs?: string[],
   *   depends_on?: string[],
   *   verification_commands?: string[],
   *   verification_hint?: string | null,
   *   upstream_commits?: string[],
   * }} taskGroup
   */
  build(taskGroup) {
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

    const targets = [
      ...new Set([
        ...(taskGroup.read_set || []),
        ...(taskGroup.files || []),
        ...(taskGroup.tests || []),
        ...(taskGroup.symbol_refs || []),
      ]),
    ];
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

      const excerptText = lines
        .slice(startIdx, endIdx)
        .map((l, idx) => `${startIdx + idx + 1}: ${l}`)
        .join("\n");
      addSnippet(cleanRel, startIdx + 1, endIdx, excerptText, symName || null);
    }

    const upstreamChanges = this.#buildUpstreamChanges(taskGroup.upstream_commits || []);
    return {
      flow_id: taskGroup.flow_id,
      group_id: taskGroup.group_id,
      title: taskGroup.title,
      files: taskGroup.files || [],
      tests: taskGroup.tests || [],
      verification_commands: taskGroup.verification_commands || [],
      verification_hint: taskGroup.verification_hint || null,
      upstream_changes: upstreamChanges,
      snippets,
      approx_tokens: Math.ceil((totalChars + upstreamChanges.join("\n").length) / 4),
    };
  }

  /**
   * Format up to 15 compact lines summarizing recent upstream task commits.
   *
   * @param {string[]} commits
   * @returns {string[]}
   */
  #buildUpstreamChanges(commits) {
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
 * Plan ready chapter or spec tasks into parallel steps on separate files with optional briefs.
 */
export class TaskPlanner {
  /**
   * @param {string} workspaceRoot
   * @param {{ maxTaskLoc?: number, maxTaskFiles?: number, workers?: number, maxTasksPerWorker?: number }} [options]
   */
  constructor(
    workspaceRoot,
    {
      maxTaskLoc = DEFAULT_MAX_TASK_LOC,
      maxTaskFiles = DEFAULT_MAX_TASK_FILES,
      workers = DEFAULT_MAX_WORKERS,
      maxTasksPerWorker = DEFAULT_MAX_TASKS_PER_WORKER,
    } = {},
  ) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.maxTaskLoc = Math.max(40, Number(maxTaskLoc) || DEFAULT_MAX_TASK_LOC);
    this.maxTaskFiles = Math.max(1, Number(maxTaskFiles) || DEFAULT_MAX_TASK_FILES);
    this.workers = Math.max(1, Math.min(MAX_WORKERS_CAP, Number(workers) || DEFAULT_MAX_WORKERS));
    this.maxTasksPerWorker = Math.max(1, Number(maxTasksPerWorker) || DEFAULT_MAX_TASKS_PER_WORKER);
    this.engine = new SpecEngine(this.workspaceRoot);
    this.briefBuilder = new TaskBriefBuilder(this.workspaceRoot);
  }

  /**
   * Normalize a relative file or test path for file-conflict checks.
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
   * Plan ready tasks for `flowId` into parallel steps on separate files.
   *
   * @param {{
   *   flowId: string,
   *   chapterId?: string | null,
   *   allReadyChapters?: boolean,
   *   includeBriefs?: boolean,
   *   excludeTaskIds?: string[],
   *   excludePaths?: string[],
   *   workers?: number | null,
   *   maxTaskLoc?: number | null,
   *   maxTaskFiles?: number | null,
   * }} params
   */
  plan({
    flowId,
    chapterId = null,
    allReadyChapters = false,
    includeBriefs = false,
    excludeTaskIds = [],
    excludePaths = [],
    workers = null,
    maxTaskLoc = null,
    maxTaskFiles = null,
  }) {
    const effectiveMaxLoc = maxTaskLoc ? Math.max(40, Number(maxTaskLoc) || this.maxTaskLoc) : this.maxTaskLoc;
    const effectiveMaxFiles = maxTaskFiles ? Math.max(1, Number(maxTaskFiles) || this.maxTaskFiles) : this.maxTaskFiles;
    const effectiveWorkers = workers
      ? Math.max(1, Math.min(MAX_WORKERS_CAP, Number(workers) || this.workers))
      : this.workers;
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
    const excludedPaths = new Set((excludePaths || []).map((p) => TaskPlanner.#cleanPath(p)).filter(Boolean));
    for (const t of scopeTasks) {
      if (t.state === "in_progress" && t.claimed_by) {
        for (const p of [...(t.files || []), ...(t.tests || []), ...(t.lock_scopes || [])]) {
          const clean = TaskPlanner.#cleanPath(p);
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

    const atomicGroups = readyTasks.map((task) => this.#toTaskGroup(spec.flow_id, task, allTasks));

    const grouped = this.#groupSameFileTasks(atomicGroups, effectiveMaxLoc);
    const steps = this.#planSteps(grouped, excludedPaths, {
      workers: effectiveWorkers,
      maxTaskLoc: effectiveMaxLoc,
      maxTaskFiles: effectiveMaxFiles,
    });

    if (includeBriefs) {
      for (const step of steps) {
        for (const group of step.tasks) {
          group.brief = this.briefBuilder.build(group);
        }
      }
    }

    const totalFiles = new Set(grouped.flatMap((g) => [...g.files, ...g.tests])).size;
    const totalLoc = grouped.reduce((sum, g) => sum + (g.estimated_loc || 0), 0);
    const chapterIds = Array.from(
      new Set(
        (spec.has_chapters ? scopeChapters.map((c) => c.chapter_id) : []).concat(
          grouped.flatMap((g) => g.chapter_ids || (g.chapter_id ? [g.chapter_id] : [])),
        ),
      ),
    );
    const readyNow = steps.length > 0 && !steps[0].waits_for_inflight ? steps[0].tasks : [];

    return {
      ok: true,
      flow_id: spec.flow_id,
      chapter_id: allReadyChapters ? chapterIds[0] || null : chapterId || scopeChapters[0]?.chapter_id || null,
      chapter_ids: chapterIds,
      all_ready_chapters: Boolean(allReadyChapters),
      ready_task_count: readyTasks.length,
      group_count: grouped.length,
      total_files: totalFiles,
      total_estimated_loc: totalLoc,
      inline_fast_path_eligible: totalFiles <= 5 && totalLoc <= 300,
      ready_tasks: readyNow,
      steps,
    };
  }

  #toTaskGroup(flowId, task, allTasks) {
    const files = (task.files || []).map((f) => TaskPlanner.#cleanPath(f)).filter(Boolean);
    const tests = (task.tests || []).map((f) => TaskPlanner.#cleanPath(f)).filter(Boolean);
    const lockScopes = (task.lock_scopes || []).map((f) => TaskPlanner.#cleanPath(f)).filter(Boolean);
    const estLoc = Math.max(10, Number(task.estimated_loc) || files.length * 60 || 80);
    const upstreamCommits = task.depends_on
      .map((d) => resolveTaskDependency(task, d, allTasks, flowId)?.commit)
      .filter(Boolean);
    const verificationCommands = Array.from(new Set(task.verification_commands || []));
    const verificationHint = verificationCommands[0] || null;
    const chapterIds = task.chapter_id ? [task.chapter_id] : [];

    return {
      group_id: task.id,
      task_id: task.id,
      task_ids: [task.id],
      task_paths: [task.rel_path],
      flow_id: flowId,
      chapter_id: task.chapter_id,
      chapter_ids: chapterIds,
      title: task.title,
      files,
      tests,
      lock_scopes: lockScopes,
      read_set: task.read_set || [],
      symbol_refs: task.symbol_refs || [],
      estimated_loc: estLoc,
      upstream_commits: upstreamCommits,
      verification_commands: verificationCommands,
      verification_hint: verificationHint,
    };
  }

  #mergeGroupsInto(target, src) {
    target.task_ids = Array.from(new Set([...target.task_ids, ...src.task_ids]));
    target.task_paths = Array.from(new Set([...target.task_paths, ...src.task_paths]));
    target.chapter_ids = Array.from(
      new Set([...(target.chapter_ids || []), ...(src.chapter_ids || []), ...(src.chapter_id ? [src.chapter_id] : [])]),
    );
    target.files = Array.from(new Set([...target.files, ...src.files]));
    target.tests = Array.from(new Set([...target.tests, ...src.tests]));
    target.lock_scopes = Array.from(new Set([...(target.lock_scopes || []), ...(src.lock_scopes || [])]));
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

  #groupSameFileTasks(groups, maxTaskLoc = this.maxTaskLoc) {
    const out = [];
    for (const group of groups) {
      const target =
        group.files.length === 1
          ? out.find(
              (cand) =>
                cand.files.length === 1 &&
                cand.files[0] === group.files[0] &&
                (!cand.chapter_id || !group.chapter_id || cand.chapter_id === group.chapter_id) &&
                cand.task_ids.length + group.task_ids.length <= this.maxTasksPerWorker &&
                cand.estimated_loc + group.estimated_loc <= maxTaskLoc,
            )
          : null;
      if (target) {
        this.#mergeGroupsInto(target, group);
      } else {
        out.push({ ...group, chapter_ids: [...(group.chapter_ids || (group.chapter_id ? [group.chapter_id] : []))] });
      }
    }
    return out;
  }

  #planSteps(
    groups,
    excludedPaths = new Set(),
    { workers = this.workers, maxTaskLoc = this.maxTaskLoc, maxTaskFiles = this.maxTaskFiles } = {},
  ) {
    const steps = [];
    const remaining = groups.map((g) => ({ ...g }));
    let activeExcludedPaths = new Set(excludedPaths);
    let carryWaitForInflight = false;

    while (remaining.length > 0) {
      const stepTasks = [];
      const usedOwnedPaths = new Set();
      const waitsForInflight = carryWaitForInflight;
      carryWaitForInflight = false;

      let idx = 0;
      while (idx < remaining.length && stepTasks.length < workers) {
        const cand = remaining[idx];
        const owned = [...cand.files, ...cand.tests, ...(cand.lock_scopes || [])];
        const conflict = owned.some((p) => usedOwnedPaths.has(p) || activeExcludedPaths.has(p));
        if (conflict) {
          idx += 1;
          continue;
        }
        for (const p of owned) usedOwnedPaths.add(p);
        stepTasks.push(cand);
        remaining.splice(idx, 1);
      }

      if (stepTasks.length > 0 && remaining.length > 0) {
        let remIdx = 0;
        while (remIdx < remaining.length) {
          const cand = remaining[remIdx];
          const owned = [...cand.files, ...cand.tests, ...(cand.lock_scopes || [])];
          if (owned.some((p) => activeExcludedPaths.has(p))) {
            remIdx += 1;
            continue;
          }
          const eligibleTargets = stepTasks
            .filter((target) => {
              if (cand.chapter_id && target.chapter_id && cand.chapter_id !== target.chapter_id) return false;
              const mergedFiles = new Set([...target.files, ...cand.files]);
              const mergedTasks = target.task_ids.length + cand.task_ids.length;
              if (mergedFiles.size > maxTaskFiles) return false;
              if (mergedTasks > this.maxTasksPerWorker) return false;
              if (target.estimated_loc + cand.estimated_loc > maxTaskLoc) return false;
              return !stepTasks.some(
                (other) =>
                  other !== target &&
                  owned.some(
                    (p) =>
                      other.files.includes(p) || other.tests.includes(p) || (other.lock_scopes || []).includes(p),
                  ),
              );
            })
            .sort((a, b) => a.estimated_loc - b.estimated_loc || a.task_ids.length - b.task_ids.length);
          if (eligibleTargets.length > 0) {
            this.#mergeGroupsInto(eligibleTargets[0], cand);
            for (const p of owned) usedOwnedPaths.add(p);
            remaining.splice(remIdx, 1);
          } else {
            remIdx += 1;
          }
        }
      }

      if (stepTasks.length === 0 && remaining.length > 0) {
        if (activeExcludedPaths.size > 0) {
          carryWaitForInflight = true;
          activeExcludedPaths = new Set();
          continue;
        }
        stepTasks.push(remaining.shift());
      }

      const stepChapterIds = Array.from(new Set(stepTasks.flatMap((g) => g.chapter_ids || [])));
      steps.push({
        step_index: steps.length + 1,
        parallel_count: stepTasks.length,
        chapter_ids: stepChapterIds,
        shared_test_files: [],
        waits_for_inflight: waitsForInflight,
        tasks: stepTasks,
      });
      activeExcludedPaths = new Set();
    }
    return steps;
  }
}
