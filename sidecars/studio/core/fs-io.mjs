/**
 * Shared filesystem helpers, parse memo, single-file Studio state store,
 * and runtime telemetry utilities for Flow Studio and cross-harness adapters.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const IS_WIN = process.platform === "win32";
const LIVE_STATE_TTL_MS = 10 * 60 * 1000;
const KNOWN_CLAIM_HARNESSES = new Set(["agy", "claude", "codex", "cursor", "opencode", "vscode", "cli"]);
const CLOSED_STATES = new Set(["completed", "closed", "deferred", "skipped"]);

/**
 * Resolve the executable path of `binaryName` on `PATH` without spawning a shell.
 *
 * @param {string} binaryName
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string | null}
 */
export function whichSync(binaryName, env = process.env) {
  if (!binaryName) return null;
  if (path.isAbsolute(binaryName)) {
    try {
      return fs.statSync(binaryName).isFile() ? binaryName : null;
    } catch {
      return null;
    }
  }
  const pathEnv = env.PATH || "";
  const pathSep = IS_WIN ? ";" : ":";
  const exts = IS_WIN
    ? (env.PATHEXT || ".EXE;.CMD;.BAT").split(";").map((e) => e.toLowerCase())
    : [""];

  for (const rawDir of pathEnv.split(pathSep)) {
    const dir = rawDir.trim();
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(
        dir,
        ext && !binaryName.toLowerCase().endsWith(ext) ? `${binaryName}${ext}` : binaryName,
      );
      try {
        if (fs.statSync(candidate).isFile()) return candidate;
      } catch {
        // Ignore missing candidate paths.
      }
    }
  }
  return null;
}

/**
 * Resolve a working Node.js executable, falling back through Volta/nvm/Homebrew if `PATH` is minimal.
 *
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string}
 */
export function resolveNodeBinary(env = process.env) {
  const fromPath = whichSync("node", env);
  if (fromPath) return fromPath;
  const home = env.HOME || env.USERPROFILE || os.homedir();
  const candidates = [
    path.join(home, ".volta", "bin", IS_WIN ? "node.exe" : "node"),
    "/opt/homebrew/bin/node",
    "/usr/local/bin/node",
    "/usr/bin/node",
  ];
  for (const cand of candidates) {
    try {
      if (fs.existsSync(cand) && fs.statSync(cand).isFile()) return cand;
    } catch {
      // Ignore unreadable candidates.
    }
  }
  return process.execPath || "node";
}

/**
 * Compute lowercase hexadecimal SHA-1 digest.
 *
 * @param {string | Buffer} input
 * @returns {string}
 */
export function sha1Hex(input) {
  return crypto.createHash("sha1").update(input).digest("hex");
}

/**
 * Compute lowercase hexadecimal SHA-256 digest.
 *
 * @param {string | Buffer} input
 * @returns {string}
 */
export function sha256Hex(input) {
  return crypto.createHash("sha256").update(input).digest("hex");
}

/**
 * Read a UTF-8 text file safely with CRLF normalization, returning `null` on failure.
 *
 * @param {string} filePath
 * @returns {string | null}
 */
export function readTextSafe(filePath) {
  try {
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return null;
    return fs.readFileSync(filePath, "utf8").replace(/\r\n/g, "\n");
  } catch {
    return null;
  }
}

/**
 * Read and parse JSON safely, returning `null` if missing or invalid.
 *
 * @param {string} filePath
 * @returns {any}
 */
export function readJsonSafe(filePath) {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return null;
  }
}

/**
 * Atomically write text to `filePath` using a sibling temp file and rename.
 *
 * @param {string} filePath
 * @param {string} content
 */
export function writeTextAtomic(filePath, content) {
  const target = path.resolve(filePath);
  const dir = path.dirname(target);
  fs.mkdirSync(dir, { recursive: true });
  const tmpPath = path.join(dir, `.${path.basename(target)}.${process.pid}.${crypto.randomBytes(4).toString("hex")}.tmp`);
  try {
    fs.writeFileSync(tmpPath, content, "utf8");
    fs.renameSync(tmpPath, target);
  } catch (err) {
    try {
      fs.rmSync(tmpPath, { force: true });
    } catch {
      // Ignore temp cleanup failures.
    }
    throw err;
  }
}

