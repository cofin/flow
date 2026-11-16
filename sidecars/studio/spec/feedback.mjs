/**
 * Per-author collaborative specification review feedback (`specs/<flow_id>/feedback/<author_slug>.json` + `_meta.json`)
 * with transparent read and migration fallback from legacy `.agents/studio-reviews/` and `.agents/studio-comments.json`.
 */

import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import {
  normalizeRelPath,
  readJsonSafe,
  resolveConfinedPath,
  writeJsonAtomic,
} from "../core/fs-io.mjs";
import { resolveWorktreeContext } from "../core/worktree.mjs";

export const VALID_COMMENT_KINDS = new Set(["feedback", "change_request", "question", "approval"]);
export const VALID_COMMENT_STATES = new Set(["open", "addressed", "dismissed"]);

/**
 * Normalized collaborative review comment matching the shared on-disk feedback schema.
 */
export class SpecComment {
  /**
   * @param {unknown} rawId
   * @returns {string}
   */
  static canonicalKey(rawId) {
    return String(rawId || "").trim().toLowerCase();
  }

  /**
   * @param {Record<string, any>} raw
   * @param {{ viewerEmail?: string | null }} [options]
   */
  static normalize(raw, { viewerEmail = null } = {}) {
    const src = raw && typeof raw === "object" ? raw : {};
    const optStr = (v) => (typeof v === "string" && v.trim() ? v.trim() : null);
    const upvoters = Array.isArray(src.upvoterEmails)
      ? Array.from(new Set(src.upvoterEmails.map((e) => String(e || "").trim()).filter(Boolean)))
      : [];
    const rawState = String(src.state || (src.resolved ? "addressed" : "open")).trim().toLowerCase();
    const state = VALID_COMMENT_STATES.has(rawState === "resolved" ? "addressed" : rawState)
      ? rawState === "resolved"
        ? "addressed"
        : rawState
      : "open";
    const rawKind = String(src.commentKind || "feedback").trim().toLowerCase();
    const commentKind = VALID_COMMENT_KINDS.has(rawKind) ? rawKind : "feedback";
    const lineStart = Number.isInteger(src.lineStart)
      ? src.lineStart
      : Number.isInteger(src.startLine)
        ? src.startLine
        : null;
    const lineEnd = Number.isInteger(src.lineEnd)
      ? src.lineEnd
      : Number.isInteger(src.endLine)
        ? src.endLine
        : lineStart;
    const lineAnchor =
      optStr(src.lineAnchor) ||
      (lineStart !== null ? (lineEnd && lineEnd !== lineStart ? `L${lineStart}-L${lineEnd}` : `L${lineStart}`) : null);

    const viewerLower = viewerEmail ? String(viewerEmail).trim().toLowerCase() : null;
    return {
      id: optStr(src.id) || crypto.randomUUID(),
      parentCommentId: optStr(src.parentCommentId),
      authorEmail: optStr(src.authorEmail) || `${optStr(src.author) || "reviewer"}@local`,
      authorName: optStr(src.authorName) || optStr(src.author) || "reviewer",
      relPath: optStr(src.relPath),
      chapterId: optStr(src.chapterId),
      taskId: optStr(src.taskId),
      anchorHeading: optStr(src.anchorHeading),
      anchorBlockId: optStr(src.anchorBlockId),
      lineAnchor,
      lineStart,
      lineEnd,
      startLine: lineStart ?? 1,
      endLine: lineEnd ?? lineStart ?? 1,
      quotedText: optStr(src.quotedText) || optStr(src.quote),
      quote: optStr(src.quotedText) || optStr(src.quote) || "",
      commentKind,
      state,
      resolved: state !== "open",
      body: String(src.body || "").trim(),
      upvoterEmails: upvoters,
      upvoteCount: upvoters.length,
      viewerHasUpvoted: viewerLower ? upvoters.some((e) => e.toLowerCase() === viewerLower) : false,
      planRevision: Number.isInteger(src.planRevision) ? src.planRevision : 1,
      resolvedInRevision: Number.isInteger(src.resolvedInRevision) ? src.resolvedInRevision : null,
      createdAt: optStr(src.createdAt) || new Date().toISOString(),
      updatedAt: optStr(src.updatedAt) || optStr(src.createdAt) || new Date().toISOString(),
    };
  }

