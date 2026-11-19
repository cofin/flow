/**
 * @fileoverview Local SQLite (`node:sqlite` WAL) cache with automatic atomic JSON
 * fallback (`studio-cache.json`) shared across Flow CLI and Flow Studio.
 */

import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

import {
  readJsonSafe,
  safeStat,
  sha1Parts,
  StudioStateStore,
  writeJsonAtomic,
} from "./fs-io.mjs";

const SCHEMA_VERSION = 1;
const SHARED_INSTANCES = new Map();
let cachedSqliteModule;

function loadNodeSqliteSync() {
  if (cachedSqliteModule !== undefined) {
    return cachedSqliteModule;
  }
  const origEmitWarning = process.emitWarning;
  process.emitWarning = function filteredEmitWarning(warning, ...rest) {
    const msg = typeof warning === "string" ? warning : String(warning?.message || "");
    if (msg.includes("SQLite")) return undefined;
    return origEmitWarning.call(process, warning, ...rest);
  };
  try {
    const req = createRequire(import.meta.url);
    const mod = req("node:sqlite");
    cachedSqliteModule = mod && typeof mod.DatabaseSync === "function" ? mod : null;
  } catch {
    cachedSqliteModule = null;
  } finally {
    process.emitWarning = origEmitWarning;
  }
  return cachedSqliteModule;
}

/**
 * Persistent SQLite WAL cache with automatic atomic JSON fallback for parsed files,
 * workspace bundle summaries, Git metadata, and multi-branch spec scans.
 */
export class StudioCacheStore {
  static shared({ dataDir = null, env = process.env } = {}) {
    const resolvedDir = dataDir ? path.resolve(dataDir) : StudioStateStore.resolveConfigDir(env);
    const forceJson = String(env.FLOW_FORCE_JSON_CACHE || "") === "1";
    const key = `${resolvedDir}::${forceJson ? "json" : "auto"}`;
    let existing = SHARED_INSTANCES.get(key);
    if (!existing || existing.closed) {
      existing = new StudioCacheStore({ dataDir: resolvedDir, env, forceJson });
      SHARED_INSTANCES.set(key, existing);
    }
    return existing;
  }

  constructor({ dataDir = null, env = process.env, forceJson = false } = {}) {
    this.env = env;
    this.dataDir = dataDir ? path.resolve(dataDir) : StudioStateStore.resolveConfigDir(env);
    this.forceJson = Boolean(forceJson || String(env.FLOW_FORCE_JSON_CACHE || "") === "1");
    this.closed = false;
    this._db = null;
    this._stmts = {};
    this._jsonState = null;
    this._jsonDirty = false;
    this.sqlitePath = path.join(this.dataDir, "studio-cache.sqlite");
    this.jsonPath = path.join(this.dataDir, "studio-cache.json");
    this.backend = this.#initBackend();
  }

  get storagePath() {
    return this.backend === "sqlite" ? this.sqlitePath : this.jsonPath;
  }

