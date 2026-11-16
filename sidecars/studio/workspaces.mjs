/**
 * Workspace registry (pinned workspaces, Home view preference, and recent-workspaces.tsv)
 * plus safe scoped WorkspacePermissionAdvisor for `.agents/workspace-permissions.json`.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  isExistingDir,
  isInternalSidecarPath,
  isTransientTestPathForConfig,
  parseIsoMs,
  readJsonSafe,
  readTextSafe,
  sha256Hex,
  StudioStateStore,
  uriToWorkspacePath,
  writeJsonAtomic,
  writeTextAtomic,
} from "./core/fs-io.mjs";

const DANGEROUS_COMMAND_TARGETS = new Set([
  "*",
  "bash",
  "sh",
  "zsh",
  "fish",
  "dash",
  "csh",
  "tcsh",
  "ksh",
  "pwsh",
  "powershell",
  "cmd",
  "python",
  "python3",
  "node",
  "perl",
  "ruby",
  "php",
  "rm",
  "rmdir",
  "sudo",
  "su",
  "doas",
  "chmod",
  "chown",
  "curl",
  "wget",
  "ssh",
  "scp",
  "rsync",
  "eval",
  "exec",
  "env",
  "xargs",
  "git push",
  "git reset",
  "git clean",
  "docker run",
  "docker exec",
]);

const FORBIDDEN_GRANTS = new Set([
  "command(*)",
  "command(regex:.*)",
  "unsandboxed(*)",
  "write_file(*)",
  "read_file(*)",
  "mcp(*)",
  "read_url(*)",
  "execute_url(*)",
  "download_url(*)",
]);

const SAFE_MAKE_TARGET_RE =
  /^(?:lint|format|check|test|test-[a-z0-9_-]+|unit|validate|build|typecheck|verify|docs|docs-build|setup-env)$/i;
const SAFE_NPM_SCRIPT_RE =
  /^(?:test(?::[a-z0-9_-]+)?|lint(?::[a-z0-9_-]+)?|format:check|check|typecheck|build|verify|validate|docs:build)$/i;
const HOOK_KEY = "flow-workspace-allowlist";
const HOOK_MATCHER = "run_command|read_file|write_file|edit_file|read_url_content|mcp_.*|call_mcp_tool";

/**
 * Manage persistent list of user workspaces, sticky pins, and Studio Home preference.
 */
export class WorkspaceRegistry {
  /**
   * @param {string | null} [defaultWorkspace]
   * @param {{ env?: NodeJS.ProcessEnv, explicitDefault?: boolean }} [options]
   */
  constructor(defaultWorkspace = null, options = {}) {
    this.env = options.env || process.env;
    const baseConfigDir = StudioStateStore.resolveConfigDir(this.env);
    this.configPath = this.env.FLOW_WORKSPACES_CONFIG
      ? path.resolve(this.env.FLOW_WORKSPACES_CONFIG)
      : path.join(baseConfigDir, "workspaces.json");
    this.recentWorkspacesPath = this.env.FLOW_RECENT_WORKSPACES_FILE
      ? path.resolve(this.env.FLOW_RECENT_WORKSPACES_FILE)
      : path.join(path.dirname(this.configPath), "recent-workspaces.tsv");
    this.stateStore = new StudioStateStore({ env: this.env });

    const resolvedDefault = defaultWorkspace ? uriToWorkspacePath(defaultWorkspace) : null;
    const allowDefault =
      resolvedDefault && (options.explicitDefault || !isInternalSidecarPath(resolvedDefault));
    this.defaultWorkspace = allowDefault ? resolvedDefault : null;
    /** @type {Set<string>} */
    this.runtimeWorkspaces = new Set();
    if (this.defaultWorkspace && isExistingDir(this.defaultWorkspace)) {
      this.runtimeWorkspaces.add(this.defaultWorkspace);
    }
    /** @type {string | null} */
    this.lastActiveWorkspace = null;
    /** @type {string | null} */
    this.lastActiveUpdatedAt = null;
  }

