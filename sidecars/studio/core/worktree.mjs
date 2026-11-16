/**
 * Linked Git worktree inspector, environment artifact linker, and fallback bundle sync.
 * Replaces separate Python, plugin, and sidecar worktree helpers with one canonical module.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { isExistingDir, readJsonSafe, writeTextAtomic } from "./fs-io.mjs";

export const LINKED_ENV_ARTIFACTS = Object.freeze([
  ".venv",
  "node_modules",
  "uv.toml",
  ".npmrc",
  ".python-version",
]);

const SKIP_SYNC_NAMES = new Set(["worktrees", "scratch", "studio-live-state.json"]);

/**
 * Detect whether `targetPath` is a POSIX symlink or Windows symlink/NTFS junction.
 *
 * @param {string} targetPath
 * @returns {boolean}
 */
export function isLinkOrJunction(targetPath) {
  try {
    const st = fs.lstatSync(targetPath);
    if (st.isSymbolicLink()) return true;
  } catch {
    return false;
  }
  if (process.platform === "win32") {
    try {
      const real = fs.realpathSync(targetPath);
      return path.resolve(real) !== path.resolve(targetPath);
    } catch {
      return false;
    }
  }
  return false;
}

/**
 * Safe symlink / Windows junction helper returning true if created or already present.
 *
 * @param {string} src
 * @param {string} dst
 * @returns {boolean}
 */
export function safeLinkPath(src, dst) {
  try {
    fs.lstatSync(dst);
    return true;
  } catch {
    // Destination absent; link below.
  }
  try {
    if (!fs.existsSync(src)) return false;
    const isDir = fs.statSync(src).isDirectory();
    fs.symlinkSync(src, dst, isDir ? (process.platform === "win32" ? "junction" : "dir") : "file");
    return true;
  } catch {
    return false;
  }
}

/**
 * Resolve linked Git worktree metadata without spawning git when `.git` is a regular file,
 * falling back to `git rev-parse --git-common-dir` when needed.
 *
 * @param {string} workspaceRoot
 */
export function resolveWorktreeContext(workspaceRoot) {
  const root = path.resolve(workspaceRoot);
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

  const localSetup = readJsonSafe(path.join(root, ".agents", "setup-state.json"));
  const mainSetup = mainWorktree ? readJsonSafe(path.join(mainWorktree, ".agents", "setup-state.json")) : null;

  let ignorePolicy = String(
    localSetup?.workflow_preferences?.ignore_policy ||
      localSetup?.ignore_policy ||
      mainSetup?.workflow_preferences?.ignore_policy ||
      mainSetup?.ignore_policy ||
      "",
  ).trim();

  if (!ignorePolicy) {
    if (mainWorktree) {
      const localAgents = path.join(root, ".agents");
      let hasRealLocal = false;
      try {
        hasRealLocal = fs.existsSync(localAgents) && !fs.lstatSync(localAgents).isSymbolicLink();
      } catch {
        hasRealLocal = false;
      }
      ignorePolicy = !hasRealLocal && fs.existsSync(path.join(mainWorktree, ".agents")) ? "local-only" : "shared";
    } else {
      ignorePolicy = "shared";
    }
  }

  const effectiveAgentsRoot =
    mainWorktree && ignorePolicy === "local-only" && fs.existsSync(path.join(mainWorktree, ".agents"))
      ? mainWorktree
      : root;

  const bundleRel = String(
    localSetup?.bundle_root || mainSetup?.bundle_root || ".agents/bundles",
  ).trim() || ".agents/bundles";

  return {
    projectDir: root,
    isLinkedWorktree: Boolean(mainWorktree),
    mainWorktree,
    ignorePolicy,
    effectiveAgentsRoot,
    effectiveRoot: effectiveAgentsRoot,
    bundleRel,
  };
}

/**
 * Inspect linked Git worktree environment and optionally link `.venv`, `node_modules`, and `.agents/`.
 *
 * @param {string} workspaceRoot
 * @param {{ createLinks?: boolean }} [options]
 */
export function inspectOrBootstrapWorktree(workspaceRoot, { createLinks = false } = {}) {
  const ctx = resolveWorktreeContext(workspaceRoot);
  /** @type {string[]} */
  const linkedArtifacts = [];
  /** @type {string[]} */
  const warnings = [];
  let routingMode = "primary";

  if (ctx.isLinkedWorktree && ctx.mainWorktree) {
    for (const art of LINKED_ENV_ARTIFACTS) {
      const src = path.join(ctx.mainWorktree, art);
      const dst = path.join(ctx.projectDir, art);
      if (isLinkOrJunction(dst)) {
        linkedArtifacts.push(art);
      } else if (createLinks && safeLinkPath(src, dst)) {
        linkedArtifacts.push(art);
      }
    }

    if (ctx.ignorePolicy === "local-only" && isExistingDir(path.join(ctx.mainWorktree, ".agents"))) {
      const dstAgents = path.join(ctx.projectDir, ".agents");
      let linked = isLinkOrJunction(dstAgents);
      if (!linked && createLinks) {
        linked = safeLinkPath(path.join(ctx.mainWorktree, ".agents"), dstAgents);
      }
      if (linked) {
        routingMode = "symlink";
      } else {
        routingMode = "copy-fallback";
        warnings.push("Local-only .agents could not be symlinked into linked worktree; use worktree sync.");
      }
    } else {
      routingMode = "shared";
    }
  }

  const targetAgentsDir = path.join(ctx.effectiveAgentsRoot, ".agents");
  const hasFlow = fs.existsSync(targetAgentsDir);
  let bundleWritable = true;
  if (hasFlow) {
    try {
      fs.accessSync(targetAgentsDir, fs.constants.W_OK);
    } catch {
      bundleWritable = false;
    }
  }

  return {
    project_dir: ctx.projectDir,
    main_worktree: ctx.mainWorktree,
    is_linked_worktree: ctx.isLinkedWorktree,
    has_flow: hasFlow,
    ignore_policy: ctx.ignorePolicy,
    bundle_rel: ctx.bundleRel,
    target_agents_dir: hasFlow ? targetAgentsDir : null,
    target_bundle_dir: hasFlow ? path.join(ctx.effectiveAgentsRoot, ctx.bundleRel) : null,
    routing_mode: routingMode,
    bundle_writable: bundleWritable,
    linked_artifacts: linkedArtifacts,
    warnings,
  };
}