  /**
   * @param {ReturnType<typeof SpecComment.normalize>} normalized
   */
  static stripDerived(normalized) {
    return {
      id: normalized.id,
      parentCommentId: normalized.parentCommentId,
      authorEmail: normalized.authorEmail,
      authorName: normalized.authorName,
      relPath: normalized.relPath,
      chapterId: normalized.chapterId,
      taskId: normalized.taskId,
      anchorHeading: normalized.anchorHeading,
      anchorBlockId: normalized.anchorBlockId,
      lineAnchor: normalized.lineAnchor,
      lineStart: normalized.lineStart,
      lineEnd: normalized.lineEnd,
      quotedText: normalized.quotedText,
      commentKind: normalized.commentKind,
      state: normalized.state,
      body: normalized.body,
      upvoterEmails: normalized.upvoterEmails,
      planRevision: normalized.planRevision,
      resolvedInRevision: normalized.resolvedInRevision,
      createdAt: normalized.createdAt,
      updatedAt: normalized.updatedAt,
    };
  }

  /**
   * @param {any[]} existing
   * @param {any[]} incoming
   * @param {{ viewerEmail?: string | null }} [options]
   */
  static merge(existing, incoming, { viewerEmail = null } = {}) {
    /** @type {Map<string, any>} */
    const byKey = new Map();
    for (const item of [...existing, ...incoming]) {
      if (!item || typeof item !== "object") continue;
      const norm = SpecComment.normalize(item, { viewerEmail });
      const key = SpecComment.canonicalKey(norm.id);
      const prev = byKey.get(key);
      if (!prev || String(norm.updatedAt).localeCompare(String(prev.updatedAt)) >= 0) {
        byKey.set(key, norm);
      }
    }
    return Array.from(byKey.values()).sort((a, b) =>
      String(a.createdAt || "").localeCompare(String(b.createdAt || "")),
    );
  }

  /**
   * @param {any[]} comments
   */
  static summarize(comments) {
    let openCommentCount = 0;
    let addressedCommentCount = 0;
    let approvalCount = 0;
    for (const c of comments) {
      if (!c) continue;
      if (c.commentKind === "approval") {
        if (c.state !== "dismissed") approvalCount += 1;
        continue;
      }
      if (c.state === "open") openCommentCount += 1;
      else if (c.state === "addressed") addressedCommentCount += 1;
    }
    return { openCommentCount, addressedCommentCount, approvalCount };
  }
}

/**
 * Derive author slug from email or username.
 *
 * @param {string} emailOrName
 * @returns {string}
 */
export function authorSlug(emailOrName) {
  const slug = String(emailOrName || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64)
    .replace(/-+$/g, "");
  return slug || "author";
}

/**
 * Resolve current author `{ email, name, slug }` from Git config or OS identity.
 *
 * @param {string} workspaceRoot
 */