  getLastActiveWorkspace() {
    const { diskActiveWorkspace, diskUpdatedAt } = this.#readDiskState();
    if (this.lastActiveWorkspace && isExistingDir(this.lastActiveWorkspace)) {
      const diskMs = parseIsoMs(diskUpdatedAt);
      const memMs = parseIsoMs(this.lastActiveUpdatedAt);
      if (diskActiveWorkspace && diskMs > 0 && (memMs === 0 || diskMs > memMs)) {
        this.lastActiveWorkspace = diskActiveWorkspace;
        this.lastActiveUpdatedAt = diskUpdatedAt;
      }
      return this.lastActiveWorkspace;
    }
    if (diskActiveWorkspace) {
      this.lastActiveWorkspace = diskActiveWorkspace;
      this.lastActiveUpdatedAt = diskUpdatedAt;
      return diskActiveWorkspace;
    }
    if (this.defaultWorkspace && isExistingDir(this.defaultWorkspace)) return this.defaultWorkspace;
    return this.listWorkspaces()[0] || null;
  }

  listWorkspaces() {
    const { diskWorkspaces, diskActiveWorkspace } = this.#readDiskState();
    const state = this.stateStore.load();
    /** @type {Set<string>} */
    const seen = new Set();
    const addCandidate = (candidate) => {
      if (!candidate) return;
      const resolved = uriToWorkspacePath(candidate);
      if (!resolved) return;
      if (resolved !== this.defaultWorkspace && isInternalSidecarPath(resolved)) return;
      if (isExistingDir(resolved)) seen.add(resolved);
    };

    addCandidate(this.lastActiveWorkspace);
    addCandidate(diskActiveWorkspace);
    for (const ws of state.pinnedWorkspaces) addCandidate(ws);
    for (const ws of this.runtimeWorkspaces) addCandidate(ws);
    for (const ws of diskWorkspaces) addCandidate(ws);
    addCandidate(this.defaultWorkspace);
    return Array.from(seen);
  }

  /**
   * @param {string} workspacePath
   * @param {{ setActive?: boolean, pinned?: boolean }} [options]
   */
  addWorkspace(workspacePath, options = {}) {
    const resolved = uriToWorkspacePath(workspacePath);
    if (!resolved || !isExistingDir(resolved)) {
      throw new Error(`Workspace directory does not exist: ${workspacePath}`);
    }
    if (resolved !== this.defaultWorkspace && isInternalSidecarPath(resolved)) {
      return this.listWorkspaces();
    }
    this.runtimeWorkspaces.add(resolved);
    if (options.setActive !== false) {
      this.lastActiveWorkspace = resolved;
      this.lastActiveUpdatedAt = new Date().toISOString();
    }
    if (typeof options.pinned === "boolean") {
      this.setPinned(resolved, options.pinned);
    }
    const list = this.listWorkspaces();
    this.#persist(list);
    return list;
  }

  /**
   * Pin or unpin a workspace so it remains visible across Studio restarts.
   *
   * @param {string} workspacePath
   * @param {boolean} pinned
   */
  setPinned(workspacePath, pinned = true) {
    const resolved = uriToWorkspacePath(workspacePath);
    if (!resolved) return [];
    const nextState = this.stateStore.update((s) => {
      const filtered = s.pinnedWorkspaces.filter((p) => p !== resolved);
      if (pinned) filtered.unshift(resolved);
      s.pinnedWorkspaces = filtered;
    });
    return nextState.pinnedWorkspaces;
  }

  listPinnedWorkspaces() {
    return this.stateStore.load().pinnedWorkspaces.filter((ws) => isExistingDir(ws));
  }

