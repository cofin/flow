/**
 * In-process Claude Code Mod (`v2.1.287+`) for Flow.
 *
 * Registers:
 *   1. `AbovePrompt` compact task progress band
 *   2. `SidePane` Studio companion view (active tasks and open review notes)
 *   3. `tool.call` (`Agent`) interceptor that materializes `.claude/agents/flow-model-*.md`,
 *      routes `subagent_type` to the matching model role, and attaches task briefs.
 */

import path from "node:path";

import { DynamicModelCatalog } from "../../../sidecars/studio/models/inventory.mjs";
import { HarnessProfileMaterializer } from "../../../sidecars/studio/models/profiles.mjs";
import { AdaptiveModelRouter, DecisionEngine } from "../../../sidecars/studio/models/routing.mjs";
import { SpecEngine } from "../../../sidecars/studio/spec/spec-engine.mjs";
import { TaskPlanner } from "../../../sidecars/studio/spec/task-planner.mjs";

const UPWARD_PROMPT_RE = /\b(plan|spec|architecture|validat|verify|semantic|review|audit|committee|adversarial|diagnos)\b/i;
const LIGHT_PROMPT_RE = /\b(summarize|fetch|lookup|list|sync|status|grep|inspect)\b/i;

/**
 * Determine task kind from an `Agent` tool call payload.
 *
 * @param {string} subagentType
 * @param {string} promptText
 */
export function classifyAgentCall(subagentType, promptText) {
  const agent = String(subagentType || "").toLowerCase();
  const prompt = String(promptText || "");
  if (agent.includes("plan") || agent.includes("prd") || agent.includes("reviewer") || UPWARD_PROMPT_RE.test(prompt)) {
    return { taskKind: agent.includes("reviewer") ? "code_review" : "planning", risk: "high" };
  }
  if (LIGHT_PROMPT_RE.test(prompt) && !agent.includes("executor")) {
    return { taskKind: "narrow_fetch", risk: "low" };
  }
  return { taskKind: "implementation", risk: "normal" };
}

/**
 * Resolve workspace snapshot & next runnable summary for UI bands without touching LLM context.
 *
 * @param {string} workspaceRoot
 */
export function buildModSummary(workspaceRoot) {
  try {
    const engine = new SpecEngine(workspaceRoot);
    const { specs, next_runnable } = engine.status();
    const active = specs.find((s) => s.state === "active" || s.state === "in_progress") || specs[0];
    if (!active) return { hasSpec: false, line: "Flow: ready (/flow:setup to initialize)" };
    const counts = active.task_counts || { completed: 0, total: 0 };
    const nextCount = next_runnable?.ready_tasks?.length || 0;
    return {
      hasSpec: true,
      flowId: active.flow_id,
      title: active.title,
      state: active.state,
      progress: `${counts.completed}/${counts.total}`,
      readyCount: nextCount,
      line: `Flow [${active.flow_id}] ${counts.completed}/${counts.total} tasks (${nextCount} ready)`,
      nextTasks: next_runnable?.ready_tasks || [],
    };
  } catch {
    return { hasSpec: false, line: "Flow Companion active" };
  }
}

/**
 * Claude Code Mod entrypoint.
 *
 * @param {(event: string, filterOrHandler: any, maybeHandler?: Function) => void} on
 * @param {{ workspaceRoot?: string }} [options]
 */
export const register = (on, options = {}) => {
  const workspace = path.resolve(options.workspaceRoot || process.env.CLAUDE_PROJECT_DIR || process.cwd());
  const catalog = new DynamicModelCatalog({ projectRoot: workspace });
  const decisionEngine = new DecisionEngine();
  const router = new AdaptiveModelRouter({ decisionEngine });

  on("tool.call", { tool: "Agent" }, async ($, e, next) => {
    const input = e?.input && typeof e.input === "object" ? { ...e.input } : {};
    const prompt = String(input.prompt || "");
    const origType = String(input.subagent_type || "");
    const { taskKind, risk } = classifyAgentCall(origType, prompt);

    try {
      const candidates = await catalog.discoverHarnessCatalog({ harness: "claude" });
      HarnessProfileMaterializer.materialize(workspace, candidates, { harness: "claude" });
      const evalRes = await decisionEngine.evaluate({ taskKind, risk });
      const route = router.select(candidates, { taskKind, risk, complexity: evalRes.complexity_rubric });

      if (route.role && !origType.includes(":")) {
        input.subagent_type = `flow-model-${route.role}`;
      }

      if (!prompt.includes("TASK BRIEF") && (taskKind === "implementation" || taskKind === "semantic_validation")) {
        const engine = new SpecEngine(workspace);
        const { next_runnable } = engine.status();
        if (next_runnable?.flow_id) {
          const planned = new TaskPlanner(workspace).plan({
            flowId: next_runnable.flow_id,
            chapterId: next_runnable.chapter_id || null,
            includeBriefs: true,
          });
          const firstBrief = planned.steps?.[0]?.tasks?.[0]?.brief;
          if (firstBrief) {
            input.prompt = `${prompt}\n\n[FLOW TASK BRIEF ~${firstBrief.approx_tokens} tokens]\n${JSON.stringify({
              group: firstBrief.group_id,
              files: firstBrief.files,
              tests: firstBrief.tests,
              upstream: firstBrief.upstream_changes,
            })}`;
          }
        }
      }

      if (e && typeof e === "object") e.input = input;
      if ($.ui?.invalidate) $.ui.invalidate("ui.render");
    } catch {
      // Never block an Agent invocation if routing or context packing fails.
    }
    return next(e);
  });

  if (typeof on === "function") {
    on("ui.render", { component: "AbovePrompt" }, ($, e) => {
      const ui = $.ui?.resolve ? $.ui.resolve(e) : {};
      const Box = ui.Box || ((props) => props);
      const Text = ui.Text || ((props) => props);
      const summary = buildModSummary(workspace);
      return Box({ paddingX: 1 }, Text({ dimColor: !summary.hasSpec }, summary.line));
    });

    on("ui.render", { component: "SidePane" }, ($, e) => {
      const ui = $.ui?.resolve ? $.ui.resolve(e) : {};
      const Box = ui.Box || ((props) => props);
      const Text = ui.Text || ((props) => props);
      const summary = buildModSummary(workspace);
      const rows = [Text({ bold: true }, `Flow Studio — ${summary.flowId || "No Active Spec"}`)];
      rows.push(Text({}, summary.line));
      for (const rt of summary.nextTasks || []) {
        rows.push(Text({}, `• ${rt.id}: ${rt.title}`));
      }
      return Box({ flexDirection: "column", padding: 1 }, ...rows);
    });
  }
};

export default register;
