/**
 * Ephemeral harness-native tier profile generator (`frontier`, `balanced`, `fast`, `light`).
 *
 * Writes gitignored local profiles tailored to each harness's native subagent model/effort rules:
 *   - Claude Code: `.claude/agents/flow-tier-*.md` (`model:` + `effort:`)
 *   - Codex CLI: `.codex/agents/flow-tier-*.toml` (`model` + `model_reasoning_effort`)
 *   - Cursor: `.cursor/agents/flow-tier-*.md` (`model`, `readonly`, `is_background`)
 *   - VS Code Copilot: `.github/agents/flow-tier-*.agent.md` (`model: [...]` fallback array or scalar for CLI)
 *   - Google Antigravity: scratch `runtime-<role>/agent.json` (`disable_model_selection: true`)
 */

import fs from "node:fs";
import path from "node:path";

import { readTextSafe, writeJsonAtomic, writeTextAtomic } from "../core/fs-io.mjs";
import { AdaptiveModelRouter } from "./routing.mjs";

const TIER_SPECS = Object.freeze([
  {
    tier: "frontier",
    taskKind: "planning",
    readonly: false,
    description: "Deep thinking planner, contract architect, and upward semantic validator.",
    instructions: "Perform deep architecture planning, semantic contract verification, and root-cause analysis within bounded scope.",
  },
  {
    tier: "balanced",
    taskKind: "implementation",
    readonly: false,
    description: "Balanced TDD slice executor implementing bounded code and test slices.",
    instructions: "Implement the assigned Context Pack slice directly, run the targeted verification command once, and report exact outcomes.",
  },
  {
    tier: "fast",
    taskKind: "implementation",
    readonly: false,
    description: "Fast micro-slice executor for well-specified small edits.",
    instructions: "Apply the specified micro-slice edit directly without exploratory search and exit cleanly.",
  },
  {
    tier: "light",
    taskKind: "narrow_fetch",
    readonly: true,
    description: "Read-only narrow file inspector and mechanical status helper.",
    instructions: "Summarize only explicitly listed files or lines in read-only mode without modifying files.",
  },
]);

/**
 * Ensure local gitexclude hides dynamically generated ephemeral agent tier profiles.
 *
 * @param {string} workspaceRoot
 */
function ensureLocalProfileExcludes(workspaceRoot) {
  const gitExclude = path.join(workspaceRoot, ".git", "info", "exclude");
  if (!fs.existsSync(path.dirname(gitExclude))) return;
  const cur = readTextSafe(gitExclude) || "";
  const lines = new Set(cur.split("\n").map((l) => l.trim()));
  const wanted = [
    ".claude/agents/flow-tier-*",
    ".codex/agents/flow-tier-*",
    ".cursor/agents/flow-tier-*",
    ".github/agents/flow-tier-*",
  ];
  const missing = wanted.filter((w) => !lines.has(w));
  if (missing.length > 0) {
    writeTextAtomic(gitExclude, `${cur.trimEnd()}${cur.trimEnd() ? "\n" : ""}${missing.join("\n")}\n`);
  }
}

export class HarnessProfileMaterializer {
  /**
   * @param {string} workspaceRoot
   * @param {any[]} candidates
   * @param {{ outDir?: string | null, harness?: string, target?: "ide" | "copilot-cli" }} [options]
   */
  static materialize(workspaceRoot, candidates, { outDir = null, harness = "agy", target = "ide" } = {}) {
    const root = path.resolve(workspaceRoot);
    const cleanHarness = String(harness || "agy").toLowerCase();
    const router = new AdaptiveModelRouter();
    ensureLocalProfileExcludes(root);

    /** @type {Record<string, string>} */
    const written = {};
    for (const spec of TIER_SPECS) {
      const route = router.select(candidates, {
        taskKind: spec.taskKind,
        risk: spec.tier === "frontier" ? "high" : "normal",
        complexity: spec.tier === "frontier" ? 3.8 : spec.tier === "balanced" ? 2.2 : spec.tier === "fast" ? 1.2 : 0.4,
      });

      const modelName = route.model || "inherit";
      const effortName = route.effort || (spec.tier === "frontier" ? "xhigh" : spec.tier === "light" ? "low" : "medium");

      if (cleanHarness === "claude") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".claude", "agents");
        const file = path.join(dir, `flow-tier-${spec.tier}.md`);
        const roBlock = spec.readonly ? "disallowedTools:\n  - Write\n  - Edit\n  - NotebookEdit\n  - Bash\n" : "";
        const effortLine = effortName !== "default" ? `effort: ${effortName}\n` : "";
        writeTextAtomic(
          file,
          `---\nname: flow-tier-${spec.tier}\ndescription: ${spec.description}\nmodel: ${modelName}\n${effortLine}${roBlock}---\n\n${spec.instructions}\n`,
        );
        written[spec.tier] = file;
      } else if (cleanHarness === "codex") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".codex", "agents");
        const file = path.join(dir, `flow-tier-${spec.tier}.toml`);
        const sb = spec.readonly ? "read-only" : "workspace-write";
        const effortLine = effortName !== "default" ? `model_reasoning_effort = ${JSON.stringify(effortName)}\n` : "";
        writeTextAtomic(
          file,
          `name = ${JSON.stringify(`flow-tier-${spec.tier}`)}\ndescription = ${JSON.stringify(spec.description)}\nmodel = ${JSON.stringify(modelName)}\n${effortLine}sandbox_mode = ${JSON.stringify(sb)}\ndeveloper_instructions = ${JSON.stringify(spec.instructions)}\n`,
        );
        written[spec.tier] = file;
      } else if (cleanHarness === "cursor" || cleanHarness === "cursor-agent") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".cursor", "agents");
        const file = path.join(dir, `flow-tier-${spec.tier}.md`);
        writeTextAtomic(
          file,
          `---\nname: flow-tier-${spec.tier}\ndescription: ${spec.description}\nmodel: ${modelName}\nreadonly: ${spec.readonly ? "true" : "false"}\nis_background: false\n---\n\n${spec.instructions}\n`,
        );
        written[spec.tier] = file;
      } else if (cleanHarness === "vscode" || cleanHarness === "copilot") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".github", "agents");
        const file = path.join(dir, `flow-tier-${spec.tier}.agent.md`);
        const chainModels = Array.from(new Set([modelName, ...(route.fallback_chain || []).map((f) => f.model)].filter(Boolean)));
        const modelYaml =
          target === "copilot-cli"
            ? `model: ${chainModels[0] || "auto"}`
            : `model: [${chainModels.slice(0, 4).map((m) => JSON.stringify(m)).join(", ")}]\nmodel-policy: preferred`;
        writeTextAtomic(
          file,
          `---\nname: flow-tier-${spec.tier}\ndescription: ${spec.description}\n${modelYaml}\n---\n\n${spec.instructions}\n`,
        );
        written[spec.tier] = file;
      } else {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".agents", "runtime-profiles");
        const file = path.join(dir, `runtime-${spec.tier}`, "agent.json");
        writeJsonAtomic(file, {
          name: `runtime-${spec.tier}`,
          role: spec.tier,
          model: route.runtime_target || modelName,
          requested_model: modelName,
          effort: effortName,
          disable_model_selection: true,
        });
        written[spec.tier] = file;
      }
    }

    return written;
  }
}
