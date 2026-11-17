import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const INSTALL_HINT = "opencode plugin add github:cofin/flow";
const STUDIO_ROOT = path.join(PLUGIN_ROOT, "sidecars", "studio");

async function loadOptionalStudioModule(relPath) {
  const full = path.join(STUDIO_ROOT, relPath);
  if (!fs.existsSync(full)) return null;
  try {
    return await import(pathToFileURL(full).href);
  } catch {
    return null;
  }
}

const _fmMod = await loadOptionalStudioModule("core/frontmatter.mjs");
const _wtMod = await loadOptionalStudioModule("core/worktree.mjs");
const _invMod = await loadOptionalStudioModule("models/inventory.mjs");
const _routeMod = await loadOptionalStudioModule("models/routing.mjs");
const _plannerMod = await loadOptionalStudioModule("spec/task-planner.mjs");

/**
 * Minimal standalone YAML frontmatter parser fallback when loaded without `sidecars/studio/`.
 *
 * @param {string} markdown
 * @returns {{ data: Record<string, any>, body: string }}
 */
function fallbackParseFrontmatter(markdown) {
  const normalized = String(markdown || "").replace(/\r\n/g, "\n");
  const match = normalized.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) return { data: {}, body: normalized };
  /** @type {Record<string, any>} */
  const data = {};
  for (const line of match[1].split("\n")) {
    const kv = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (!kv) continue;
    let val = kv[2].replace(/\s+#.*$/, "").trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    if (val === "true") data[kv[1]] = true;
    else if (val === "false") data[kv[1]] = false;
    else if (val === "null") data[kv[1]] = null;
    else data[kv[1]] = val;
  }
  return { data, body: match[2] };
}

function fallbackResolveWorktreeContext(workspaceDir) {
  const root = path.resolve(workspaceDir || process.cwd());
  let bundleRel = ".agents/bundles";
  try {
    const setupPath = path.join(root, ".agents", "setup-state.json");
    if (fs.existsSync(setupPath)) {
      const cfg = JSON.parse(fs.readFileSync(setupPath, "utf8"));
      if (cfg?.bundle_root) bundleRel = String(cfg.bundle_root);
    }
  } catch {
    // Keep default bundleRel on invalid JSON.
  }
  return { effectiveAgentsRoot: root, bundleRel, isLinkedWorktree: false, ignorePolicy: "shared", mainWorktree: null };
}

const parseFrontmatter = _fmMod?.parseFrontmatter || fallbackParseFrontmatter;
const resolveWorktreeContext = _wtMod?.resolveWorktreeContext || fallbackResolveWorktreeContext;
const DynamicModelCatalog = _invMod?.DynamicModelCatalog || null;
const AdaptiveModelRouter = _routeMod?.AdaptiveModelRouter || null;
const TaskPlanner = _plannerMod?.TaskPlanner || null;

/**
 * Load Flow skills from `<plugin root>/skills/<name>/SKILL.md` as OpenCode V2 `Skill.Info` records.
 *
 * @param {string} [pluginRoot]
 * @returns {Array<{ id: string, name: string, description?: string, path: string, content: string }>}
 */
