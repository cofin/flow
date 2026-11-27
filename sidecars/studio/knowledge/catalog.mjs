/**
 * Knowledge catalog bridge with zero-Python weighted BM25 + sibling-workspace federation
 * and optional SQLSpec/DuckDB hybrid ONNX semantic worker.
 */

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

import { resolveCatalogWorkerCommand } from "../bridges/python.mjs";
import { parseFrontmatter, extractTruthBlock, scanWikilinks, wrapUntrustedSnippet } from "../core/frontmatter.mjs";
import {
  deriveWorkspaceId,
  isExistingDir,
  StudioStateStore,
  toPosixRelative,
  uriToWorkspacePath,
  walkMarkdownFiles,
} from "../core/fs-io.mjs";

const KNOWLEDGE_DIR = path.dirname(fileURLToPath(import.meta.url));
export const DEFAULT_PLUGIN_ROOT = path.resolve(KNOWLEDGE_DIR, "..", "..", "..");

const TOKEN_RE = /[a-z0-9_]{2,}/g;
const STOPWORDS = new Set([
  "all", "and", "are", "for", "from", "has", "into", "not", "only", "that",
  "the", "their", "then", "this", "use", "uses", "via", "when", "with",
]);

/**
 * @param {string} text
 * @returns {string[]}
 */
