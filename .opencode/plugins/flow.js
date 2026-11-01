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
  const specsDir = path.join(workspaceDir, bundleRel, "specs");
  if (fs.existsSync(specsDir)) {
    try {
      for (const entry of fs.readdirSync(specsDir, { withFileTypes: true })) {
        if (!entry.isDirectory()) continue;
        const specPath = path.join(specsDir, entry.name, "spec.md");
        if (!fs.existsSync(specPath)) continue;
        const content = fs.readFileSync(specPath, "utf8");
        const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---/);
        if (!fmMatch) continue;
        const fm = fmMatch[1];
        const flowId = fm.match(/^flow_id:\s*["']?([^"'\r\n]+)["']?/m)?.[1]?.trim() ?? entry.name;
        const state = fm.match(/^state:\s*["']?([^"'\r\n]+)["']?/m)?.[1]?.trim() ?? "unknown";
        const currentTask = fm.match(/^current_task:\s*["']?([^"'\r\n]+)["']?/m)?.[1]?.trim() ?? "";
        if (state !== "completed" && state !== "archived") {
          activeSpecs.push(
            currentTask && currentTask !== "null"
              ? `${flowId}(${state}, task=${currentTask})`
              : `${flowId}(${state})`,
          );
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
  return parts.join(" ");
}

const flowPlugin = {
  id: "flow",
  async setup(ctx) {
    const workspaceDir = ctx?.workspace?.root ?? ctx?.cwd ?? process.cwd();
    const summary = readBundleSummary(workspaceDir);

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
        systemMessage: summary,
      }));
    }

    return {
      "experimental.chat.system.transform": async (_input, output) => {
        if (Array.isArray(output?.system)) {
          output.system.push(summary);
        }
      },
    };
  },
};

export { flowPlugin, readBundleSummary, SUBAGENTS };
export default flowPlugin;