function loadSkills(pluginRoot = PLUGIN_ROOT) {
  const skillsDir = path.join(pluginRoot, "skills");
  if (!fs.existsSync(skillsDir)) return [];
  const skills = [];
  for (const entry of fs.readdirSync(skillsDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if (!entry.isDirectory()) continue;
    const skillPath = path.join(skillsDir, entry.name, "SKILL.md");
    if (!fs.existsSync(skillPath)) continue;
    const content = fs.readFileSync(skillPath, "utf8").replace(/\r\n/g, "\n");
    const { data } = parseFrontmatter(content);
    const name = data.name || entry.name;
    skills.push({
      id: name,
      name,
      ...(data.description ? { description: data.description } : {}),
      path: skillPath,
      content,
    });
  }
  return skills;
}

/**
 * Load Flow subagents from `<plugin root>/agents/*.md`.
 *
 * @param {string} [pluginRoot]
 * @returns {Array<{ id: string, name: string, description: string, system: string, readonly: boolean, taskKind: string }>}
 */
function loadSubagents(pluginRoot = PLUGIN_ROOT) {
  const agentsDir = path.join(pluginRoot, "agents");
  if (!fs.existsSync(agentsDir)) return [];
  const agents = [];
  for (const file of fs.readdirSync(agentsDir).filter((f) => f.endsWith(".md")).sort()) {
    const { data, body } = parseFrontmatter(fs.readFileSync(path.join(agentsDir, file), "utf8"));
    const id = data.name || path.basename(file, ".md");
    const readonly = data.readonly === true || data.readonly === "true";
    const taskKind =
      id === "prd-orchestrator" || id === "plan-generator"
        ? "planning"
        : id === "code-reviewer" || id === "quality-reviewer"
          ? "spec_review"
          : id === "researcher"
            ? "narrow_fetch"
            : "implementation";
    agents.push({
      id,
      name: id,
      description: String(data.description ?? ""),
      system: body.trim(),
      readonly,
      taskKind,
    });
  }
  return agents;
}

/**
 * Build concise OKF v0.2 bundle summary and active task digest for the OpenCode session context hook.
 *
 * @param {string} workspaceDir
 * @returns {string}
 */
function readBundleSummary(workspaceDir) {
  const baseMsg =
    "Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity.";
  if (!workspaceDir) return baseMsg;

  const wt = resolveWorktreeContext(workspaceDir);
  const effectiveRoot = wt.effectiveAgentsRoot;
  const agentsDir = path.join(effectiveRoot, ".agents");
  if (!fs.existsSync(agentsDir)) {
    return "Flow plugin loaded (no .agents/ bundle in this workspace; run /flow:setup to initialize).";
  }

  const bundleRel = wt.bundleRel || ".agents/bundles";
  const activeSpecs = [];
  const pendingSync = [];
  const degradedPlans = [];
  const nextStepHints = [];
  const specsDir = path.join(effectiveRoot, bundleRel, "specs");

  if (fs.existsSync(specsDir)) {
    try {
      const flowEntries = fs
        .readdirSync(specsDir, { withFileTypes: true })
        .filter((entry) => entry.isDirectory())
        .sort((a, b) => a.name.localeCompare(b.name));
      for (const entry of flowEntries) {
        const flowDir = path.join(specsDir, entry.name);
        const specPath = path.join(flowDir, "spec.md");
        if (!fs.existsSync(specPath)) continue;
        const { data } = parseFrontmatter(fs.readFileSync(specPath, "utf8"));
        const flowId = String(data.flow_id || entry.name);
        const state = String(data.state || "unknown");
        let currentChapter = data.current_chapter ? String(data.current_chapter) : "";
        const currentTask = data.current_task ? String(data.current_task) : "";
        let planningQuality = data.planning_quality ? String(data.planning_quality) : "";

        const chaptersDir = path.join(flowDir, "chapters");
        if (fs.existsSync(chaptersDir)) {
          const chEntries = fs
            .readdirSync(chaptersDir, { withFileTypes: true })
            .filter((ch) => ch.isDirectory() && ch.name.startsWith("ch"))
            .sort((a, b) => a.name.localeCompare(b.name));
          for (const ch of chEntries) {
            const chSpecPath = path.join(chaptersDir, ch.name, "spec.md");
            if (!fs.existsSync(chSpecPath)) continue;
            const { data: chData } = parseFrontmatter(fs.readFileSync(chSpecPath, "utf8"));
            const chState = String(chData.state || "");
            const chRev = chData.last_reviewed_commit ? String(chData.last_reviewed_commit) : "";
            if (chData.planning_quality === "degraded") planningQuality = "degraded";
            if ((!currentChapter || currentChapter === "null") && !["completed", "deferred", "skipped"].includes(chState)) {
              currentChapter = ch.name;
            }
            const chTasksDir = path.join(chaptersDir, ch.name, "tasks");
            if (fs.existsSync(chTasksDir)) {
              const taskFiles = fs
                .readdirSync(chTasksDir)
                .filter((f) => f.endsWith(".md") && f !== "index.md")
                .sort();
              let doneCount = 0;
              for (const tf of taskFiles) {
                const { data: tData } = parseFrontmatter(fs.readFileSync(path.join(chTasksDir, tf), "utf8"));
                if (["completed", "closed", "deferred", "skipped"].includes(String(tData.state || ""))) {
                  doneCount += 1;
                }
              }
              const unclosedDone =
                taskFiles.length > 0 &&
                doneCount === taskFiles.length &&
                !["completed", "deferred", "skipped"].includes(chState);
              const unreviewedCompleted = chState === "completed" && (!chRev || chRev === "null");
              if (unclosedDone || unreviewedCompleted) {
                pendingSync.push(`${flowId}/${ch.name}`);
              }
            }
          }
        }

        if (state !== "completed" && state !== "archived") {
          const hasCh = Boolean(currentChapter && currentChapter !== "null");
          const hasTk = Boolean(currentTask && currentTask !== "null");
          if (hasCh && hasTk) activeSpecs.push(`${flowId}(${state}, chapter=${currentChapter}, task=${currentTask})`);
          else if (hasCh) activeSpecs.push(`${flowId}(${state}, chapter=${currentChapter})`);
          else if (hasTk) activeSpecs.push(`${flowId}(${state}, task=${currentTask})`);
          else activeSpecs.push(`${flowId}(${state})`);

          if (planningQuality === "degraded") degradedPlans.push(flowId);
          try {
            if (TaskPlanner) {
              const planned = new TaskPlanner(effectiveRoot).plan({ flowId, chapterId: hasCh ? currentChapter : null });
              if (planned.steps?.length > 0) {
                const s0 = planned.steps[0];
                nextStepHints.push(`${flowId} step-1: ${s0.tasks.map((t) => t.task_id).join(",")}`);
              }
            }
          } catch {
            // Optional task summary fallback when spec has no tasks.
          }
        }
      }
    } catch {
      // Ignore transient filesystem errors during priming.
    }
  }

  const parts = [baseMsg, `Workspace bundle root: ${bundleRel}.`];
  if (wt.isLinkedWorktree) {
    parts.push(
      wt.ignorePolicy === "local-only" && wt.mainWorktree
        ? `Linked Git worktree (local-only .agents): .agents is shared from primary checkout ${wt.mainWorktree}/.agents.`
        : "Linked Git worktree (shared .agents): edit worktree .agents/ directly and reuse linked environments."
    );
  }
  if (fs.existsSync(path.join(agentsDir, "skills", "index.md"))) {
    parts.push("Project-local domain and review skills index: .agents/skills/index.md.");
  }
  if (activeSpecs.length > 0) parts.push(`Active specs: ${activeSpecs.join(", ")}.`);
  if (nextStepHints.length > 0) parts.push(`Ready tasks: ${nextStepHints.join("; ")}.`);
  if (degradedPlans.length > 0) {
    parts.push(
      `Degraded planning quality warning (planning_quality=degraded — not planned with the strongest model): ${degradedPlans.join(", ")}.`
    );
  }
  if (pendingSync.length > 0) parts.push(`Pending chapter review/Markdown sync: ${pendingSync.join(", ")}.`);
  parts.push("Flow Studio UI: npx --yes --package github:cofin/flow flow-studio.");
  return parts.join(" ");
}

/**
 * OpenCode V2 Promise plugin.
 */
const flowPlugin = {
  id: "flow",
  async setup(ctx) {
    const workspaceDir = ctx.location?.directory ?? process.cwd();
    const skills = loadSkills();
    const agents = loadSubagents();

    if (skills.length === 0 && agents.length === 0) {
      console.warn(
        `[flow] skills/ and agents/ not found next to ${PLUGIN_ROOT}; install the full package with: ${INSTALL_HINT}`
      );
    }

    if (skills.length > 0) {
      await ctx.skill.transform((editor) => {
        for (const skill of skills) {
          if (!editor.get(skill.id)) editor.add(skill);
        }
      });
    }

    if (typeof ctx.mcp?.transform === "function") {
      const mcpEntry = path.join(PLUGIN_ROOT, "sidecars", "studio", "mcp-server.mjs");
      if (fs.existsSync(mcpEntry)) {
        await ctx.mcp.transform((editor) => {
          if (!editor.get("flow-studio")) {
            editor.set("flow-studio", {
              type: "local",
              command: ["node", mcpEntry],
              cwd: workspaceDir,
              codemode: true,
            });
          }
        });
      }
    }

    if (agents.length > 0) {
      let candidates = [];
      if (DynamicModelCatalog) {
        try {
          const catalog = new DynamicModelCatalog({ projectRoot: workspaceDir });
          candidates = await catalog.discoverHarnessCatalog({ harness: "opencode", allowNetwork: false });
        } catch {
          candidates = [];
        }
      }
      const router = AdaptiveModelRouter ? new AdaptiveModelRouter() : null;
      await ctx.agent.transform((editor) => {
        for (const agent of agents) {
          const decision =
            router && candidates.length > 0 ? router.select(candidates, { taskKind: agent.taskKind }) : null;
          editor.update(agent.id, (item) => {
            item.name = agent.name;
            item.description = agent.description;
            item.system = agent.system;
            item.mode = "subagent";
            if (decision?.model) item.model = decision.model;
            if (decision?.effort && decision.effort !== "default") item.variant = decision.effort;
            if (agent.readonly) {
              item.permissions.push({ action: "edit", resource: "*", effect: "deny" });
            }
          });
        }
      });
    }

    await ctx.session.hook("context", (event) => {
      event.system.push({ type: "text", text: readBundleSummary(workspaceDir) });
    });
  },
};

export { flowPlugin, loadSkills, loadSubagents, parseFrontmatter, readBundleSummary };
export default flowPlugin;