export function resolveAuthorIdentity(workspaceRoot) {
  const safeGitCfg = (key) => {
    try {
      return execFileSync("git", ["-C", workspaceRoot, "config", "--get", key], {
        encoding: "utf8",
        timeout: 1500,
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
    } catch {
      return "";
    }
  };
  let fallback = "author";
  try {
    const info = os.userInfo();
    if (info?.username) fallback = info.username;
  } catch {
    fallback = process.env.USER || process.env.USERNAME || "author";
  }
  const email = safeGitCfg("user.email") || `${fallback}@local`;
  const name = safeGitCfg("user.name") || (email.includes("@") ? email.split("@")[0] : fallback);
  return { email, name, slug: authorSlug(email || name) };
}

/**
 * Read/write collaborative review comments across `.agents/bundles/specs/<flow_id>/feedback/<author_slug>.json`
 * with seamless read & migration support for legacy `.agents/studio-reviews/` and `.agents/studio-comments.json`.
 */
export class SpecFeedbackStore {
  /**
   * @param {string} workspaceRoot
   */
  constructor(workspaceRoot) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    const wt = resolveWorktreeContext(this.workspaceRoot);
    this.agentsBaseRoot = wt.effectiveAgentsRoot;
    this.bundleRel = wt.bundleRel || ".agents/bundles";
    this.legacyReviewsDir = path.join(this.agentsBaseRoot, ".agents", "studio-reviews");
    this.legacyFlatCommentsFile = path.join(this.agentsBaseRoot, ".agents", "studio-comments.json");
  }

  /**
   * Infer `<flow_id>` from a spec-relative path if possible.
   *
   * @param {string} relPath
   * @returns {string | null}
   */
  inferFlowId(relPath) {
    const m = String(relPath || "").replace(/\\/g, "/").match(/(?:^|\/)specs\/([^/]+)\//);
    return m ? m[1] : null;
  }

  /**
   * Return the collaborative feedback directory for `flowId`.
   *
   * @param {string} flowId
   */
  feedbackDirForFlow(flowId) {
    return path.join(this.agentsBaseRoot, this.bundleRel, "specs", flowId, "feedback");
  }

  /**
   * Load `_meta.json` for a spec directory.
   *
   * @param {string} flowId
   */
  readMeta(flowId) {
    const metaPath = path.join(this.feedbackDirForFlow(flowId), "_meta.json");
    const parsed = readJsonSafe(metaPath);
    const optStr = (v) => (typeof v === "string" && v.trim() ? v.trim() : null);
    return {
      id: optStr(parsed?.id) || flowId,
      reviewState: optStr(parsed?.reviewState ?? parsed?.review_state),
      catalogEntryName: optStr(parsed?.catalogEntryName ?? parsed?.catalog_entry_name),
      hiveSlug: optStr(parsed?.hiveSlug ?? parsed?.hive_slug),
      updatedAt: optStr(parsed?.updatedAt),
    };
  }

  /**
   * Load all comments for a given `flowId` across per-author files and legacy storage.
   *
   * @param {string} flowId
   * @param {{ viewerEmail?: string | null }} [options]
   */
  listForFlow(flowId, { viewerEmail = null } = {}) {
    const dir = this.feedbackDirForFlow(flowId);
    /** @type {any[]} */
    let merged = [];
    if (fs.existsSync(dir)) {
      for (const name of fs
        .readdirSync(dir)
        .filter((n) => n.endsWith(".json") && !n.startsWith("_") && !n.startsWith("."))
        .sort()) {
        const parsed = readJsonSafe(path.join(dir, name));
        const list = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.comments) ? parsed.comments : [];
        merged = SpecComment.merge(merged, list, { viewerEmail });
      }
    }
    const legacy = this.#readLegacyForFlow(flowId, viewerEmail);
    if (legacy.length > 0) {
      merged = SpecComment.merge(merged, legacy, { viewerEmail });
    }
    return merged;
  }

  /**
   * List comments scoped to a specific document `relPath`.
   *
   * @param {string} relPath
   * @param {{ viewerEmail?: string | null }} [options]
   */
  list(relPath, { viewerEmail = null } = {}) {
    const normRel = this.#normalizeRel(relPath);
    const flowId = this.inferFlowId(normRel);
    const results = [];
    if (flowId) {
      for (const c of this.listForFlow(flowId, { viewerEmail })) {
        if (!c.relPath || c.relPath === normRel) {
          results.push(c);
        }
      }
    }
    const legacyFile = this.#legacyStorageFileFor(normRel);
    const legacyData = readJsonSafe(legacyFile);
    const legacyList = Array.isArray(legacyData?.comments) ? legacyData.comments : [];
    const flat = readJsonSafe(this.legacyFlatCommentsFile);
    const flatList = flat && Array.isArray(flat[normRel]) ? flat[normRel] : [];
    return SpecComment.merge(results, [...legacyList, ...flatList].map((c) => ({ ...c, relPath: normRel })), {
      viewerEmail,
    });
  }

  /**
   * Add a comment, migrating legacy comments for the target flow into per-author feedback files on first write.
   *
   * @param {Record<string, any>} input
   */
  add(input) {
    const relPath = input.relPath ? this.#normalizeRel(input.relPath) : null;
    const flowId = input.flowId || (relPath ? this.inferFlowId(relPath) : null);
    if (!flowId) {
      return this.#addLegacy(relPath || String(input.relPath || ""), input);
    }

    const identity = resolveAuthorIdentity(this.workspaceRoot);
    const authorEmail = String(input.authorEmail || "").trim() || identity.email;
    const authorName = String(input.authorName || input.author || "").trim() || identity.name;
    const slug = authorSlug(authorEmail || authorName);
    const rawKind = String(input.commentKind || "feedback").trim().toLowerCase();
    const body =
      rawKind === "approval" && !String(input.body || "").trim() ? "Approved." : String(input.body || "").trim();
    if (!body) {
      throw new Error("Comment body cannot be empty");
    }

    this.#migrateLegacyIntoFeedback(flowId);

    const feedbackDir = this.feedbackDirForFlow(flowId);
    const authorPath = path.join(feedbackDir, `${slug}.json`);
    const existingData = readJsonSafe(authorPath);
    const existingList = Array.isArray(existingData)
      ? existingData
      : Array.isArray(existingData?.comments)
        ? existingData.comments
        : [];

    const nowIso = new Date().toISOString();
    const comment = SpecComment.normalize({
      ...input,
      relPath,
      authorEmail,
      authorName,
      body,
      createdAt: input.createdAt || nowIso,
      updatedAt: input.updatedAt || nowIso,
    });

    const key = SpecComment.canonicalKey(comment.id);
    const idx = existingList.findIndex((c) => SpecComment.canonicalKey(c?.id) === key);
    const stored = SpecComment.stripDerived(comment);
    if (idx >= 0) existingList[idx] = stored;
    else existingList.push(stored);

    writeJsonAtomic(
      authorPath,
      {
        authorEmail,
        authorName,
        authorSlug: slug,
        updatedAt: nowIso,
        comments: existingList,
      },
      2,
    );
    return comment;
  }

  /**
   * Update state, body, or upvote on an existing comment across per-author feedback files or legacy storage.
   *
   * @param {string} relPathOrFlowId
   * @param {string} commentId
   * @param {Record<string, any> | boolean} [updatesOrResolved]
   */
  setResolvedOrUpdate(relPathOrFlowId, commentId, updatesOrResolved = true) {
    const cleanId = String(commentId || "").trim();
    if (!cleanId) throw new Error("commentId is required");
    const opts =
      typeof updatesOrResolved === "boolean"
        ? { state: updatesOrResolved ? "addressed" : "open" }
        : updatesOrResolved && typeof updatesOrResolved === "object"
          ? updatesOrResolved
          : { state: "addressed" };
    if (opts.resolved !== undefined && opts.state === undefined) {
      opts.state = opts.resolved ? "addressed" : "open";
    }

    const maybeFlowId =
      this.inferFlowId(relPathOrFlowId) ||
      (!String(relPathOrFlowId).includes("/") ? String(relPathOrFlowId).trim() : null);

    if (maybeFlowId) {
      this.#migrateLegacyIntoFeedback(maybeFlowId);
      const dir = this.feedbackDirForFlow(maybeFlowId);
      if (fs.existsSync(dir)) {
        const cleanKey = SpecComment.canonicalKey(cleanId);
        for (const name of fs
          .readdirSync(dir)
          .filter((n) => n.endsWith(".json") && !n.startsWith("_") && !n.startsWith("."))
          .sort()) {
          const full = path.join(dir, name);
          const parsed = readJsonSafe(full);
          const list = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.comments) ? parsed.comments : null;
          if (!list) continue;
          const idx = list.findIndex((c) => c && SpecComment.canonicalKey(c.id) === cleanKey);
          if (idx === -1) continue;

          const target = SpecComment.stripDerived(SpecComment.normalize(list[idx]));
          const nowIso = new Date().toISOString();
          if (opts.state !== undefined && opts.state !== null) {
            const norm = String(opts.state).trim().toLowerCase() === "resolved" ? "addressed" : String(opts.state).trim().toLowerCase();
            if (!VALID_COMMENT_STATES.has(norm)) throw new Error(`Invalid comment state '${opts.state}'`);
            target.state = norm;
            if (norm === "open" && opts.resolvedInRevision === undefined) target.resolvedInRevision = null;
          }
          if (opts.body !== undefined && opts.body !== null) {
            const cleanBody = String(opts.body).trim();
            if (!cleanBody) throw new Error("Comment body cannot be empty");
            target.body = cleanBody;
          }
          if (opts.resolvedInRevision !== undefined) target.resolvedInRevision = opts.resolvedInRevision;
          if (opts.toggleUpvote === true) {
            const actor = String(opts.actorEmail || "").trim() || resolveAuthorIdentity(this.workspaceRoot).email;
            const actorLower = actor.toLowerCase();
            if (target.upvoterEmails.some((e) => e.toLowerCase() === actorLower)) {
              target.upvoterEmails = target.upvoterEmails.filter((e) => e.toLowerCase() !== actorLower);
            } else {
              target.upvoterEmails.push(actor);
            }
          }
          target.updatedAt = nowIso;
          list[idx] = target;
          const out = Array.isArray(parsed) ? list : { ...parsed, updatedAt: nowIso, comments: list };
          writeJsonAtomic(full, out, 2);
          return SpecComment.normalize(target);
        }
      }
    }

    const legacyTarget = this.#legacyStorageFileFor(this.#normalizeRel(relPathOrFlowId));
    const data = readJsonSafe(legacyTarget);
    if (Array.isArray(data?.comments)) {
      const hit = data.comments.find((c) => c.id === cleanId);
      if (hit) {
        hit.resolved = opts.state ? opts.state !== "open" : true;
        hit.state = hit.resolved ? "addressed" : "open";
        writeJsonAtomic(legacyTarget, data, 2);
        return SpecComment.normalize(hit);
      }
    }
    throw new Error(`Review comment not found: ${commentId}`);
  }

  /**
   * Synchronize feedback `_meta.json` and bulk-address resolved comment ids.
   *
   * @param {string} flowId
   * @param {Record<string, any>} updates
   */
  syncReview(flowId, updates = {}) {
    const dir = this.feedbackDirForFlow(flowId);
    const nowIso = new Date().toISOString();
    if (Array.isArray(updates.addressedCommentIds)) {
      for (const cid of updates.addressedCommentIds) {
        try {
          this.setResolvedOrUpdate(flowId, cid, {
            state: "addressed",
            resolvedInRevision: updates.resolvedInRevision ?? null,
          });
        } catch {
          // Ignore unknown ids during bulk sync.
        }
      }
    }
    const meta = this.readMeta(flowId);
    const nextMeta = {
      ...meta,
      ...(updates.reviewState !== undefined ? { reviewState: updates.reviewState } : {}),
      ...(updates.catalogEntryName !== undefined ? { catalogEntryName: updates.catalogEntryName } : {}),
      ...(updates.id !== undefined ? { id: updates.id } : {}),
      ...(updates.hiveSlug !== undefined ? { hiveSlug: updates.hiveSlug } : {}),
      updatedAt: nowIso,
    };
    writeJsonAtomic(path.join(dir, "_meta.json"), nextMeta, 2);
    return nextMeta;
  }

  /**
   * Return map of `{ [relPath]: openCount }` across per-author feedback and legacy directories.
   *
   * @returns {Record<string, number>}
   */
  countByRelPath() {
    /** @type {Record<string, number>} */
    const counts = {};
    const specsDir = path.join(this.agentsBaseRoot, this.bundleRel, "specs");
    if (fs.existsSync(specsDir)) {
      for (const ent of fs.readdirSync(specsDir, { withFileTypes: true })) {
        if (!ent.isDirectory()) continue;
        const comments = this.listForFlow(ent.name);
        for (const c of comments) {
          if (c.state !== "open" || c.commentKind === "approval") continue;
          const key = c.relPath || path.posix.join(this.bundleRel, "specs", ent.name, "spec.md");
          counts[key] = (counts[key] || 0) + 1;
        }
      }
    }
    if (fs.existsSync(this.legacyReviewsDir)) {
      for (const name of fs.readdirSync(this.legacyReviewsDir)) {
        if (!name.endsWith(".json")) continue;
        const data = readJsonSafe(path.join(this.legacyReviewsDir, name));
        if (data?.relPath && Array.isArray(data.comments)) {
          const open = data.comments.filter((c) => !c.resolved && c.state !== "addressed" && c.state !== "dismissed").length;
          if (open > 0 && !counts[data.relPath]) counts[data.relPath] = open;
        }
      }
    }
    return counts;
  }

  /**
   * Format an actionable `/flow:revise` prompt from open review items.
   *
   * @param {string} relPathOrFlowId
   * @param {string | null} [flowIdHint]
   * @param {any[] | null} [preloadedComments]
   */
  buildRevisePrompt(relPathOrFlowId, flowIdHint = null, preloadedComments = null) {
    const inferredFlow = flowIdHint || this.inferFlowId(relPathOrFlowId);
    const targetId = inferredFlow || relPathOrFlowId;
    const rawComments =
      preloadedComments ||
      (relPathOrFlowId.includes("/") ? this.list(relPathOrFlowId) : this.listForFlow(targetId));
    const unresolved = rawComments.filter((c) => c.state === "open" && c.commentKind !== "approval");
    const lines = [
      `/flow:revise ${targetId}`,
      "",
      relPathOrFlowId.includes("/")
        ? `Apply the following line-anchored review notes on \`${relPathOrFlowId}\`:`
        : `Address ${unresolved.length} open review note(s) on \`${targetId}\`:`,
      "",
    ];
    for (const c of unresolved) {
      const range = c.lineAnchor || (c.startLine === c.endLine ? `L${c.startLine}` : `L${c.startLine}-L${c.endLine}`);
      const loc = c.relPath ? `${c.relPath}:${range}` : range;
      lines.push(`- **${loc}** [${c.commentKind}] (${c.authorName || c.authorEmail}): ${c.body}`);
      if (c.quote) lines.push(`  > ${c.quote.replace(/\n/g, " ")}`);
    }
    return lines.join("\n");
  }

  #normalizeRel(relPath) {
    const clean = String(relPath || "").replace(/\\/g, "/");
    const baseRoot = clean.startsWith(".agents/") ? this.agentsBaseRoot : this.workspaceRoot;
    return normalizeRelPath(baseRoot, clean);
  }

  #legacyStorageFileFor(normRel) {
    const hash = crypto.createHash("sha256").update(normRel).digest("hex").slice(0, 12);
    const safeSlug = normRel.replace(/[^a-zA-Z0-9_-]+/g, "_").slice(-48);
    return path.join(this.legacyReviewsDir, `${safeSlug}-${hash}.json`);
  }

  #readLegacyForFlow(flowId, viewerEmail = null) {
    const collected = [];
    if (fs.existsSync(this.legacyReviewsDir)) {
      for (const name of fs.readdirSync(this.legacyReviewsDir)) {
        if (!name.endsWith(".json")) continue;
        const data = readJsonSafe(path.join(this.legacyReviewsDir, name));
        if (data?.relPath && this.inferFlowId(data.relPath) === flowId && Array.isArray(data.comments)) {
          collected.push(...data.comments.map((c) => SpecComment.normalize({ ...c, relPath: data.relPath }, { viewerEmail })));
        }
      }
    }
    const flat = readJsonSafe(this.legacyFlatCommentsFile);
    if (flat && typeof flat === "object") {
      for (const [rp, list] of Object.entries(flat)) {
        if (this.inferFlowId(rp) === flowId && Array.isArray(list)) {
          collected.push(...list.map((c) => SpecComment.normalize({ ...c, relPath: rp }, { viewerEmail })));
        }
      }
    }
    return collected;
  }

  #migrateLegacyIntoFeedback(flowId) {
    const feedbackDir = this.feedbackDirForFlow(flowId);
    if (fs.existsSync(feedbackDir)) return;
    const legacy = this.#readLegacyForFlow(flowId);
    if (legacy.length === 0) return;

    /** @type {Map<string, { authorEmail: string, authorName: string, comments: any[] }>} */
    const byAuthor = new Map();
    for (const item of legacy) {
      const slug = authorSlug(item.authorEmail || item.authorName);
      if (!byAuthor.has(slug)) {
        byAuthor.set(slug, {
          authorEmail: item.authorEmail,
          authorName: item.authorName,
          comments: [],
        });
      }
      byAuthor.get(slug).comments.push(SpecComment.stripDerived(item));
    }
    for (const [slug, group] of byAuthor.entries()) {
      writeJsonAtomic(
        path.join(feedbackDir, `${slug}.json`),
        {
          authorEmail: group.authorEmail,
          authorName: group.authorName,
          authorSlug: slug,
          updatedAt: new Date().toISOString(),
          comments: group.comments,
        },
        2,
      );
    }
  }

  #addLegacy(normRel, input) {
    const file = this.#legacyStorageFileFor(normRel);
    const existing = readJsonSafe(file);
    const list = Array.isArray(existing?.comments) ? existing.comments : [];
    const comment = SpecComment.normalize({ ...input, relPath: normRel });
    list.push(comment);
    writeJsonAtomic(file, { relPath: normRel, comments: list }, 2);
    return comment;
  }
}
