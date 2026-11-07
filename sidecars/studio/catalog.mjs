/**
 * Persistent stdio bridge to the Python SQLSpec + DuckDB `flow-catalog` worker,
 * paired with a zero-dependency Node Okapi BM25 fallback when Python/DuckDB is absent.
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

import { resolveCatalogWorkerCommand } from "./python-runner.mjs";
import { deriveWorkspaceId, extractTruthBlock, parseFrontmatter } from "./snapshot.mjs";

const STUDIO_DIR = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_PLUGIN_ROOT = path.resolve(STUDIO_DIR, "..", "..");

const TOKEN_RE = /[a-z0-9_]{2,}/g;
const STOPWORDS = new Set([
  "all",
  "and",
  "are",
  "for",
  "from",
  "has",
  "into",
  "not",
  "only",
  "that",
  "the",
  "their",
  "then",
  "this",
  "use",
  "uses",
  "via",
  "when",
  "with",
]);

/**
 * Tokenize text into normalized lexical terms.
 *
 * @param {string} text
 * @returns {string[]}
 */
function tokenize(text) {
  const matches = String(text || "").toLowerCase().match(TOKEN_RE) || [];
  return matches.filter((t) => !STOPWORDS.has(t));
}

/**
 * Pure-JS in-memory Okapi BM25 + provenance + drift fallback used when DuckDB is disabled or absent.
 */
export class NodeBm25FallbackCatalog {
  constructor() {
    /** @type {Map<string, any>} */
    this.entries = new Map();
    /** @type {Set<string>} */
    this.workspaces = new Set();
  }