  /**
   * @param {string[]} [urisOrPaths]
   */
  recordActiveWorkspaces(urisOrPaths = []) {
    const valid = [];
    for (const item of urisOrPaths) {
      const resolved = uriToWorkspacePath(item);
      if (
        resolved &&
        isExistingDir(resolved) &&
        (resolved === this.defaultWorkspace || !isInternalSidecarPath(resolved))
      ) {
        valid.push(resolved);
      }
    }
    if (valid.length === 0) return [];
    for (let i = valid.length - 1; i >= 0; i -= 1) {
      this.runtimeWorkspaces.add(valid[i]);
    }
    this.lastActiveWorkspace = valid[0];
    this.lastActiveUpdatedAt = new Date().toISOString();
    this.#persist(this.listWorkspaces());
    return valid;
  }

  #persist(list) {
    try {
      const persistable = list.filter((ws) => !isTransientTestPathForConfig(ws, this.configPath));
      if (persistable.length === 0 && list.length > 0) return;
      const activeToPersist =
        this.lastActiveWorkspace && !isTransientTestPathForConfig(this.lastActiveWorkspace, this.configPath)
          ? this.lastActiveWorkspace
          : persistable[0] || null;
      writeJsonAtomic(this.configPath, {
        lastActiveWorkspace: activeToPersist,
        updatedAt: this.lastActiveUpdatedAt || new Date().toISOString(),
        workspaces: persistable,
      });
    } catch {
      // Retain in-memory workspaces when home config is read-only.
    }
  }

  #readDiskState() {
    const diskWorkspaces = [];
    let diskActiveWorkspace = null;
    let diskUpdatedAt = null;

    if (fs.existsSync(this.recentWorkspacesPath)) {
      try {
        const lines = fs
          .readFileSync(this.recentWorkspacesPath, "utf8")
          .split(/\r?\n/)
          .map((l) => l.trim())
          .filter(Boolean);
        for (let idx = lines.length - 1; idx >= 0; idx -= 1) {
          const line = lines[idx];
          const tabIdx = line.indexOf("\t");
          const ts = tabIdx > 0 ? line.slice(0, tabIdx).trim() : "";
          const rawPath = tabIdx > 0 ? line.slice(tabIdx + 1).trim() : line;
          const resolved = uriToWorkspacePath(rawPath);
          if (
            resolved &&
            isExistingDir(resolved) &&
            !isInternalSidecarPath(resolved) &&
            !isTransientTestPathForConfig(resolved, this.configPath)
          ) {
            if (!diskActiveWorkspace) {
              diskActiveWorkspace = resolved;
              diskUpdatedAt = ts || null;
            }
            if (!diskWorkspaces.includes(resolved)) diskWorkspaces.push(resolved);
          }
        }
      } catch {
        // Ignore unreadable recent-workspaces.tsv.
      }
    }

    const saved = readJsonSafe(this.configPath);
    if (saved && typeof saved === "object") {
      if (typeof saved.lastActiveWorkspace === "string" && saved.lastActiveWorkspace.trim()) {
        const resolvedSaved = uriToWorkspacePath(saved.lastActiveWorkspace);
        if (
          resolvedSaved &&
          isExistingDir(resolvedSaved) &&
          !isInternalSidecarPath(resolvedSaved) &&
          !isTransientTestPathForConfig(resolvedSaved, this.configPath)
        ) {
          const savedTs = typeof saved.updatedAt === "string" ? saved.updatedAt : "";
          const savedMs = parseIsoMs(savedTs);
          const diskMs = parseIsoMs(diskUpdatedAt);
          if (!diskActiveWorkspace || (savedMs > 0 && (diskMs === 0 || savedMs >= diskMs))) {
            diskActiveWorkspace = resolvedSaved;
            diskUpdatedAt = savedTs || diskUpdatedAt;
          }
          if (!diskWorkspaces.includes(resolvedSaved)) diskWorkspaces.unshift(resolvedSaved);
        }
      }
      if (Array.isArray(saved.workspaces)) {
        for (const raw of saved.workspaces) {
          const resolved = uriToWorkspacePath(raw);
          if (
            resolved &&
            isExistingDir(resolved) &&
            !isInternalSidecarPath(resolved) &&
            !isTransientTestPathForConfig(resolved, this.configPath) &&
            !diskWorkspaces.includes(resolved)
          ) {
            diskWorkspaces.push(resolved);
          }
        }
      }
    }

    return { diskWorkspaces, diskActiveWorkspace, diskUpdatedAt };
  }
}

