/**
 * Ephemeral harness-native model profile generator (`strong`, `standard`, `fast`, `light`).
 *
 * Writes gitignored local profiles tailored to each harness's native subagent model/effort rules:
 *   - Claude Code: `.claude/agents/flow-model-*.md` (`model:` + `effort:`)
 *   - Codex CLI: `.codex/agents/flow-model-*.toml` (`model` + `model_reasoning_effort`)
 *   - Cursor: `.cursor/agents/flow-model-*.md` (`model`, `readonly`, `is_background`)
 *   - VS Code Copilot: `.github/agents/flow-model-*.agent.md` (`model: [...]` fallback array or scalar for CLI)
 *   - Google Antigravity: scratch `flow-model-<role>/agent.json` (`disable_model_selection: true`)
 */

import fs from "node:fs";
import path from "node:path";

import { readTextSafe, writeJsonAtomic, writeTextAtomic } from "../core/fs-io.mjs";
import { AdaptiveModelRouter } from "./routing.mjs";

const ROLE_SPECS = Object.freeze([
  {
    role: "strong",
    taskKind: "planning",
    readonly: false,
    description: "Strongest model for planning, spec review, and complex diagnosis.",
    instructions: "Handle architecture planning, spec validation, and root-cause analysis within the assigned scope.",
  },
  {
    role: "standard",
    taskKind: "implementation",
    readonly: false,
    description: "Standard task worker for code and tests.",
    instructions: "Implement the assigned task brief directly, run its verification command once, and report exact outcomes.",
  },
  {
    role: "fast",
    taskKind: "implementation",
    readonly: false,
    description: "Fast worker for small, well-specified tasks.",
    instructions: "Apply the specified task edit directly without broad search and stop when done.",
  },
  {
    role: "light",
    taskKind: "narrow_fetch",
    readonly: true,
    description: "Read-only file inspector and status helper.",
    instructions: "Summarize only explicitly listed files or lines in read-only mode without editing files.",
  },
]);

/**
 * Ensure local gitexclude hides dynamically generated ephemeral agent model profiles.
 *
 * @param {string} workspaceRoot
 */
function ensureLocalProfileExcludes(workspaceRoot) {
  const gitExclude = path.join(workspaceRoot, ".git", "info", "exclude");
  if (!fs.existsSync(path.dirname(gitExclude))) return;
  const cur = readTextSafe(gitExclude) || "";
  const lines = new Set(cur.split("\n").map((l) => l.trim()));
  const wanted = [
    ".claude/agents/flow-model-*",
    ".codex/agents/flow-model-*",
    ".cursor/agents/flow-model-*",
    ".github/agents/flow-model-*",
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
    for (const spec of ROLE_SPECS) {
      const route = router.select(candidates, {
        taskKind: spec.taskKind,
        risk: spec.role === "strong" ? "high" : "normal",
        complexity: spec.role === "strong" ? 3.8 : spec.role === "standard" ? 2.2 : spec.role === "fast" ? 1.2 : 0.4,
      });

      const modelName = route.model || "inherit";
      const effortName = route.effort || (spec.role === "strong" ? "xhigh" : spec.role === "light" ? "low" : "medium");

      if (cleanHarness === "claude") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".claude", "agents");
        const file = path.join(dir, `flow-model-${spec.role}.md`);
        const roBlock = spec.readonly ? "disallowedTools:\n  - Write\n  - Edit\n  - NotebookEdit\n  - Bash\n" : "";
        const effortLine = effortName !== "default" ? `effort: ${effortName}\n` : "";
        writeTextAtomic(
          file,
          `---\nname: flow-model-${spec.role}\ndescription: ${spec.description}\nmodel: ${modelName}\n${effortLine}${roBlock}---\n\n${spec.instructions}\n`,
        );
        written[spec.role] = file;
      } else if (cleanHarness === "codex") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".codex", "agents");
        const file = path.join(dir, `flow-model-${spec.role}.toml`);
        const sb = spec.readonly ? "read-only" : "workspace-write";
        const effortLine = effortName !== "default" ? `model_reasoning_effort = ${JSON.stringify(effortName)}\n` : "";
        writeTextAtomic(
          file,
          `name = ${JSON.stringify(`flow-model-${spec.role}`)}\ndescription = ${JSON.stringify(spec.description)}\nmodel = ${JSON.stringify(modelName)}\n${effortLine}sandbox_mode = ${JSON.stringify(sb)}\ndeveloper_instructions = ${JSON.stringify(spec.instructions)}\n`,
        );
        written[spec.role] = file;
      } else if (cleanHarness === "cursor" || cleanHarness === "cursor-agent") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".cursor", "agents");
        const file = path.join(dir, `flow-model-${spec.role}.md`);
        writeTextAtomic(
          file,
          `---\nname: flow-model-${spec.role}\ndescription: ${spec.description}\nmodel: ${modelName}\nreadonly: ${spec.readonly ? "true" : "false"}\nis_background: false\n---\n\n${spec.instructions}\n`,
        );
        written[spec.role] = file;
      } else if (cleanHarness === "vscode" || cleanHarness === "copilot") {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".github", "agents");
        const file = path.join(dir, `flow-model-${spec.role}.agent.md`);
        const chainModels = Array.from(new Set([modelName, ...(route.fallback_chain || []).map((f) => f.model)].filter(Boolean)));
        const modelYaml =
          target === "copilot-cli"
            ? `model: ${chainModels[0] || "auto"}`
            : `model: [${chainModels.slice(0, 4).map((m) => JSON.stringify(m)).join(", ")}]\nmodel-policy: preferred`;
        writeTextAtomic(
          file,
          `---\nname: flow-model-${spec.role}\ndescription: ${spec.description}\n${modelYaml}\n---\n\n${spec.instructions}\n`,
        );
        written[spec.role] = file;
      } else {
        const dir = outDir ? path.resolve(outDir) : path.join(root, ".agents", "runtime-profiles");
        const file = path.join(dir, `flow-model-${spec.role}`, "agent.json");
        writeJsonAtomic(file, {
          name: `flow-model-${spec.role}`,
          role: spec.role,
          model: route.runtime_target || modelName,
          requested_model: modelName,
          effort: effortName,
          disable_model_selection: true,
        });
        written[spec.role] = file;
      }
    }

    return written;
  }
}