/**
 * Copy non-transient `.agents/` files from `srcRoot` to `dstRoot`.
 *
 * @param {string} srcAgents
 * @param {string} dstAgents
 */
function mergeAgentsTrees(srcAgents, dstAgents) {
  let copied = 0;
  let skipped = 0;
  if (!isExistingDir(srcAgents)) return { copied, skipped };
  const walkCopy = (curDir) => {
    for (const ent of fs.readdirSync(curDir, { withFileTypes: true })) {
      if (SKIP_SYNC_NAMES.has(ent.name)) {
        skipped += 1;
        continue;
      }
      const full = path.join(curDir, ent.name);
      const rel = path.relative(srcAgents, full);
      const target = path.join(dstAgents, rel);
      if (ent.isDirectory()) {
        fs.mkdirSync(target, { recursive: true });
        walkCopy(full);
      } else if (ent.isFile()) {
        writeTextAtomic(target, fs.readFileSync(full, "utf8"));
        copied += 1;
      }
    }
  };
  walkCopy(srcAgents);
  return { copied, skipped };
}

/**
 * Seed a linked worktree's `.agents/` copy from the primary checkout.
 *
 * @param {string} workspaceRoot
 */
export function syncMainBundleToWorktree(workspaceRoot) {
  const ctx = resolveWorktreeContext(workspaceRoot);
  if (!ctx.isLinkedWorktree || !ctx.mainWorktree) {
    return { ok: false, reason: "Not inside a linked Git worktree." };
  }
  const srcAgents = path.join(ctx.mainWorktree, ".agents");
  const dstAgents = path.join(ctx.projectDir, ".agents");
  const stats = mergeAgentsTrees(srcAgents, dstAgents);
  return { ok: true, direction: "main-to-worktree", ...stats };
}

/**
 * Sync local-only changes from a linked worktree back to the primary checkout.
 *
 * @param {string} workspaceRoot
 */
export function syncWorktreeBundleToMain(workspaceRoot) {
  const ctx = resolveWorktreeContext(workspaceRoot);
  if (!ctx.isLinkedWorktree || !ctx.mainWorktree) {
    return { ok: false, reason: "Not inside a linked Git worktree." };
  }
  const srcAgents = path.join(ctx.projectDir, ".agents");
  const dstAgents = path.join(ctx.mainWorktree, ".agents");
  const stats = mergeAgentsTrees(srcAgents, dstAgents);
  return { ok: true, direction: "worktree-to-main", ...stats };
}

/**
 * Provision an isolated detached Git worktree under `.agents/worktrees/<harness>-<runId>`
 * with shared `.venv`, `node_modules`, `uv.toml`, `.npmrc`, `.python-version`, and `local-only` `.agents`.
 *
 * @param {string} workspacePath
 * @param {string} harness
 * @param {string} runId
 * @returns {string}
 */
export function provisionIsolatedWorktree(workspacePath, harness, runId) {
  const root = path.resolve(workspacePath);
  const wtRoot = path.join(root, ".agents", "worktrees");
  fs.mkdirSync(wtRoot, { recursive: true });
  const targetDir = path.join(wtRoot, `${harness}-${runId}`);
  const res = spawnSync("git", ["worktree", "add", "--detach", targetDir, "HEAD"], {
    cwd: root,
    encoding: "utf8",
  });
  if (res.status !== 0) {
    throw new Error(`Failed to create isolated git worktree: ${res.stderr || res.stdout}`);
  }
  for (const art of LINKED_ENV_ARTIFACTS) {
    safeLinkPath(path.join(root, art), path.join(targetDir, art));
  }
  const setup = readJsonSafe(path.join(root, ".agents", "setup-state.json"));
  const ignorePolicy = String(setup?.workflow_preferences?.ignore_policy || setup?.ignore_policy || "");
  if ((ignorePolicy === "local-only" || !fs.existsSync(path.join(targetDir, ".agents"))) && fs.existsSync(path.join(root, ".agents"))) {
    safeLinkPath(path.join(root, ".agents"), path.join(targetDir, ".agents"));
  }
  return targetDir;
}