  #initBackend() {
    try {
      fs.mkdirSync(this.dataDir, { recursive: true });
    } catch {
      return "memory";
    }
    if (!this.forceJson) {
      const sqlite = loadNodeSqliteSync();
      if (sqlite && this.#openSqlite(sqlite)) {
        return "sqlite";
      }
    }
    this.#loadJsonFallback();
    return "json";
  }

  #openSqlite(sqlite) {
    const tryOpen = () => {
      const db = new sqlite.DatabaseSync(this.sqlitePath);
      try {
        fs.chmodSync(this.sqlitePath, 0o600);
      } catch {
        // Non-POSIX filesystems ignore chmod.
      }
      db.exec("PRAGMA journal_mode = WAL;");
      db.exec("PRAGMA synchronous = NORMAL;");
      db.exec("PRAGMA busy_timeout = 3000;");
      db.exec("PRAGMA temp_store = MEMORY;");
      const verRow = db.prepare("PRAGMA user_version;").get();
      const currentVer = Number(verRow?.user_version || 0);
      if (currentVer !== SCHEMA_VERSION) {
        db.exec(`
          DROP TABLE IF EXISTS kv_state;
          DROP TABLE IF EXISTS file_cache;
          DROP TABLE IF EXISTS workspace_cache;
          DROP TABLE IF EXISTS git_meta_cache;
        `);
        db.exec(`PRAGMA user_version = ${SCHEMA_VERSION};`);
      }
      db.exec(`
        CREATE TABLE IF NOT EXISTS kv_state (
          namespace TEXT NOT NULL,
          key TEXT NOT NULL,
          value_json TEXT NOT NULL,
          updated_at_ms INTEGER NOT NULL,
          expires_at_ms INTEGER,
          PRIMARY KEY (namespace, key)
        );
        CREATE TABLE IF NOT EXISTS file_cache (
          file_path TEXT NOT NULL,
          kind TEXT NOT NULL,
          mtime_ms REAL NOT NULL,
          size_bytes INTEGER NOT NULL,
          payload_json TEXT NOT NULL,
          updated_at_ms INTEGER NOT NULL,
          PRIMARY KEY (file_path, kind)
        );
        CREATE TABLE IF NOT EXISTS workspace_cache (
          workspace TEXT NOT NULL,
          kind TEXT NOT NULL,
          fingerprint TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          updated_at_ms INTEGER NOT NULL,
          PRIMARY KEY (workspace, kind)
        );
        CREATE TABLE IF NOT EXISTS git_meta_cache (
          workspace TEXT PRIMARY KEY,
          fingerprint TEXT NOT NULL,
          payload_json TEXT NOT NULL,
          updated_at_ms INTEGER NOT NULL
        );
      `);
      this._db = db;
      this._stmts = {
        getKv: db.prepare("SELECT value_json, updated_at_ms, expires_at_ms FROM kv_state WHERE namespace = ? AND key = ?"),
        setKv: db.prepare(`
          INSERT INTO kv_state (namespace, key, value_json, updated_at_ms, expires_at_ms)
          VALUES (?, ?, ?, ?, ?)
          ON CONFLICT(namespace, key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at_ms = excluded.updated_at_ms,
            expires_at_ms = excluded.expires_at_ms
        `),
        delKv: db.prepare("DELETE FROM kv_state WHERE namespace = ? AND key = ?"),
        getFile: db.prepare("SELECT mtime_ms, size_bytes, payload_json FROM file_cache WHERE file_path = ? AND kind = ?"),
        setFile: db.prepare(`
          INSERT INTO file_cache (file_path, kind, mtime_ms, size_bytes, payload_json, updated_at_ms)
          VALUES (?, ?, ?, ?, ?, ?)
          ON CONFLICT(file_path, kind) DO UPDATE SET
            mtime_ms = excluded.mtime_ms,
            size_bytes = excluded.size_bytes,
            payload_json = excluded.payload_json,
            updated_at_ms = excluded.updated_at_ms
        `),
        delFilePrefix: db.prepare("DELETE FROM file_cache WHERE file_path LIKE ?"),
        getWs: db.prepare("SELECT fingerprint, payload_json, updated_at_ms FROM workspace_cache WHERE workspace = ? AND kind = ?"),
        setWs: db.prepare(`
          INSERT INTO workspace_cache (workspace, kind, fingerprint, payload_json, updated_at_ms)
          VALUES (?, ?, ?, ?, ?)
          ON CONFLICT(workspace, kind) DO UPDATE SET
            fingerprint = excluded.fingerprint,
            payload_json = excluded.payload_json,
            updated_at_ms = excluded.updated_at_ms
        `),
        delWs: db.prepare("DELETE FROM workspace_cache WHERE workspace = ?"),
        getGit: db.prepare("SELECT fingerprint, payload_json FROM git_meta_cache WHERE workspace = ?"),
        setGit: db.prepare(`
          INSERT INTO git_meta_cache (workspace, fingerprint, payload_json, updated_at_ms)
          VALUES (?, ?, ?, ?)
          ON CONFLICT(workspace) DO UPDATE SET
            fingerprint = excluded.fingerprint,
            payload_json = excluded.payload_json,
            updated_at_ms = excluded.updated_at_ms
        `),
      };
      return true;
    };

    try {
      return tryOpen();
    } catch {
      try {
        for (const suffix of ["", "-wal", "-shm"]) {
          const p = `${this.sqlitePath}${suffix}`;
          if (fs.existsSync(p)) fs.unlinkSync(p);
        }
        return tryOpen();
      } catch {
        this._db = null;
        this._stmts = {};
        return false;
      }
    }
  }

  #loadJsonFallback() {
    const parsed = readJsonSafe(this.jsonPath);
    if (!parsed || typeof parsed !== "object" || parsed.version !== SCHEMA_VERSION) {
      this._jsonState = { version: SCHEMA_VERSION, kv_state: {}, file_cache: {}, workspace_cache: {}, git_meta_cache: {} };
      return;
    }
    this._jsonState = {
      version: SCHEMA_VERSION,
      kv_state: parsed.kv_state && typeof parsed.kv_state === "object" ? parsed.kv_state : {},
      file_cache: parsed.file_cache && typeof parsed.file_cache === "object" ? parsed.file_cache : {},
      workspace_cache: parsed.workspace_cache && typeof parsed.workspace_cache === "object" ? parsed.workspace_cache : {},
      git_meta_cache: parsed.git_meta_cache && typeof parsed.git_meta_cache === "object" ? parsed.git_meta_cache : {},
    };
  }

  #persistJsonFallback() {
    if (this.backend !== "json" || !this._jsonState) return;
    try {
      writeJsonAtomic(this.jsonPath, this._jsonState, 2);
      this._jsonDirty = false;
    } catch {
      // Read-only filesystems retain state in memory for the active process.
    }
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    if (this._db) {
      try {
        this._db.close();
      } catch {
        // Ignore close errors.
      }
      this._db = null;
      this._stmts = {};
    } else if (this._jsonDirty) {
      this.#persistJsonFallback();
    }
  }

  diagnostics() {
    return { backend: this.backend, path: this.storagePath, data_dir: this.dataDir };
  }

  getKv(namespace, key, { nowMs = Date.now() } = {}) {
    const ns = String(namespace || "default");
    const k = String(key || "");
    if (!k) return undefined;
    if (this.backend === "sqlite" && this._db) {
      try {
        const row = this._stmts.getKv.get(ns, k);
        if (!row) return undefined;
        if (row.expires_at_ms !== null && row.expires_at_ms !== undefined && Number(row.expires_at_ms) < nowMs) {
          this._stmts.delKv.run(ns, k);
          return undefined;
        }
        return JSON.parse(row.value_json);
      } catch {
        return undefined;
      }
    }
    const compound = `${ns}::${k}`;
    const entry = this._jsonState?.kv_state?.[compound];
    if (!entry) return undefined;
    if (entry.expires_at_ms !== null && entry.expires_at_ms !== undefined && Number(entry.expires_at_ms) < nowMs) {
      delete this._jsonState.kv_state[compound];
      this._jsonDirty = true;
      return undefined;
    }
    return entry.value;
  }

  setKv(namespace, key, value, { ttlMs = null, nowMs = Date.now() } = {}) {
    const ns = String(namespace || "default");
    const k = String(key || "");
    if (!k) return;
    const expiresAt = Number.isFinite(ttlMs) && ttlMs > 0 ? Math.round(nowMs + ttlMs) : null;
    if (this.backend === "sqlite" && this._db) {
      try {
        this._stmts.setKv.run(ns, k, JSON.stringify(value), Math.round(nowMs), expiresAt);
      } catch {
        // Ignore SQLITE_BUSY writes.
      }
      return;
    }
    if (!this._jsonState) return;
    this._jsonState.kv_state[`${ns}::${k}`] = { value, updated_at_ms: Math.round(nowMs), expires_at_ms: expiresAt };
    this._jsonDirty = true;
    this.#persistJsonFallback();
  }

  getOrComputeFile(filePath, kind, computeFn) {
    const absPath = path.resolve(filePath);
    const st = safeStat(absPath);
    if (!st.exists || !st.isFile) return computeFn(absPath, st);
    if (this.backend === "sqlite" && this._db) {
      try {
        const row = this._stmts.getFile.get(absPath, kind);
        if (row && Number(row.size_bytes) === st.size && Math.abs(Number(row.mtime_ms) - st.mtimeMs) < 0.5) {
          return JSON.parse(row.payload_json);
        }
      } catch {
        // Recompute on corrupt payload.
      }
    } else if (this._jsonState?.file_cache) {
      const entry = this._jsonState.file_cache[`${absPath}::${kind}`];
      if (entry && entry.size_bytes === st.size && Math.abs(entry.mtime_ms - st.mtimeMs) < 0.5) {
        return entry.payload;
      }
    }
    const computed = computeFn(absPath, st);
    if (computed !== undefined) {
      const now = Date.now();
      if (this.backend === "sqlite" && this._db) {
        try {
          this._stmts.setFile.run(absPath, kind, st.mtimeMs, st.size, JSON.stringify(computed), now);
        } catch {
          // Ignore cache write contention.
        }
      } else if (this._jsonState?.file_cache) {
        this._jsonState.file_cache[`${absPath}::${kind}`] = {
          mtime_ms: st.mtimeMs,
          size_bytes: st.size,
          payload: computed,
          updated_at_ms: now,
        };
        this._jsonDirty = true;
        this.#persistJsonFallback();
      }
    }
    return computed;
  }

  static computeWorkspaceFingerprint(workspaceRoot, bundleRel = ".agents/bundles") {
    if (!workspaceRoot || typeof workspaceRoot !== "string" || !path.isAbsolute(workspaceRoot)) return "empty";
    const root = path.resolve(workspaceRoot);
    const parts = [];
    const recordStat = (label, absPath) => {
      const st = safeStat(absPath);
      parts.push(`${label}:${st.exists ? 1 : 0}:${Math.round(st.mtimeMs)}:${st.size}\n`);
    };
    recordStat("setup", path.join(root, ".agents", "setup-state.json"));
    const bundleDir = path.join(root, bundleRel);
    if (!safeStat(bundleDir).isDirectory) return sha1Parts(parts);
    recordStat("bundle-index", path.join(bundleDir, "index.md"));
    const scanDir = (dirAbs, relPrefix, depth = 0) => {
      if (depth > 4) return;
      let entries = [];
      try {
        entries = fs.readdirSync(dirAbs, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name));
      } catch {
        return;
      }
      for (const entry of entries) {
        if (entry.name.startsWith(".")) continue;
        const childAbs = path.join(dirAbs, entry.name);
        const childRel = `${relPrefix}/${entry.name}`;
        if (entry.isDirectory()) scanDir(childAbs, childRel, depth + 1);
        else if (entry.isFile() && /\.(?:md|json|ya?ml)$/i.test(entry.name)) recordStat(childRel, childAbs);
      }
    };
    for (const sec of ["specs", "research", "knowledge", "product"]) {
      const secAbs = path.join(bundleDir, sec);
      if (safeStat(secAbs).isDirectory) scanDir(secAbs, sec, 0);
    }
    return sha1Parts(parts);
  }

  getOrComputeWorkspace(workspaceRoot, kind, fingerprint, computeFn) {
    const ws = path.resolve(workspaceRoot);
    const fp = String(fingerprint || "");
    if (fp) {
      if (this.backend === "sqlite" && this._db) {
        try {
          const row = this._stmts.getWs.get(ws, kind);
          if (row && row.fingerprint === fp) return JSON.parse(row.payload_json);
        } catch {
          // Recompute on corrupt payload.
        }
      } else if (this._jsonState?.workspace_cache) {
        const entry = this._jsonState.workspace_cache[`${ws}::${kind}`];
        if (entry && entry.fingerprint === fp) return entry.payload;
      }
    }
    const value = computeFn();
    if (value !== undefined && fp) {
      const now = Date.now();
      if (this.backend === "sqlite" && this._db) {
        try {
          this._stmts.setWs.run(ws, kind, fp, JSON.stringify(value), now);
        } catch {
          // Ignore write contention.
        }
      } else if (this._jsonState?.workspace_cache) {
        this._jsonState.workspace_cache[`${ws}::${kind}`] = { fingerprint: fp, payload: value, updated_at_ms: now };
        this._jsonDirty = true;
        this.#persistJsonFallback();
      }
    }
    return value;
  }

  invalidateWorkspace(workspaceRoot) {
    if (!workspaceRoot) return;
    const ws = path.resolve(workspaceRoot);
    if (this.backend === "sqlite" && this._db) {
      try {
        this._stmts.delWs.run(ws);
        this._stmts.delFilePrefix.run(`${ws}%`);
      } catch {
        // Ignore invalidation errors.
      }
      return;
    }
    if (this._jsonState) {
      for (const k of Object.keys(this._jsonState.workspace_cache || {})) {
        if (k.startsWith(`${ws}::`)) delete this._jsonState.workspace_cache[k];
      }
      for (const k of Object.keys(this._jsonState.file_cache || {})) {
        if (k.startsWith(ws)) delete this._jsonState.file_cache[k];
      }
      this.#persistJsonFallback();
    }
  }
}