function tokenize(text) {
  const expanded = String(text || "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Za-z])(\d)/g, "$1 $2");
  const matches = expanded.toLowerCase().match(TOKEN_RE) || [];
  return matches.filter((t) => !STOPWORDS.has(t));
}

/**
 * Weighted BM25 lexical index supporting single or federated sibling workspaces and `wiki/` links.
 */
export class NodeBm25FallbackCatalog {
  constructor() {
    /** @type {Map<string, any>} */
    this.entries = new Map();
    /** @type {Set<string>} */
    this.workspaces = new Set();
  }

  /**
   * Discover up to 8 sibling workspaces from recent Studio history.
   *
   * @param {string} currentWorkspace
   * @param {NodeJS.ProcessEnv} [env]
   */
  static discoverSiblingWorkspaces(currentWorkspace, env = process.env) {
    const cur = path.resolve(currentWorkspace);
    const cfgDir = StudioStateStore.resolveConfigDir(env);
    const tsvPath = env.FLOW_RECENT_WORKSPACES_FILE
      ? path.resolve(env.FLOW_RECENT_WORKSPACES_FILE)
      : path.join(cfgDir, "recent-workspaces.tsv");
    const siblings = [];
    if (!fs.existsSync(tsvPath)) return siblings;
    try {
      const lines = fs.readFileSync(tsvPath, "utf8").split(/\r?\n/).filter(Boolean).reverse();
      for (const line of lines) {
        const raw = line.includes("\t") ? line.split("\t")[1] : line;
        const resolved = uriToWorkspacePath(raw);
        if (
          resolved &&
          resolved !== cur &&
          !siblings.includes(resolved) &&
          isExistingDir(path.join(resolved, ".agents", "bundles"))
        ) {
          siblings.push(resolved);
          if (siblings.length >= 8) break;
        }
      }
    } catch {
      // Ignore unreadable history files.
    }
    return siblings;
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

      for (const mdFile of walkMarkdownFiles(bundleRoot)) {
        const relToBundle = toPosixRelative(bundleRoot, mdFile);
        if (relToBundle === "index.md" || relToBundle === "log.md" || relToBundle.includes("/feedback/")) continue;
        const raw = fs.readFileSync(mdFile, "utf8");
        const { frontmatter, body } = parseFrontmatter(raw);
        if (path.basename(mdFile, ".md") === "index" && !frontmatter.type) continue;

        const conceptId = relToBundle.replace(/\.md$/i, "");
        const entryId = `${workspaceId}:${conceptId}`;
        const relPath = toPosixRelative(wsRoot, mdFile);
        const title = String(frontmatter.title || body.match(/^#\s+(.+?)\s*$/m)?.[1] || path.basename(mdFile, ".md"));
        const description = String(frontmatter.description || "");
        const status = String(frontmatter.status || "draft");
        const state = frontmatter.state ? String(frontmatter.state) : null;
        const truthBlock = extractTruthBlock(body);
        const trustTier = resolveTrustTier(frontmatter, status);
        const conceptType = String(frontmatter.type || inferConceptType(relToBundle));
        const tags = Array.isArray(frontmatter.tags) ? frontmatter.tags.map(String) : [];

        const fieldTerms = [
          ...tokenize(title),
          ...tokenize(title),
          ...tokenize(description),
          ...tokenize(tags.join(" ")),
          ...tokenize(truthBlock || ""),
          ...tokenize(body),
        ];
        /** @type {Record<string, number>} */
        const tf = {};
        for (const t of fieldTerms) tf[t] = (tf[t] || 0) + 1;

        this.entries.set(entryId, {
          entry_id: entryId,
          workspace_id: workspaceId,
          workspace_root: wsRoot,
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
          docLen: Math.max(fieldTerms.length, 1),
          tf,
          sources: extractSources(entryId, wsRoot, frontmatter),
          links: extractLinks(entryId, workspaceId, bundleRoot, mdFile, body),
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
   * Search across indexed local and sibling entries, optionally fencing cross-workspace snippets.
   *
   * @param {Record<string, any>} params
   */
  search(params) {
    const queryTerms = Array.from(new Set(tokenize(params.query || "")));
    if (queryTerms.length === 0) return [];
    const docs = Array.from(this.entries.values());
    const docCount = Math.max(docs.length, 1);
    const avgDocLen = docs.reduce((s, d) => s + d.docLen, 0) / docCount || 1;
    const primaryWsId = params.primary_workspace ? deriveWorkspaceId(params.primary_workspace) : null;

    /** @type {Record<string, number>} */
    const df = {};
    for (const term of queryTerms) {
      let c = 0;
      for (const d of docs) if (d.tf[term]) c += 1;
      df[term] = c;
    }

    const hits = [];
    for (const d of docs) {
      if (params.workspace_id && d.workspace_id !== params.workspace_id) continue;
      if (params.concept_type && d.concept_type !== params.concept_type) continue;
      if (params.trust_tier && d.trust_tier !== params.trust_tier) continue;
      let score = 0;
      for (const term of queryTerms) {
        const tfVal = d.tf[term] || 0;
        if (!tfVal || !df[term]) continue;
        const idf = Math.log(1 + Math.max(docCount - df[term] + 0.5, 0.5) / (df[term] + 0.5));
        score += idf * ((tfVal * 2.2) / (tfVal + 1.2 * (0.25 + 0.75 * (d.docLen / avgDocLen))));
      }
      if (score > 0) {
        const isExternal = Boolean(primaryWsId && d.workspace_id !== primaryWsId);
        const snippetRaw = d.truth_block || d.description || d.body_markdown.slice(0, 240);
        hits.push({
          entry_id: d.entry_id,
          workspace_id: d.workspace_id,
          rel_path: d.rel_path,
          concept_id: d.concept_id,
          concept_type: d.concept_type,
          title: d.title,
          description: d.description,
          snippet: isExternal ? wrapUntrustedSnippet(snippetRaw, `${d.workspace_id}:${d.rel_path}`) : snippetRaw,
          plane: isExternal ? "siblings" : "local",
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
          s.resource.startsWith(`${target}::`),
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

  entry(entryId) {
    const d = this.entries.get(entryId);
    if (!d) return null;
    const referencedBy = [];
    for (const other of this.entries.values()) {
      for (const edge of other.links) {
        if (edge.to_entry_id === entryId) referencedBy.push(edge);
      }
    }
    return { entry: d, sources: d.sources, outbound_links: d.links, referenced_by: referencedBy };
  }

  facets() {
    const ws = {};
    const types = {};
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
    return { workspaces: toBuckets(ws), concept_types: toBuckets(types), trust_tiers: toBuckets(trust) };
  }

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

export class CatalogBridge {
  constructor(options = {}) {
    this.pluginRoot = path.resolve(options.pluginRoot || DEFAULT_PLUGIN_ROOT);
    this.workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
    this.env = options.env || process.env;
    this.dbPath = options.dbPath || this.env.FLOW_CATALOG_DB || null;
    this.embedder = options.embedder || this.env.FLOW_CATALOG_EMBEDDER || null;
    this.enableDuckDb =
      options.enableDuckDb === true ||
      String(this.env.FLOW_ENABLE_DUCKDB || "").trim() === "1";
    this.fallback = new NodeBm25FallbackCatalog();
    this.child = null;
    this.nextId = 1;
    this.pending = new Map();
    this.useFallbackOnly = !this.enableDuckDb;
    this.workerStrategy = this.enableDuckDb ? "uninitialized" : "node-bm25";
  }

  async index(workspaceRoots) {
    return this.#call("index", { workspaces: workspaceRoots });
  }

  async search(params) {
    return this.#call("search", params);
  }

  async federatedSearch({ query, planes = ["local", "siblings"], limit = 12 } = {}) {
    const targets = [this.workspaceRoot];
    if (planes.includes("siblings")) {
      targets.push(...NodeBm25FallbackCatalog.discoverSiblingWorkspaces(this.workspaceRoot));
    }
    this.fallback.indexWorkspaces(targets);
    return this.fallback.search({ query, primary_workspace: this.workspaceRoot, limit });
  }

  async provenance(params) {
    return this.#call("provenance", params);
  }

  async entry(entryId) {
    return this.#call("entry", { entry_id: entryId });
  }

  async facets() {
    return this.#call("facets", {});
  }

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

  async #call(method, params) {
    if (!this.useFallbackOnly) {
      try {
        await this.#ensureWorker();
        if (this.child) return await this.#sendRpc(method, params);
      } catch {
        this.useFallbackOnly = true;
        this.workerStrategy = "node-bm25-fallback";
      }
    }
    return this.#callFallback(method, params);
  }

  async #ensureWorker() {
    if (this.child) return;
    const spec = resolveCatalogWorkerCommand(this.pluginRoot, this.workspaceRoot, {
      enableDuckDb: this.enableDuckDb,
      env: this.env,
    });
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
    if (serveIdx >= 0 && globalFlags.length > 0) args.splice(serveIdx, 0, ...globalFlags);

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
      const req = this.pending.get(msg.id);
      if (!req) return;
      this.pending.delete(msg.id);
      clearTimeout(req.timer);
      if (msg.error) req.reject(new Error(msg.error.message || "Catalog worker error"));
      else req.resolve(msg.result);
    });
    child.on("exit", () => {
      this.child = null;
      for (const [, p] of this.pending) {
        clearTimeout(p.timer);
        p.reject(new Error("Catalog worker exited"));
      }
      this.pending.clear();
    });
    this.child = child;
    await this.#sendRpc("ping", {});
  }

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

function inferConceptType(relToBundle) {
  if (relToBundle.startsWith("specs/")) return "Spec";
  if (relToBundle.includes("decisions/")) return "Decision";
  if (relToBundle.includes("patterns/")) return "Pattern";
  if (relToBundle.startsWith("research/")) return "Research";
  return "Concept";
}

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
        if (concept !== "index" && concept !== "log") toEntryId = `${workspaceId}:${concept}`;
      }
    }
    out.push({ from_entry_id: entryId, to_target: cleanRel, to_entry_id: toEntryId, edge_kind: "reference", target_exists: exists });
  }
  for (const wl of scanWikilinks(body)) {
    const slug = `${wl.target.replace(/\.md$/i, "")}.md`;
    if (seen.has(slug)) continue;
    seen.add(slug);
    const cand = path.resolve(bundleRoot, slug);
    const exists = fs.existsSync(cand) || fs.existsSync(path.resolve(path.dirname(mdFile), slug));
    out.push({
      from_entry_id: entryId,
      to_target: wl.target,
      to_entry_id: `${workspaceId}:${wl.target.replace(/\.md$/i, "")}`,
      edge_kind: "wikilink",
      target_exists: exists,
    });
  }
  return out;
}
