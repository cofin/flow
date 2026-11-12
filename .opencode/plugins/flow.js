import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const PLUGIN_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const INSTALL_HINT = "opencode plugin add github:cofin/flow";

/**
 * Parse the scalar `key: value` lines of a Markdown file's YAML frontmatter.
 *
 * Flow's agent and skill files only use single-line scalars for the keys the plugin reads,
 * so nested lists and block scalars are skipped rather than parsed.
 *
 * @param {string} content Markdown text.
 * @returns {{ data: Record<string, string>, body: string }}
 */
function parseFrontmatter(content) {
  const normalized = content.replace(/\r\n/g, "\n");
  const match = normalized.match(/^---\n([\s\S]*?)\n---\n?/);
  if (!match) return { data: {}, body: normalized };
  const data = {};
  for (const line of match[1].split("\n")) {
    const kv = line.match(/^([A-Za-z_][\w-]*):\s*(.*)$/);
    if (!kv || !kv[2]) continue;
    let value = kv[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    data[kv[1]] = value;
  }
  return { data, body: normalized.slice(match[0].length) };
}

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
 * @returns {Array<{ id: string, name: string, description: string, system: string, readonly: boolean }>}
 */
function loadSubagents(pluginRoot = PLUGIN_ROOT) {
  const agentsDir = path.join(pluginRoot, "agents");
  if (!fs.existsSync(agentsDir)) return [];
  const agents = [];
  for (const file of fs.readdirSync(agentsDir).filter((f) => f.endsWith(".md")).sort()) {
    const { data, body } = parseFrontmatter(fs.readFileSync(path.join(agentsDir, file), "utf8"));
    const id = data.name || path.basename(file, ".md");
    agents.push({
      id,
      name: id,
      description: data.description ?? "",
      system: body.trim(),
      readonly: data.readonly === "true",
    });
  }
  return agents;
}

function resolveWorktreeEnv(workspaceDir) {
  const root = path.resolve(workspaceDir);
  const gitMarker = path.join(root, ".git");
  let mainWorktree = null;
  try {
    if (fs.existsSync(gitMarker) && fs.statSync(gitMarker).isFile()) {
      const rawGit = fs.readFileSync(gitMarker, "utf8").trim();
      const match = rawGit.match(/^gitdir:\s*(.+)$/m);
      if (match) {
        const gitDir = path.resolve(root, match[1].trim());
        const commonFile = path.join(gitDir, "commondir");
        const commonGitDir = fs.existsSync(commonFile)
          ? path.resolve(gitDir, fs.readFileSync(commonFile, "utf8").trim())
          : path.resolve(gitDir, "../..");
        const candidateMain = path.dirname(commonGitDir);
        if (candidateMain && path.resolve(candidateMain) !== root) {
          mainWorktree = path.resolve(candidateMain);
        }
      }
    }
  } catch {
    mainWorktree = null;
  }

  if (!mainWorktree) {
    return { effectiveRoot: root, worktreeNote: "" };
  }

  const linkItem = (src, dst) => {
    try {
      fs.lstatSync(dst);
      return;
    } catch {
      // Destination does not exist yet.
    }
    try {
      if (!fs.existsSync(src)) return;
      const isDir = fs.statSync(src).isDirectory();
      fs.symlinkSync(src, dst, isDir ? (process.platform === "win32" ? "junction" : "dir") : "file");
    } catch {
      // Ignore read-only sandbox link errors.
    }
  };

  for (const art of [".venv", "node_modules", "uv.toml", ".npmrc"]) {
    linkItem(path.join(mainWorktree, art), path.join(root, art));
  }

  const readPolicy = (base) => {
    try {
      const parsed = JSON.parse(fs.readFileSync(path.join(base, ".agents", "setup-state.json"), "utf8"));
      return parsed?.workflow_preferences?.ignore_policy || parsed?.ignore_policy || "";
    } catch {
      return "";
    }
  };

  let ignorePolicy = readPolicy(root) || readPolicy(mainWorktree);
  if (!ignorePolicy) {
    const localAgents = path.join(root, ".agents");
    const hasRealLocalAgents = fs.existsSync(localAgents) && !fs.lstatSync(localAgents).isSymbolicLink();
    ignorePolicy = !hasRealLocalAgents && fs.existsSync(path.join(mainWorktree, ".agents")) ? "local-only" : "shared";
  }

  if (ignorePolicy === "local-only" && fs.existsSync(path.join(mainWorktree, ".agents"))) {
    linkItem(path.join(mainWorktree, ".agents"), path.join(root, ".agents"));
    return {
      effectiveRoot: mainWorktree,
      worktreeNote: `Linked Git worktree (local-only .agents): .agents is shared from primary checkout ${mainWorktree}/.agents — edit Flow Markdown there (or via symlinked .agents/), and reuse symlinked .venv with uv run --no-sync (do not run make install).`,
    };
  }
  return {
    effectiveRoot: root,
    worktreeNote:
      "Linked Git worktree (shared .agents): edit worktree .agents/ directly, and reuse symlinked .venv with uv run --no-sync (do not run make install).",
  };
}

function readBundleSummary(workspaceDir) {
  const baseMsg =
    "Flow Spec-Driven Development is active. Resolve the bundle root from .agents/setup-state.json (default .agents/bundles/), read its index.md and applicable nested knowledge chapters, and follow skills/flow/references/state.md for direct Markdown + Git continuity.";
  if (!workspaceDir) {
    return baseMsg;
  }

  const { effectiveRoot, worktreeNote } = resolveWorktreeEnv(workspaceDir);
  const agentsDir = path.join(effectiveRoot, ".agents");
  if (!fs.existsSync(agentsDir)) {
    return "Flow plugin loaded (no .agents/ bundle in this workspace; run /flow:setup to initialize).";
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
  const degradedPlans = [];
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
        const content = fs.readFileSync(specPath, "utf8").replace(/\r\n/g, "\n");
        const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
        if (!fmMatch) continue;
        const fm = fmMatch[1];
        const flowId = fm.match(/^flow_id:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? entry.name;
        const state = fm.match(/^state:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "unknown";
        let currentChapter = fm.match(/^current_chapter:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
        const currentTask = fm.match(/^current_task:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
        let planningQuality = fm.match(/^planning_quality:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";

        const chaptersDir = path.join(flowDir, "chapters");
        if (fs.existsSync(chaptersDir)) {
          const chEntries = fs
            .readdirSync(chaptersDir, { withFileTypes: true })
            .filter((ch) => ch.isDirectory() && ch.name.startsWith("ch"))
            .sort((a, b) => a.name.localeCompare(b.name));
          for (const ch of chEntries) {
            const chSpecPath = path.join(chaptersDir, ch.name, "spec.md");
            if (!fs.existsSync(chSpecPath)) continue;
            const chContent = fs.readFileSync(chSpecPath, "utf8").replace(/\r\n/g, "\n");
            const chFm = chContent.match(/^---\n([\s\S]*?)\n---/)?.[1] ?? "";
            const chState = chFm.match(/^state:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
            const chRev = chFm.match(/^last_reviewed_commit:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
            const chPq = chFm.match(/^planning_quality:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
            if (chPq === "degraded") planningQuality = "degraded";
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
                const tContent = fs.readFileSync(path.join(chTasksDir, tf), "utf8").replace(/\r\n/g, "\n");
                const tFm = tContent.match(/^---\n([\s\S]*?)\n---/)?.[1] ?? "";
                const tState = tFm.match(/^state:\s*["']?([^#"'\n]+)["']?/m)?.[1]?.trim() ?? "";
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
          if (planningQuality === "degraded") {
            degradedPlans.push(flowId);
          }
        }
      }
    } catch {
      // Ignore transient filesystem errors during priming.
    }
  }

  const parts = [baseMsg, `Workspace bundle root: ${bundleRel}.`];
  if (worktreeNote) {
    parts.push(worktreeNote);
  }
  if (fs.existsSync(path.join(agentsDir, "skills", "index.md"))) {
    parts.push("Project-local domain and review skills index: .agents/skills/index.md.");
  }
  if (activeSpecs.length > 0) {
    parts.push(`Active specs: ${activeSpecs.join(", ")}.`);
  }
  if (degradedPlans.length > 0) {
    parts.push(
      `Degraded planning quality warning (planning_quality=degraded — not planned with optimal primary frontier thinking model): ${degradedPlans.join(", ")}.`
    );
  }
  if (pendingSync.length > 0) {
    parts.push(`Pending chapter review/Markdown sync: ${pendingSync.join(", ")}.`);
  }
  parts.push("Flow Studio UI: npx --yes --package github:cofin/flow flow-studio.");
  return parts.join(" ");
}

/**
 * OpenCode V2 Promise plugin.
 *
 * Registers Flow skills and subagents through the domain editors and injects the live
 * bundle summary into every agent-loop model request through the session `context` hook.
 * A standalone copy outside the package (for example `~/.config/opencode/plugins/flow.js`)
 * still injects the summary but cannot find `skills/` or `agents/`, so it warns once.
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

    if (agents.length > 0) {
      await ctx.agent.transform((editor) => {
        for (const agent of agents) {
          editor.update(agent.id, (item) => {
            item.name = agent.name;
            item.description = agent.description;
            item.system = agent.system;
            item.mode = "subagent";
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