/**
 * Atomically write JSON with trailing newline.
 *
 * @param {string} filePath
 * @param {any} data
 * @param {number} [indent]
 */
export function writeJsonAtomic(filePath, data, indent = 2) {
  writeTextAtomic(filePath, `${JSON.stringify(data, null, indent)}\n`);
}

/**
 * Return true if `dirPath` exists and is a directory.
 *
 * @param {string} dirPath
 * @returns {boolean}
 */
export function isExistingDir(dirPath) {
  try {
    return Boolean(dirPath) && fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory();
  } catch {
    return false;
  }
}

/**
 * Confine a relative path strictly inside `rootDir`.
 *
 * @param {string} rootDir
 * @param {string} relPath
 * @returns {string}
 */
export function resolveConfinedPath(rootDir, relPath) {
  const root = path.resolve(rootDir);
  const candidate = path.resolve(root, String(relPath || ""));
  const rel = path.relative(root, candidate);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`Path escapes workspace root: ${relPath}`);
  }
  return candidate;
}

/**
 * Normalize a workspace-relative POSIX path after confinement check.
 *
 * @param {string} rootDir
 * @param {string} relPath
 * @returns {string}
 */
export function normalizeRelPath(rootDir, relPath) {
  const target = resolveConfinedPath(rootDir, relPath);
  return path.relative(path.resolve(rootDir), target).split(path.sep).join("/");
}

/**
 * Convert `absPath` relative to `baseDir` with POSIX `/` separators.
 *
 * @param {string} baseDir
 * @param {string} absPath
 * @returns {string}
 */
export function toPosixRelative(baseDir, absPath) {
  return path.relative(path.resolve(baseDir), path.resolve(absPath)).split(path.sep).join("/");
}

/**
 * Deterministically walk Markdown files inside `dir`.
 *
 * @param {string} dir
 * @param {{ excludeDirs?: Set<string> }} [options]
 * @returns {string[]}
 */
export function walkMarkdownFiles(dir, { excludeDirs = new Set(["node_modules", ".git", ".venv", "__pycache__"]) } = {}) {
  if (!isExistingDir(dir)) return [];
  /** @type {string[]} */
  const out = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
  for (const ent of entries) {
    if (ent.name.startsWith(".") && ent.name !== ".agents") continue;
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      if (!excludeDirs.has(ent.name)) {
        out.push(...walkMarkdownFiles(full, { excludeDirs }));
      }
    } else if (ent.isFile() && ent.name.toLowerCase().endsWith(".md")) {
      out.push(full);
    }
  }
  return out;
}

/**
 * Derive deterministic `<repo_name>-<hash8>` workspace identifier matching Python `CatalogService`.
 *
 * @param {string} workspaceRoot
 * @returns {string}
 */
export function deriveWorkspaceId(workspaceRoot) {
  const resolved = path.resolve(workspaceRoot);
  const hash8 = sha256Hex(resolved).slice(0, 8);
  const safeName =
    path
      .basename(resolved)
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/^-+|-+$/g, "") || "workspace";
  return `${safeName}-${hash8}`;
}

/**
 * Convert a `file://` URI or filesystem path into a resolved directory path.
 *
 * @param {string | null | undefined} uriOrPath
 * @returns {string | null}
 */
