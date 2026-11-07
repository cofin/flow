import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const SUBAGENTS = Object.freeze([
  { id: "code-reviewer", file: "agents/code-reviewer.md", readonly: true },
  { id: "executor", file: "agents/executor.md", readonly: false },
  { id: "plan-generator", file: "agents/plan-generator.md", readonly: false },
  { id: "prd-orchestrator", file: "agents/prd-orchestrator.md", readonly: false },
  { id: "quality-reviewer", file: "agents/quality-reviewer.md", readonly: true },
  { id: "researcher", file: "agents/researcher.md", readonly: true },
]);

function readBundleSummary(workspaceDir) {
  const baseMsg =
    "Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity.";
  if (!workspaceDir) {
    return baseMsg;
  }

  const agentsDir = path.join(workspaceDir, ".agents");
  if (!fs.existsSync(agentsDir)) {
    return baseMsg;
  }

  let bundleRel = ".agents/bundles";
  const setupStatePath = path.join(agentsDir, "setup-state.json");
  if (fs.existsSync(setupStatePath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(setupStatePath, "utf8"));
      if (typeof parsed.bundle_root === "string" && parsed.bundle_root.trim()) {
        bundleRel = parsed.bundle_root.trim();
      }
    } catch {
      bundleRel = ".agents/bundles";
    }
  }

  const activeSpecs = [];
  const pendingSync = [];
  const specsDir = path.join(workspaceDir, bundleRel, "specs");
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
        const content = fs.readFileSync(specPath, "utf8");
        const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
        if (!fmMatch) continue;
        const fm = fmMatch[1];
        const flowId = fm.match(/^flow_id:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? entry.name;
        const state = fm.match(/^state:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "unknown";
        let currentChapter = fm.match(/^current_chapter:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";
        const currentTask = fm.match(/^current_task:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";

        const chaptersDir = path.join(flowDir, "chapters");
        if (fs.existsSync(chaptersDir)) {
          const chEntries = fs
            .readdirSync(chaptersDir, { withFileTypes: true })
            .filter((ch) => ch.isDirectory() && ch.name.startsWith("ch"))
            .sort((a, b) => a.name.localeCompare(b.name));
          for (const ch of chEntries) {
            const chSpecPath = path.join(chaptersDir, ch.name, "spec.md");
            if (!fs.existsSync(chSpecPath)) continue;
            const chContent = fs.readFileSync(chSpecPath, "utf8");
            const chFm = chContent.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? "";
            const chState = chFm.match(/^state:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";
            const chRev = chFm.match(/^last_reviewed_commit:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";
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
                const tContent = fs.readFileSync(path.join(chTasksDir, tf), "utf8");
                const tFm = tContent.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? "";
                const tState = tFm.match(/^state:\s*["']?([^#"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";
                if (["completed", "closed", "deferred", "skipped"].includes(tState)) {
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
          if (hasCh && hasTk) {
            activeSpecs.push(`${flowId}(${state}, chapter=${currentChapter}, task=${currentTask})`);
          } else if (hasCh) {
            activeSpecs.push(`${flowId}(${state}, chapter=${currentChapter})`);
          } else if (hasTk) {
            activeSpecs.push(`${flowId}(${state}, task=${currentTask})`);
          } else {
            activeSpecs.push(`${flowId}(${state})`);
          }
        }
      }
    } catch {
      // Ignore transient filesystem errors during priming.
    }
  }

  const parts = [baseMsg, `Workspace bundle root: ${bundleRel}.`];
  if (fs.existsSync(path.join(agentsDir, "skills", "index.md"))) {
    parts.push("Project-local domain and review skills index: .agents/skills/index.md.");
  }
  if (activeSpecs.length > 0) {
    parts.push(`Active specs: ${activeSpecs.join(", ")}.`);
  }
  if (pendingSync.length > 0) {
    parts.push(`Pending chapter review/Markdown sync: ${pendingSync.join(", ")}.`);
  }
  parts.push("Flow Studio UI: npx flow-studio.");
  return parts.join(" ");
}

const flowPlugin = {
  id: "flow",
  async setup(ctx) {
    const workspaceDir = ctx?.workspace?.root ?? ctx?.cwd ?? process.cwd();

    if (ctx?.agent?.transform) {
      ctx.agent.transform((agents) => {
        const nextAgents = Array.isArray(agents) ? [...agents] : [];
        for (const subagent of SUBAGENTS) {
          nextAgents.push({
            id: subagent.id,
            promptFile: path.join(PLUGIN_ROOT, subagent.file),
            readonly: subagent.readonly,
          });
        }
        return nextAgents;
      });
    }

    if (ctx?.session?.hook) {
      ctx.session.hook("context", async () => ({
        systemMessage: readBundleSummary(workspaceDir),
      }));
    }

    return {
      "experimental.chat.system.transform": async (_input, output) => {
        if (Array.isArray(output?.system)) {
          output.system.push(readBundleSummary(workspaceDir));
        }
      },
    };
  },
};

export { flowPlugin, readBundleSummary, SUBAGENTS };
export default flowPlugin;