  /**
   * @param {string[]} workspaceRoots
   */
  indexWorkspaces(workspaceRoots) {
    let indexed = 0;
    for (const rawRoot of workspaceRoots) {
      const wsRoot = path.resolve(rawRoot);
      const bundleRoot = path.join(wsRoot, ".agents", "bundles");
      if (!fs.existsSync(bundleRoot)) continue;
      const workspaceId = deriveWorkspaceId(wsRoot);
      this.workspaces.add(workspaceId);

      for (const mdFile of walkMd(bundleRoot)) {
        const relToBundle = path.relative(bundleRoot, mdFile).split(path.sep).join("/");
        if (relToBundle === "index.md" || relToBundle === "log.md") continue;
        const raw = fs.readFileSync(mdFile, "utf8");
        const { frontmatter, body } = parseFrontmatter(raw);
        if (path.basename(mdFile, ".md") === "index" && !frontmatter.type) continue;

        const conceptId = relToBundle.replace(/\.md$/i, "");
        const entryId = `${workspaceId}:${conceptId}`;
        const relPath = path.relative(wsRoot, mdFile).split(path.sep).join("/");
        const title = String(frontmatter.title || body.match(/^#\s+(.+?)\s*$/m)?.[1] || path.basename(mdFile, ".md"));
        const description = String(frontmatter.description || "");
        const status = String(frontmatter.status || "draft");
        const state = frontmatter.state ? String(frontmatter.state) : null;
        const truthBlock = extractTruthBlock(body);
        const trustTier = resolveTrustTier(frontmatter, status);
        const conceptType = String(frontmatter.type || inferConceptType(relToBundle));
        const tags = Array.isArray(frontmatter.tags) ? frontmatter.tags.map(String) : [];

        const terms = tokenize(`${title} ${description} ${tags.join(" ")} ${truthBlock || ""} ${body}`);
        /** @type {Record<string, number>} */
        const tf = {};
        for (const t of terms) tf[t] = (tf[t] || 0) + 1;

        const sources = extractSources(entryId, wsRoot, frontmatter);
        const links = extractLinks(entryId, workspaceId, bundleRoot, mdFile, body);

        this.entries.set(entryId, {
          entry_id: entryId,
          workspace_id: workspaceId,
          rel_path: relPath,
          concept_id: conceptId,
          concept_type: conceptType,
          title,
          description,
          status,
          state,
          trust_tier: trustTier,
          tags,
          truth_block: truthBlock,
          body_markdown: body.trim(),
          frontmatter_json: JSON.stringify(frontmatter),
          docLen: Math.max(terms.length, 1),
          tf,
          sources,
          links,
        });
        indexed += 1;
      }
    }
    return {
      workspaces_indexed: workspaceRoots.length,
      entries_indexed: indexed,
      entries_unchanged: 0,
      entries_removed: 0,
      embeddings_computed: 0,
      embeddings_reused: 0,
      embedder_model: "node-bm25",
      embedding_dim: 0,
      fts_enabled: false,
      vss_enabled: false,
    };
  }

  /**
   * @param {Record<string, any>} params
   */
  search(params) {
    const queryTerms = Array.from(new Set(tokenize(params.query || "")));
    if (queryTerms.length === 0) return [];
    const docs = Array.from(this.entries.values());
    const docCount = Math.max(docs.length, 1);
    const avgDocLen = docs.reduce((s, d) => s + d.docLen, 0) / docCount || 1;

    /** @type {Record<string, number>} */
    const df = {};
    for (const term of queryTerms) {
      let c = 0;
      for (const d of docs) {
        if (d.tf[term]) c += 1;
      }
      df[term] = c;
    }

    const hits = [];
    for (const d of docs) {
      if (params.workspace_id && d.workspace_id !== params.workspace_id) continue;
      if (params.concept_type && d.concept_type !== params.concept_type) continue;
      if (params.trust_tier && d.trust_tier !== params.trust_tier) continue;
      let score = 0;
      for (const term of queryTerms) {
        const termFreq = d.tf[term] || 0;
        if (!termFreq || !df[term]) continue;
        const idf = Math.log(1 + Math.max(docCount - df[term] + 0.5, 0.5) / (df[term] + 0.5));
        score += idf * ((termFreq * 2.2) / (termFreq + 1.2 * (0.25 + 0.75 * (d.docLen / avgDocLen))));
      }
      if (score > 0) {
        hits.push({
          entry_id: d.entry_id,
          workspace_id: d.workspace_id,
          rel_path: d.rel_path,
          concept_id: d.concept_id,
          concept_type: d.concept_type,
          title: d.title,
          description: d.description,
          trust_tier: d.trust_tier,
          truth_block: d.truth_block,
          status: d.status,
          state: d.state,
          bm25_score: score,
          semantic_score: null,
          rrf_score: score,
        });
      }
    }
    hits.sort((a, b) => b.rrf_score - a.rrf_score);
    return hits.slice(0, Number(params.limit) || 20);
  }

  /**
   * @param {Record<string, any>} params
   */
  provenance(params) {
    const target = String(params.file_path || "").replace(/^\.\//, "");
    if (!target) return [];
    const out = [];
    for (const d of this.entries.values()) {
      if (params.workspace_id && d.workspace_id !== params.workspace_id) continue;
      const matches = d.sources.filter(
        (s) =>
          s.file_path === target ||
          (s.file_path && s.file_path.endsWith(`/${target}`)) ||
          s.resource === target ||
          s.resource.startsWith(`${target}::`)
      );
      if (matches.length > 0) {
        out.push({
          entry_id: d.entry_id,
          workspace_id: d.workspace_id,
          rel_path: d.rel_path,
          concept_id: d.concept_id,
          concept_type: d.concept_type,
          title: d.title,
          description: d.description,
          trust_tier: d.trust_tier,
          truth_block: d.truth_block,
          status: d.status,
          state: d.state,
          bm25_score: null,
          semantic_score: null,
          rrf_score: matches.length,
        });
      }
    }
    return out.slice(0, Number(params.limit) || 20);
  }

  /**
   * @param {string} entryId
   */
  entry(entryId) {
    const d = this.entries.get(entryId);
    if (!d) return null;
    const referencedBy = [];
    for (const other of this.entries.values()) {
      for (const edge of other.links) {
        if (edge.to_entry_id === entryId) referencedBy.push(edge);
      }
    }
    return {
      entry: d,
      sources: d.sources,
      outbound_links: d.links,
      referenced_by: referencedBy,
    };
  }

  facets() {
    /** @type {Record<string, number>} */
    const ws = {};
    /** @type {Record<string, number>} */
    const types = {};
    /** @type {Record<string, number>} */
    const trust = {};
    for (const d of this.entries.values()) {
      ws[d.workspace_id] = (ws[d.workspace_id] || 0) + 1;
      types[d.concept_type] = (types[d.concept_type] || 0) + 1;
      trust[d.trust_tier] = (trust[d.trust_tier] || 0) + 1;
    }
    const toBuckets = (obj) =>
      Object.entries(obj)
        .map(([value, count]) => ({ value, count }))
        .sort((a, b) => b.count - a.count);
    return {
      workspaces: toBuckets(ws),
      concept_types: toBuckets(types),
      trust_tiers: toBuckets(trust),
    };
  }

  /**
   * @param {string | null} [workspaceId]
   */
  drift(workspaceId = null) {
    const broken_links = [];
    const missing_sources = [];
    for (const d of this.entries.values()) {
      if (workspaceId && d.workspace_id !== workspaceId) continue;
      for (const l of d.links) {
        if (!l.target_exists) {
          broken_links.push({
            entry_id: d.entry_id,
            workspace_id: d.workspace_id,
            rel_path: d.rel_path,
            title: d.title,
            issue_kind: "broken_link",
            target: l.to_target,
          });
        }
      }
      for (const s of d.sources) {
        if (!s.resource_exists) {
          missing_sources.push({
            entry_id: d.entry_id,
            workspace_id: d.workspace_id,
            rel_path: d.rel_path,
            title: d.title,
            issue_kind: "missing_source",
            target: s.resource,
          });
        }
      }
    }
    return { broken_links, missing_sources };
  }

  status() {
    return {
      db_path: "memory://node-bm25",
      exists: true,
      workspace_count: this.workspaces.size,
      entry_count: this.entries.size,
      embedding_count: 0,
      embedder_model: "node-bm25",
      embedding_dim: 0,
      fts_enabled: false,
      vss_enabled: false,
    };
  }
}

/**
 * Bridge managing persistent stdio JSON-RPC calls to `flow-catalog` with automatic fallback.
 */
export class CatalogBridge {
  /**
   * @param {{ pluginRoot?: string, workspaceRoot?: string, dbPath?: string, embedder?: string }} [options]
   */
  constructor(options = {}) {
    this.pluginRoot = path.resolve(options.pluginRoot || DEFAULT_PLUGIN_ROOT);
    this.workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
    this.dbPath = options.dbPath || process.env.FLOW_CATALOG_DB || null;
    this.embedder = options.embedder || process.env.FLOW_CATALOG_EMBEDDER || null;
    this.fallback = new NodeBm25FallbackCatalog();
    this.child = null;
    this.nextId = 1;
    /** @type {Map<number, { resolve: Function, reject: Function, timer: NodeJS.Timeout }>} */
    this.pending = new Map();
    this.workerStrategy = "uninitialized";
    this.useFallbackOnly = false;
  }

  /**
   * @param {string[]} workspaceRoots
   */
  async index(workspaceRoots) {
    const res = await this.#call("index", { workspaces: workspaceRoots });
    return res;
  }

  /**
   * @param {Record<string, any>} params
   */
  async search(params) {
    return this.#call("search", params);
  }

  /**
   * @param {Record<string, any>} params
   */
  async provenance(params) {
    return this.#call("provenance", params);
  }

  /**
   * @param {string} entryId
   */
  async entry(entryId) {
    return this.#call("entry", { entry_id: entryId });
  }

  async facets() {
    return this.#call("facets", {});
  }

  /**
   * @param {string | null} [workspaceId]
   */
  async drift(workspaceId = null) {
    return this.#call("drift", { workspace_id: workspaceId });
  }

  async status() {
    const raw = await this.#call("status", {});
    return { ...raw, strategy: this.workerStrategy };
  }

  close() {
    if (this.child) {
      this.child.stdin.end();
      this.child.kill();
      this.child = null;
    }
    for (const [, p] of this.pending) {
      clearTimeout(p.timer);
      p.reject(new Error("CatalogBridge closed"));
    }
    this.pending.clear();
  }

  /**
   * @param {string} method
   * @param {Record<string, any>} params
   */
  async #call(method, params) {
    if (!this.useFallbackOnly) {
      try {
        await this.#ensureWorker();
        if (this.child) {
          return await this.#sendRpc(method, params);
        }
      } catch {
        this.useFallbackOnly = true;
        this.workerStrategy = "node-bm25-fallback";
      }
    }
    return this.#callFallback(method, params);
  }

  async #ensureWorker() {
    if (this.child) return;
    const spec = resolveCatalogWorkerCommand(this.pluginRoot, this.workspaceRoot);
    this.workerStrategy = spec.strategy;
    if (!spec.command) {
      this.useFallbackOnly = true;
      return;
    }

    const args = [...spec.args];
    const serveIdx = args.indexOf("serve-stdio");
    const globalFlags = [];
    if (this.dbPath) globalFlags.push("--db", this.dbPath);
    if (this.embedder) globalFlags.push("--embedder", this.embedder);
    if (serveIdx >= 0 && globalFlags.length > 0) {
      args.splice(serveIdx, 0, ...globalFlags);
    }

    const child = spawn(spec.command, args, {
      cwd: spec.cwd,
      env: { ...process.env, ...spec.env },
      stdio: ["pipe", "pipe", "pipe"],
    });

    const rl = readline.createInterface({ input: child.stdout });
    rl.on("line", (line) => {
      const trimmed = line.trim();
      if (!trimmed) return;
      let msg;
      try {
        msg = JSON.parse(trimmed);
      } catch {
        return;
      }
      const pendingReq = this.pending.get(msg.id);
      if (!pendingReq) return;
      this.pending.delete(msg.id);
      clearTimeout(pendingReq.timer);
      if (msg.error) {
        pendingReq.reject(new Error(msg.error.message || "Catalog worker error"));
      } else {
        pendingReq.resolve(msg.result);
      }
    });

    child.on("exit", () => {
      this.child = null;
      for (const [, p] of this.pending) {
        clearTimeout(p.timer);
        p.reject(new Error("Catalog worker exited unexpectedly"));
      }
      this.pending.clear();
    });

    this.child = child;
    await this.#sendRpc("ping", {});
  }

  /**
   * @param {string} method
   * @param {Record<string, any>} params
   */
  #sendRpc(method, params) {
    return new Promise((resolve, reject) => {
      if (!this.child || !this.child.stdin.writable) {
        reject(new Error("Worker stdin not writable"));
        return;
      }
      const id = this.nextId++;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Catalog RPC '${method}' timed out`));
      }, 30000);
      this.pending.set(id, { resolve, reject, timer });
      this.child.stdin.write(`${JSON.stringify({ id, method, params })}\n`);
    });
  }

  /**
   * @param {string} method
   * @param {Record<string, any>} params
   */
  #callFallback(method, params) {
    if (method === "index") return this.fallback.indexWorkspaces(params.workspaces || [this.workspaceRoot]);
    if (method === "search") return this.fallback.search(params);
    if (method === "provenance") return this.fallback.provenance(params);
    if (method === "entry") return this.fallback.entry(params.entry_id);
    if (method === "facets") return this.fallback.facets();
    if (method === "drift") return this.fallback.drift(params.workspace_id || null);
    if (method === "status") return this.fallback.status();
    return { ok: true };
  }
}

/**
 * @param {string} dir
 * @returns {string[]}
 */
function walkMd(dir) {
  if (!fs.existsSync(dir)) return [];
  /** @type {string[]} */
  const out = [];
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) out.push(...walkMd(full));
    else if (ent.isFile() && ent.name.endsWith(".md")) out.push(full);
  }
  return out;
}

/**
 * @param {Record<string, any>} fm
 * @param {string} status
 */
function resolveTrustTier(fm, status) {
  if (Array.isArray(fm.verified)) {
    for (const v of fm.verified) {
      if (v && typeof v === "object" && String(v.by || "").startsWith("human:")) return "human-reviewed";
    }
    for (const v of fm.verified) {
      if (v && typeof v === "object" && String(v.by || "").startsWith("agent:")) return "agent-verified";
    }
  }
  if (["stable", "accepted", "completed"].includes(status.toLowerCase())) return "verified";
  return "draft";
}

/**
 * @param {string} relToBundle
 */
function inferConceptType(relToBundle) {
  if (relToBundle.startsWith("specs/")) return "Spec";
  if (relToBundle.includes("decisions/")) return "Decision";
  if (relToBundle.includes("patterns/")) return "Pattern";
  if (relToBundle.startsWith("research/")) return "Research";
  return "Concept";
}

/**
 * @param {string} entryId
 * @param {string} wsRoot
 * @param {Record<string, any>} fm
 */
function extractSources(entryId, wsRoot, fm) {
  if (!Array.isArray(fm.sources)) return [];
  return fm.sources
    .filter((s) => s && typeof s === "object" && s.resource)
    .map((s, idx) => {
      const resource = String(s.resource).trim();
      const [rawFile, sym] = resource.includes("::") ? resource.split("::", 2) : [resource, null];
      const filePath = resource.startsWith("http") ? null : rawFile.replace(/^\.\//, "");
      const exists = filePath ? fs.existsSync(path.join(wsRoot, filePath)) : true;
      return {
        entry_id: entryId,
        source_id: String(s.id || `src-${idx + 1}`),
        resource,
        file_path: filePath,
        symbol_name: sym,
        title: s.title ? String(s.title) : null,
        resource_exists: exists,
      };
    });
}

/**
 * @param {string} entryId
 * @param {string} workspaceId
 * @param {string} bundleRoot
 * @param {string} mdFile
 * @param {string} body
 */
function extractLinks(entryId, workspaceId, bundleRoot, mdFile, body) {
  const linkRe = /(?<!!)\[[^\]]+\]\(([^)]+)\)/g;
  const seen = new Set();
  const out = [];
  let m;
  while ((m = linkRe.exec(body)) !== null) {
    const rawTarget = m[1].trim().split(/\s+/)[0];
    if (!rawTarget || /^(#|https?:|mailto:|sidecar:|file:)/.test(rawTarget)) continue;
    const cleanRel = rawTarget.split("#")[0];
    if (!cleanRel || seen.has(cleanRel)) continue;
    seen.add(cleanRel);
    const resolved = path.resolve(path.dirname(mdFile), cleanRel);
    const exists = fs.existsSync(resolved);
    let toEntryId = null;
    if (resolved.endsWith(".md")) {
      const rel = path.relative(bundleRoot, resolved);
      if (!rel.startsWith("..") && !path.isAbsolute(rel)) {
        const concept = rel.replace(/\.md$/i, "").split(path.sep).join("/");
        if (concept !== "index" && concept !== "log") {
          toEntryId = `${workspaceId}:${concept}`;
        }
      }
    }
    out.push({
      from_entry_id: entryId,
      to_target: cleanRel,
      to_entry_id: toEntryId,
      edge_kind: "reference",
      target_exists: exists,
    });
  }
  return out;
}