/**
 * Inspects workspace manifests (`Makefile`, `pyproject.toml`, `package.json`) to recommend
 * tight, scoped permission grants stored in `.agents/workspace-permissions.json`.
 */
export class WorkspacePermissionAdvisor {
  /**
   * @param {string} raw
   */
  static parseGrant(raw) {
    if (typeof raw !== "string") return null;
    const m = raw.trim().match(/^([a-z_]+)\(([\s\S]*)\)$/);
    if (!m) return null;
    const action = m[1].trim();
    const target = m[2].trim();
    if (!action || !target) return null;
    return { action, target, grant: `${action}(${target})` };
  }

  /**
   * @param {string} raw
   * @returns {string | null}
   */
  static validateGrantSafety(raw) {
    const parsed = WorkspacePermissionAdvisor.parseGrant(raw);
    if (!parsed) return "Invalid grant syntax; expected action(target).";
    if (FORBIDDEN_GRANTS.has(parsed.grant)) return `Wildcard grant '${parsed.grant}' is blocked for safety.`;
    if (!["command", "mcp", "read_file", "write_file", "read_url"].includes(parsed.action)) {
      return `Unsupported grant action '${parsed.action}'.`;
    }
    if (parsed.action === "command") {
      const norm = parsed.target.replace(/\s+/g, " ").trim();
      if (DANGEROUS_COMMAND_TARGETS.has(norm) || norm === "*" || norm.startsWith("regex:.*")) {
        return `Overly broad command grant '${parsed.grant}' is blocked.`;
      }
      if (/[`;]|(?:\$\()/.test(norm)) return `Shell metacharacters are forbidden in '${parsed.grant}'.`;
    }
    if ((parsed.action === "read_file" || parsed.action === "write_file") && ["/", "~", "*"].includes(parsed.target)) {
      return `Root filesystem path '${parsed.grant}' is blocked.`;
    }
    if (parsed.action === "mcp" && (!parsed.target.includes("/") || parsed.target === "*/*")) {
      return `MCP grant '${parsed.grant}' must name a specific server.`;
    }
    if (parsed.action === "read_url" && (parsed.target === "*" || parsed.target.includes("*"))) {
      return `URL grant '${parsed.grant}' must name a concrete hostname.`;
    }
    return null;
  }

  /**
   * @param {string} workspaceRoot
   */
  constructor(workspaceRoot) {
    this.workspace = path.resolve(workspaceRoot);
    this.policyPath = path.join(this.workspace, ".agents", "workspace-permissions.json");
    this.hooksJsonPath = path.join(this.workspace, ".agents", "hooks.json");
    this.hookScriptPath = path.join(this.workspace, ".agents", "workspace-permissions-hook.mjs");
  }

  inspect() {
    const policy = readJsonSafe(this.policyPath);
    const allow = Array.isArray(policy?.allow) ? policy.allow.map(String) : [];
    const deny = Array.isArray(policy?.deny) ? policy.deny.map(String) : [];
    const hooksData = readJsonSafe(this.hooksJsonPath);
    const hookEnabled = Boolean(hooksData?.[HOOK_KEY]?.PreToolUse?.length && fs.existsSync(this.hookScriptPath));
    const recommendations = this.#scanRecommendations(new Set(allow));
    return {
      workspace: this.workspace,
      policy_exists: Boolean(policy),
      mode: policy?.mode || "disabled",
      hook_enabled: hookEnabled,
      allow,
      deny,
      recommendations,
    };
  }

  /**
   * @param {{ allowGrants?: string[], denyGrants?: string[], enableHook?: boolean }} params
   */
  apply({ allowGrants = [], denyGrants = [], enableHook = false } = {}) {
    const cleanAllow = [];
    for (const g of allowGrants) {
      const err = WorkspacePermissionAdvisor.validateGrantSafety(g);
      if (err) throw new Error(err);
      const parsed = WorkspacePermissionAdvisor.parseGrant(g);
      if (parsed && !cleanAllow.includes(parsed.grant)) cleanAllow.push(parsed.grant);
    }
    const cleanDeny = denyGrants.map((g) => String(g || "").trim()).filter(Boolean);
    writeJsonAtomic(this.policyPath, {
      version: 1,
      mode: enableHook ? "allowlist" : "advisory",
      updatedAt: new Date().toISOString(),
      allow: cleanAllow,
      deny: cleanDeny,
    });

    if (enableHook) {
      writeTextAtomic(
        this.hookScriptPath,
        [
          'import fs from "node:fs";',
          'import path from "node:path";',
          "let payload = {};",
          'try { payload = JSON.parse(fs.readFileSync(0, "utf8") || "{}"); } catch {}',
          'const tool = payload.toolCall?.name || payload.tool_name || "";',
          'const cmd = String(payload.toolCall?.input?.CommandLine || payload.tool_input?.command || "").trim();',
          'const ws = payload.workspacePaths?.[0] || payload.cwd || process.cwd();',
          'let allow = [];',
          'try { allow = JSON.parse(fs.readFileSync(path.join(ws, ".agents", "workspace-permissions.json"), "utf8")).allow || []; } catch {}',
          'if ((tool === "run_command" || tool === "Bash") && cmd && allow.includes(`command(${cmd.split(/\\s+/).slice(0, 2).join(" ")})`)) {',
          '  process.stdout.write(JSON.stringify({ decision: "allow" }) + "\\n");',
          "} else {",
          '  process.stdout.write("{}\\n");',
          "}",
          "",
        ].join("\n"),
      );
      const existingHooks = readJsonSafe(this.hooksJsonPath) || {};
      existingHooks[HOOK_KEY] = {
        PreToolUse: [
          {
            matcher: HOOK_MATCHER,
            hooks: [{ type: "command", command: "node .agents/workspace-permissions-hook.mjs", timeout: 5 }],
          },
        ],
      };
      writeJsonAtomic(this.hooksJsonPath, existingHooks);
    }
    return this.inspect();
  }

  #scanRecommendations(existingAllow) {
    /** @type {Map<string, any>} */
    const rules = new Map();
    const addRule = (grant, category, source, reason) => {
      if (WorkspacePermissionAdvisor.validateGrantSafety(grant)) return;
      const parsed = WorkspacePermissionAdvisor.parseGrant(grant);
      if (!parsed) return;
      rules.set(parsed.grant, {
        id: `perm-${sha256Hex(parsed.grant).slice(0, 10)}`,
        grant: parsed.grant,
        action: parsed.action,
        target: parsed.target,
        category,
        source,
        reason,
        selected: existingAllow.has(parsed.grant),
      });
    };

    const makefile = readTextSafe(path.join(this.workspace, "Makefile"));
    if (makefile) {
      for (const m of makefile.matchAll(/^([a-zA-Z0-9_-]+)\s*:/gm)) {
        if (SAFE_MAKE_TARGET_RE.test(m[1])) {
          addRule(`command(make ${m[1]})`, "build", "Makefile", `Run safe Makefile target '${m[1]}'`);
        }
      }
    }

    const pkg = readJsonSafe(path.join(this.workspace, "package.json"));
    if (pkg?.scripts && typeof pkg.scripts === "object") {
      for (const name of Object.keys(pkg.scripts)) {
        if (SAFE_NPM_SCRIPT_RE.test(name)) {
          addRule(`command(npm run ${name})`, "test", "package.json", `Run safe npm script '${name}'`);
        }
      }
    }

    if (fs.existsSync(path.join(this.workspace, "pyproject.toml"))) {
      addRule("command(uv run pytest)", "test", "pyproject.toml", "Execute Python unit tests via uv");
      addRule("command(uv run ruff)", "lint", "pyproject.toml", "Run ruff lint checks");
      addRule("command(uv run mypy)", "lint", "pyproject.toml", "Run mypy type checks");
    }

    return Array.from(rules.values());
  }
}