export function uriToWorkspacePath(uriOrPath) {
  if (typeof uriOrPath !== "string") return null;
  const raw = uriOrPath.trim();
  if (!raw) return null;
  if (raw.startsWith("file:")) {
    try {
      return path.resolve(fileURLToPath(raw));
    } catch {
      const stripped = decodeURIComponent(raw.replace(/^file:\/\//i, ""));
      return stripped ? path.resolve(stripped) : null;
    }
  }
  return path.resolve(raw);
}

/**
 * Return true if `dirPath` is an internal sidecar or plugin cache directory.
 *
 * @param {string} dirPath
 * @returns {boolean}
 */
export function isInternalSidecarPath(dirPath) {
  const normalized = path.resolve(dirPath).replace(/\\/g, "/").replace(/\/+$/, "");
  if (normalized.endsWith("/sidecars/studio")) return true;
  if (normalized.includes("/.gemini/config/plugins/")) return true;
  if (normalized.includes("/.claude/plugins/cache/")) return true;
  return false;
}

/**
 * Return true if `dirPath` is a transient pytest temp directory while config is non-pytest.
 *
 * @param {string} dirPath
 * @param {string} [configPath]
 * @returns {boolean}
 */
export function isTransientTestPathForConfig(dirPath, configPath = "") {
  const normalized = path.resolve(dirPath).replace(/\\/g, "/");
  const normalizedCfg = String(configPath || "").replace(/\\/g, "/");
  return !normalizedCfg.includes("/pytest-of-") && normalized.includes("/pytest-of-");
}

/**
 * Parse ISO-8601 timestamp into epoch milliseconds (or 0 when invalid).
 *
 * @param {string | null | undefined} ts
 * @returns {number}
 */
export function parseIsoMs(ts) {
  if (typeof ts !== "string" || !ts.trim()) return 0;
  const ms = Date.parse(ts);
  return Number.isFinite(ms) ? ms : 0;
}

/**
 * Return the ephemeral runtime directory base (`FLOW_RUNTIME_DIR` or `$TMPDIR/flow-runtime`).
 *
 * @param {Record<string, string | undefined>} [env]
 * @returns {string}
 */
export function runtimeBaseDir(env = process.env) {
  const explicit = String(env.FLOW_RUNTIME_DIR || "").trim().replace(/[/\\]+$/, "");
  if (explicit) return explicit;
  const rawTmp = String(env.TMPDIR || "").trim().replace(/[/\\]+$/, "") || os.tmpdir().replace(/[/\\]+$/, "") || "/tmp";
  return path.join(rawTmp, "flow-runtime");
}

/**
 * Derive sanitized workspace runtime directory key matching hooks and workflows.
 *
 * @param {string} workspacePath
 * @returns {string}
 */
export function workspaceRuntimeId(workspacePath) {
  const norm = String(workspacePath || "").replace(/\\/g, "/").replace(/\/+$/, "");
  const cleaned = norm.replace(/[^A-Za-z0-9._-]/g, "_");
  const tail = cleaned.length > 120 ? cleaned.slice(cleaned.length - 120) : cleaned;
  return tail || "default";
}

/**
 * Read live telemetry heartbeat from the workspace runtime directory with legacy `.agents/` fallback.
 *
 * @param {string} workspaceRoot
 * @param {{ agentsDir?: string, env?: Record<string, string | undefined>, nowMs?: number }} [options]
 */
export function readStudioLiveState(workspaceRoot, { agentsDir, env = process.env, nowMs = Date.now() } = {}) {
  const rtBase = runtimeBaseDir(env);
  const wsId = workspaceRuntimeId(workspaceRoot);
  const candidates = [path.join(rtBase, wsId, "studio-live-state.json")];
  if (agentsDir) candidates.push(path.join(agentsDir, "studio-live-state.json"));
  const localLegacy = path.join(path.resolve(workspaceRoot), ".agents", "studio-live-state.json");
  if (!candidates.includes(localLegacy)) candidates.push(localLegacy);

  for (const stateFile of candidates) {
    let stat;
    try {
      stat = fs.statSync(stateFile);
    } catch {
      continue;
    }
    if (!stat.isFile()) continue;
    const raw = readJsonSafe(stateFile);
    if (!raw || typeof raw !== "object") continue;

    const updatedIso =
      typeof raw.updatedAt === "string" && raw.updatedAt.trim() ? raw.updatedAt.trim() : stat.mtime.toISOString();
    const updatedMs = Date.parse(updatedIso);
    const effectiveMs = Number.isFinite(updatedMs) ? updatedMs : stat.mtimeMs;
    const ageMs = nowMs - effectiveMs;
    const fresh = Number.isFinite(ageMs) && ageMs <= LIVE_STATE_TTL_MS;

    return {
      ...raw,
      v: typeof raw.v === "number" ? raw.v : 1,
      updatedAt: updatedIso,
      fresh,
      activeTurn: Boolean(raw.activeTurn) && fresh,
      sourcePath: stateFile,
    };
  }
  return null;
}

/**
 * Parse structured `<harness>:<session_id>[:<role>]` or legacy claim string.
 *
 * @param {unknown} raw
 */
export function parseClaimIdentity(raw) {
  if (typeof raw !== "string") return null;
  const text = raw.trim().replace(/^['"]|['"]$/g, "");
  if (!text || text === "null") return null;
  const parts = text.split(":").map((part) => part.trim());
  if (parts.length >= 2 && KNOWN_CLAIM_HARNESSES.has(parts[0].toLowerCase()) && parts[1]) {
    return {
      raw: text,
      structured: true,
      harness: parts[0].toLowerCase(),
      sessionId: parts[1],
      role: parts.slice(2).join(":") || null,
    };
  }
  return {
    raw: text,
    structured: false,
    harness: null,
    sessionId: null,
    role: parts.length >= 2 ? parts.slice(1).join(":") : text,
  };
}

/**
 * Map a task/chapter state string to its checklist box character.
 *
 * @param {string} state
 * @returns {string}
 */
export function expectedMarkerForState(state) {
  const s = String(state || "").trim().toLowerCase();
  if (s === "completed" || s === "closed") return "x";
  if (s === "in_progress" || s === "active") return "~";
  if (s === "blocked") return "!";
  if (s === "deferred" || s === "skipped") return "-";
  return " ";
}

/**
 * Map a checklist character back to canonical task state.
 *
 * @param {string} marker
 * @returns {string}
 */
export function stateFromChecklistMarker(marker) {
  const m = String(marker || "").toLowerCase();
  if (m === "x") return "completed";
  if (m === "~") return "in_progress";
  if (m === "!") return "blocked";
  if (m === "-") return "skipped";
  return "pending";
}

/**
 * Return true if `state` represents a finished/closed item.
 *
 * @param {string | null | undefined} state
 * @returns {boolean}
 */
export function isClosedState(state) {
  return CLOSED_STATES.has(String(state || "").trim().toLowerCase());
}

/**
 * Bounded `(path, mtimeMs, size)` in-memory parse memo avoiding SQLite lock overhead.
 */
export class ParseMemo {
  /**
   * @param {number} [maxEntries]
   */
  constructor(maxEntries = 1024) {
    this.maxEntries = maxEntries;
    /** @type {Map<string, { mtimeMs: number, size: number, value: any }>} */
    this.cache = new Map();
  }

  /**
   * @template T
   * @param {string} filePath
   * @param {(rawText: string) => T} parser
   * @returns {T | null}
   */
  readAndParse(filePath, parser) {
    let stat;
    try {
      stat = fs.statSync(filePath);
    } catch {
      this.cache.delete(filePath);
      return null;
    }
    if (!stat.isFile()) return null;
    const hit = this.cache.get(filePath);
    if (hit && hit.mtimeMs === stat.mtimeMs && hit.size === stat.size) {
      this.cache.delete(filePath);
      this.cache.set(filePath, hit);
      return hit.value;
    }
    const raw = fs.readFileSync(filePath, "utf8").replace(/\r\n/g, "\n");
    const value = parser(raw);
    this.cache.set(filePath, { mtimeMs: stat.mtimeMs, size: stat.size, value });
    if (this.cache.size > this.maxEntries) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey !== undefined) this.cache.delete(oldestKey);
    }
    return value;
  }

  invalidate(prefix = "") {
    if (!prefix) {
      this.cache.clear();
      return;
    }
    for (const k of this.cache.keys()) {
      if (k.startsWith(prefix)) this.cache.delete(k);
    }
  }
}

export const sharedParseMemo = new ParseMemo();

/**
 * Atomic single-file JSON store under `~/.config/flow/studio-state.json`
 * persisting pinned workspaces, UI preferences, `models.dev` SWR snapshots, and 429 cooldowns.
 */
export class StudioStateStore {
  /**
   * @param {{ env?: NodeJS.ProcessEnv, statePath?: string }} [options]
   */
  constructor({ env = process.env, statePath = null } = {}) {
    this.env = env;
    this.configDir = StudioStateStore.resolveConfigDir(env);
    this.statePath = statePath
      ? path.resolve(statePath)
      : env.FLOW_STUDIO_STATE_FILE
        ? path.resolve(env.FLOW_STUDIO_STATE_FILE)
        : path.join(this.configDir, "studio-state.json");
  }

  /**
   * @param {NodeJS.ProcessEnv} [env]
   * @returns {string}
   */
  static resolveConfigDir(env = process.env) {
    if (env.FLOW_CONFIG_DIR) return path.resolve(env.FLOW_CONFIG_DIR);
    if (env.XDG_CONFIG_HOME) return path.join(path.resolve(env.XDG_CONFIG_HOME), "flow");
    return path.join(os.homedir(), ".config", "flow");
  }

  load() {
    const raw = readJsonSafe(this.statePath);
    const data = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
    return {
      version: 1,
      studioHome: data.studioHome !== false,
      lastActiveWorkspace: typeof data.lastActiveWorkspace === "string" ? data.lastActiveWorkspace : null,
      updatedAt: typeof data.updatedAt === "string" ? data.updatedAt : null,
      pinnedWorkspaces: Array.isArray(data.pinnedWorkspaces) ? data.pinnedWorkspaces.map(String) : [],
      workspaces: Array.isArray(data.workspaces) ? data.workspaces.map(String) : [],
      modelCooldowns:
        data.modelCooldowns && typeof data.modelCooldowns === "object" ? data.modelCooldowns : {},
      modelsDevSnapshot:
        data.modelsDevSnapshot && typeof data.modelsDevSnapshot === "object" ? data.modelsDevSnapshot : null,
      modelsDevFetchedAt: typeof data.modelsDevFetchedAt === "string" ? data.modelsDevFetchedAt : null,
      probeCache: data.probeCache && typeof data.probeCache === "object" ? data.probeCache : {},
    };
  }

  /**
   * @param {(draft: ReturnType<StudioStateStore["load"]>) => void} mutator
   */
  update(mutator) {
    const state = this.load();
    mutator(state);
    state.updatedAt = new Date().toISOString();
    try {
      writeJsonAtomic(this.statePath, state, 2);
    } catch {
      // Sandboxed read-only $HOME environments retain state in memory for the current run.
    }
    return state;
  }

  /**
   * Record a temporary cooldown window for `(harness, model, effort)` after 429 / capacity errors.
   *
   * @param {{ harness: string, model: string, effort?: string, reason?: string, ttlMs?: number, nowMs?: number }} params
   */
  recordCooldown({ harness, model, effort = "default", reason = "rate_limit", ttlMs = 180000, nowMs = Date.now() }) {
    const key = `${String(harness || "").toLowerCase()}:${model}:${effort || "default"}`;
    const untilMs = nowMs + Math.max(5000, Number(ttlMs) || 180000);
    return this.update((s) => {
      s.modelCooldowns[key] = {
        harness: String(harness || "").toLowerCase(),
        model,
        effort: effort || "default",
        reason,
        untilIso: new Date(untilMs).toISOString(),
        untilMs,
      };
    });
  }

  /**
   * Return active `[0, 1]` availability penalty factor (0 when cooling down, 1 when clear).
   *
   * @param {string} harness
   * @param {string} model
   * @param {string} [effort]
   * @param {number} [nowMs]
   */
  getAvailabilityFactor(harness, model, effort = "default", nowMs = Date.now()) {
    const state = this.load();
    const exactKey = `${String(harness || "").toLowerCase()}:${model}:${effort || "default"}`;
    const baseKey = `${String(harness || "").toLowerCase()}:${model}:default`;
    const hit = state.modelCooldowns[exactKey] || state.modelCooldowns[baseKey];
    if (!hit || !Number.isFinite(Number(hit.untilMs))) return 1.0;
    if (nowMs >= Number(hit.untilMs)) return 1.0;
    return 0.05;
  }
}
