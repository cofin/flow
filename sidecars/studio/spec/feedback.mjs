/**
 * Per-author collaborative specification review feedback stored out-of-tree inside Git repositories
 * (`<git-common-dir>/spec-feedback/<flow_id>/<author_slug>.json`), with transparent discovery
 * across sibling `*-feedback/` stores, in-tree `<spec_dir>/feedback/` fallbacks for non-Git
 * workspaces, remote zero-clone config storage, and legacy `.agents/studio-reviews/` files.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import {
  normalizeRelPath,
  readJsonSafe,
  resolveConfinedPath,
  StudioStateStore,
  writeJsonAtomic,
} from "../core/fs-io.mjs";
import { GitRunner, resolveGitIdentity } from "../core/git.mjs";
import { DEFAULT_FEEDBACK_STORE_DIR, resolveWorktreeContext } from "../core/worktree.mjs";

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
    const mappedState = rawState === "resolved" ? "addressed" : rawState;
    const state = VALID_COMMENT_STATES.has(mappedState) ? mappedState : "open";
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

    let externalSource = null;
    if (src.externalSource && typeof src.externalSource === "object" && !Array.isArray(src.externalSource)) {
      const extKind = optStr(src.externalSource.kind);
      const extFileId = optStr(src.externalSource.fileId);
      const extUrl = optStr(src.externalSource.url);
      if (extKind || extFileId || extUrl) {
        externalSource = {
          kind: extKind,
          label: optStr(src.externalSource.label),
          fileId: extFileId,
          url: extUrl,
          title: optStr(src.externalSource.title),
          threadId: optStr(src.externalSource.threadId),
        };
      }
    }

    const viewerLower = viewerEmail ? String(viewerEmail).trim().toLowerCase() : null;
    return {
      id: optStr(src.id) || crypto.randomUUID(),
      parentCommentId: optStr(src.parentCommentId),
      authorEmail: optStr(src.authorEmail) || `${optStr(src.author) || "reviewer"}@local`,
      authorName: optStr(src.authorName) || optStr(src.author) || "reviewer",
      relPath: optStr(src.relPath),
      gitBranch: optStr(src.gitBranch),
      commitSha: optStr(src.commitSha),
      ghPrCommentId:
        src.ghPrCommentId !== undefined && src.ghPrCommentId !== null && String(src.ghPrCommentId).trim()
          ? String(src.ghPrCommentId).trim()
          : null,
      externalSource,
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
      gitBranch: normalized.gitBranch || null,
      commitSha: normalized.commitSha || null,
      ghPrCommentId: normalized.ghPrCommentId || null,
      ...(normalized.externalSource ? { externalSource: normalized.externalSource } : {}),
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
  return resolveGitIdentity(workspaceRoot);
}

/**
 * Parse raw feedback JSON string, automatically merging conflict blocks if present.
 *
 * @param {string} rawText
 * @param {{ viewerEmail?: string | null }} [options]
 * @returns {any[]}
 */
export function parseFeedbackJsonText(rawText, { viewerEmail = null } = {}) {
  const text = String(rawText || "").trim();
  if (!text) return [];
  if (/^<{7}(?: .*)?$/m.test(text) && /^={7}$/m.test(text) && /^>{7}(?: .*)?$/m.test(text)) {
    const oursLines = [];
    const theirsLines = [];
    let mode = "common";
    for (const line of text.replace(/\r\n/g, "\n").split("\n")) {
      if (line.startsWith("<<<<<<<")) {
        mode = "ours";
        continue;
      }
      if (mode === "ours" && line.startsWith("|||||||")) {
        mode = "base";
        continue;
      }
      if ((mode === "ours" || mode === "base") && line === "=======") {
        mode = "theirs";
        continue;
      }
      if (mode === "theirs" && line.startsWith(">>>>>>>")) {
        mode = "common";
        continue;
      }
      if (mode === "common") {
        oursLines.push(line);
        theirsLines.push(line);
      } else if (mode === "ours") {
        oursLines.push(line);
      } else if (mode === "theirs") {
        theirsLines.push(line);
      }
    }
    return SpecComment.merge(
      parseFeedbackJsonText(oursLines.join("\n"), { viewerEmail }),
      parseFeedbackJsonText(theirsLines.join("\n"), { viewerEmail }),
      { viewerEmail },
    );
  }
  try {
    const parsed = JSON.parse(text);
    const list = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.comments) ? parsed.comments : [];
    return SpecComment.merge([], list, { viewerEmail });
  } catch {
    return [];
  }
}

/**
 * Read and write collaborative review comments out-of-tree in `<git-common-dir>/spec-feedback/<flow_id>/`
 * for Git repos, with automatic discovery of sibling `<git-common-dir>/*-feedback/<flow_id>/` stores,
 * `<spec_dir>/feedback/` outside Git, and `<FLOW_CONFIG_DIR>/feedback/<repo>/<flow_id>/` for remote repos.
 */
export class SpecFeedbackStore {
  /**
   * @param {string} workspaceRoot
   * @param {{ env?: NodeJS.ProcessEnv, repoLocator?: string | null }} [options]
   */
  constructor(workspaceRoot, { env = process.env, repoLocator = null } = {}) {
    this.workspaceRoot = workspaceRoot ? path.resolve(workspaceRoot) : null;
    this.env = env;
    this.repoLocator = repoLocator || null;
    if (this.workspaceRoot) {
      const wt = resolveWorktreeContext(this.workspaceRoot);
      this.agentsBaseRoot = wt.effectiveAgentsRoot;
      this.bundleRel = wt.bundleRel || ".agents/bundles";
      this.feedbackStoreDirName = wt.feedbackStoreDir || DEFAULT_FEEDBACK_STORE_DIR;
      this.legacyReviewsDir = path.join(this.agentsBaseRoot, ".agents", "studio-reviews");
      this.legacyFlatCommentsFile = path.join(this.agentsBaseRoot, ".agents", "studio-comments.json");
    } else {
      this.agentsBaseRoot = null;
      this.bundleRel = ".agents/bundles";
      this.feedbackStoreDirName = DEFAULT_FEEDBACK_STORE_DIR;
      this.legacyReviewsDir = null;
      this.legacyFlatCommentsFile = null;
    }
  }

  /**
   * Resolve `<git-common-dir>` if `workspaceRoot` is inside a Git repository.
   *
   * @returns {string | null}
   */
  resolveCommonGitDir() {
    if (!this.workspaceRoot || !fs.existsSync(this.workspaceRoot)) return null;
    const git = GitRunner.forWorkspace(this.workspaceRoot, { timeoutMs: 2500, env: this.env });
    if (!git.isGitRepo()) return null;
    const common = git.gitCommonDir();
    return common.ok && common.value ? common.value : null;
  }

  /**
   * Infer `<flow_id>` from a spec-relative path if possible.
   *
   * @param {string} relPath
   * @returns {string | null}
   */
  inferFlowId(relPath) {
    const m = String(relPath || "").replace(/\\/g, "/").match(/(?:^|\/)(?:specs|tracks)\/([^/]+)\//);
    return m ? m[1] : null;
  }

  /**
   * Primary writable feedback directory for `flowId`.
   *
   * @param {string} flowId
   */
  feedbackDirForFlow(flowId) {
    const cleanFlow = String(flowId || "").trim();
    if (this.repoLocator && !this.workspaceRoot) {
      const cfgDir = StudioStateStore.resolveConfigDir(this.env);
      return path.join(cfgDir, "feedback", authorSlug(this.repoLocator), cleanFlow);
    }
    const commonDir = this.resolveCommonGitDir();
    if (commonDir) {
      return path.join(commonDir, this.feedbackStoreDirName, cleanFlow);
    }
    if (this.agentsBaseRoot) {
      return path.join(this.agentsBaseRoot, this.bundleRel, "specs", cleanFlow, "feedback");
    }
    return path.join(StudioStateStore.resolveConfigDir(this.env), "feedback", "local", cleanFlow);
  }

  /**
   * Return all candidate feedback directories for `flowId` across primary store, sibling `*-feedback/`
   * stores in `<git-common-dir>`, and in-tree `<spec_dir>/feedback/`.
   *
   * @param {string} flowId
   * @returns {string[]}
   */
  candidateDirsForFlow(flowId) {
    const cleanFlow = String(flowId || "").trim();
    const dirs = [];
    const pushDir = (candidate) => {
      if (!candidate) return;
      const resolved = path.resolve(candidate);
      if (!dirs.includes(resolved)) dirs.push(resolved);
    };

    pushDir(this.feedbackDirForFlow(cleanFlow));

    const commonDir = this.resolveCommonGitDir();
    if (commonDir && fs.existsSync(commonDir)) {
      try {
        for (const ent of fs.readdirSync(commonDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
          if (ent.isDirectory() && ent.name.endsWith("-feedback")) {
            pushDir(path.join(commonDir, ent.name, cleanFlow));
          }
        }
      } catch {
        // Ignore unreadable .git directories.
      }
    }

    if (this.agentsBaseRoot) {
      pushDir(path.join(this.agentsBaseRoot, this.bundleRel, "specs", cleanFlow, "feedback"));
    }
    return dirs;
  }

  /**
   * Load `_meta.json` across candidate feedback directories for a flow.
   *
   * @param {string} flowId
   */
  readMeta(flowId) {
    const optStr = (v) => (typeof v === "string" && v.trim() ? v.trim() : null);
    for (const dir of this.candidateDirsForFlow(flowId)) {
      const metaPath = path.join(dir, "_meta.json");
      const parsed = readJsonSafe(metaPath);
      if (!parsed || typeof parsed !== "object") continue;
      return {
        id: optStr(parsed.id) || flowId,
        reviewState: optStr(parsed.reviewState ?? parsed.review_state),
        catalogEntryName: optStr(parsed.catalogEntryName ?? parsed.catalog_entry_name),
        updatedAt: optStr(parsed.updatedAt),
      };
    }
    return {
      id: flowId,
      reviewState: null,
      catalogEntryName: null,
      updatedAt: null,
    };
  }

  /**
   * Load all comments for a given `flowId` across primary store, sibling `*-feedback/`, in-tree files, and legacy storage.
   *
   * @param {string} flowId
   * @param {{ viewerEmail?: string | null, extraComments?: any[] }} [options]
   */
  listForFlow(flowId, { viewerEmail = null, extraComments = [] } = {}) {
    /** @type {any[]} */
    let merged = [];
    for (const dir of this.candidateDirsForFlow(flowId)) {
      if (!fs.existsSync(dir)) continue;
      let files = [];
      try {
        files = fs
          .readdirSync(dir)
          .filter((n) => n.endsWith(".json") && !n.startsWith("_") && !n.startsWith("."))
          .sort();
      } catch {
        continue;
      }
      for (const name of files) {
        try {
          const list = parseFeedbackJsonText(fs.readFileSync(path.join(dir, name), "utf8"), { viewerEmail });
          merged = SpecComment.merge(merged, list, { viewerEmail });
        } catch {
          // Ignore malformed feedback snapshot.
        }
      }
    }
    const legacy = this.#readLegacyForFlow(flowId, viewerEmail);
    if (legacy.length > 0) {
      merged = SpecComment.merge(merged, legacy, { viewerEmail });
    }
    if (Array.isArray(extraComments) && extraComments.length > 0) {
      merged = SpecComment.merge(merged, extraComments, { viewerEmail });
    }
    return merged;
  }

  /**
   * List comments scoped to a specific document `relPath`.
   *
   * @param {string} relPath
   * @param {{ viewerEmail?: string | null, extraComments?: any[] }} [options]
   */
  list(relPath, { viewerEmail = null, extraComments = [] } = {}) {
    const normRel = this.#normalizeRel(relPath);
    const flowId = this.inferFlowId(normRel);
    const results = [];
    if (flowId) {
      for (const c of this.listForFlow(flowId, { viewerEmail, extraComments })) {
        if (!c.relPath || c.relPath === normRel) {
          results.push(c);
        }
      }
    }
    const legacyFile = this.#legacyStorageFileFor(normRel);
    const legacyData = legacyFile ? readJsonSafe(legacyFile) : null;
    const legacyList = Array.isArray(legacyData?.comments) ? legacyData.comments : [];
    const flat = this.legacyFlatCommentsFile ? readJsonSafe(this.legacyFlatCommentsFile) : null;
    const flatList = flat && Array.isArray(flat[normRel]) ? flat[normRel] : [];
    return SpecComment.merge(results, [...legacyList, ...flatList].map((c) => ({ ...c, relPath: normRel })), {
      viewerEmail,
    });
  }

  /**
   * Add a comment or reply to the active author's JSON file.
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
    const existingList = this.#readAuthorRaw(flowId, slug);

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
   * Create a threaded reply linked to `parentCommentId`.
   *
   * @param {string} relPathOrFlowId
   * @param {string} parentCommentId
   * @param {Record<string, any>} input
   */
  replyToComment(relPathOrFlowId, parentCommentId, input = {}) {
    const cleanParent = String(parentCommentId || "").trim();
    if (!cleanParent) throw new Error("parentCommentId is required");
    const flowId =
      input.flowId ||
      this.inferFlowId(relPathOrFlowId) ||
      (!String(relPathOrFlowId).includes("/") ? String(relPathOrFlowId).trim() : null);
    if (!flowId) throw new Error("flowId is required for comment replies");
    const all = this.listForFlow(flowId);
    const parent = all.find((c) => SpecComment.canonicalKey(c.id) === SpecComment.canonicalKey(cleanParent));
    return this.add({
      ...input,
      flowId,
      relPath: input.relPath || parent?.relPath || (String(relPathOrFlowId).includes("/") ? relPathOrFlowId : null),
      parentCommentId: parent?.id || cleanParent,
      chapterId: input.chapterId || parent?.chapterId || undefined,
      taskId: input.taskId || parent?.taskId || undefined,
      lineStart: input.lineStart ?? parent?.lineStart ?? undefined,
      lineEnd: input.lineEnd ?? parent?.lineEnd ?? undefined,
      anchorHeading: input.anchorHeading || parent?.anchorHeading || undefined,
      anchorBlockId: input.anchorBlockId || parent?.anchorBlockId || undefined,
    });
  }

  /**
   * Merge an external batch of comments for one author (e.g. pulled from another branch or PR).
   *
   * @param {{ flowId: string, authorEmail: string, authorName: string, authorSlug?: string | null, comments: any[] }} params
   */
  writeMergedAuthorBatch({ flowId, authorEmail, authorName, authorSlug: explicitSlug = null, comments = [] }) {
    const slug = authorSlug(explicitSlug || authorEmail || authorName);
    const dir = this.feedbackDirForFlow(flowId);
    const existing = this.#readAuthorRaw(flowId, slug);
    const merged = SpecComment.merge(existing, comments).map((c) => SpecComment.stripDerived(c));
    const authorPath = path.join(dir, `${slug}.json`);
    writeJsonAtomic(
      authorPath,
      {
        authorEmail: authorEmail || `${slug}@local`,
        authorName: authorName || slug,
        authorSlug: slug,
        updatedAt: new Date().toISOString(),
        comments: merged,
      },
      2,
    );
    return { path: authorPath, slug, comments: merged };
  }

  /**
   * Update state, body, or upvote on an existing comment across primary, sibling, and legacy stores.
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
      const all = this.listForFlow(maybeFlowId, { extraComments: opts.extraComments || [] });
      const cleanKey = SpecComment.canonicalKey(cleanId);
      const found = all.find((c) => SpecComment.canonicalKey(c.id) === cleanKey);
      if (found) {
        const target = SpecComment.stripDerived(SpecComment.normalize(found));
        const nowIso = new Date().toISOString();
        if (opts.state !== undefined && opts.state !== null) {
          const norm =
            String(opts.state).trim().toLowerCase() === "resolved" ? "addressed" : String(opts.state).trim().toLowerCase();
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

        const ownerSlug = authorSlug(target.authorEmail || target.authorName);
        this.writeMergedAuthorBatch({
          flowId: maybeFlowId,
          authorEmail: target.authorEmail,
          authorName: target.authorName,
          authorSlug: ownerSlug,
          comments: [target],
        });
        return SpecComment.normalize(target, { viewerEmail: opts.actorEmail || null });
      }
    }

    if (this.workspaceRoot) {
      const legacyTarget = this.#legacyStorageFileFor(this.#normalizeRel(relPathOrFlowId));
      const data = legacyTarget ? readJsonSafe(legacyTarget) : null;
      if (Array.isArray(data?.comments)) {
        const hit = data.comments.find((c) => c.id === cleanId);
        if (hit) {
          hit.resolved = opts.state ? opts.state !== "open" : true;
          hit.state = hit.resolved ? "addressed" : "open";
          writeJsonAtomic(legacyTarget, data, 2);
          return SpecComment.normalize(hit);
        }
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
      updatedAt: nowIso,
    };
    writeJsonAtomic(path.join(dir, "_meta.json"), nextMeta, 2);
    return nextMeta;
  }

  /**
   * Return map of `{ [relPath]: openCount }` across primary store, sibling stores, in-tree files, and legacy dirs.
   *
   * @returns {Record<string, number>}
   */
  countByRelPath() {
    /** @type {Record<string, number>} */
    const counts = {};
    const flowIds = new Set();

    if (this.agentsBaseRoot) {
      const specsDir = path.join(this.agentsBaseRoot, this.bundleRel, "specs");
      if (fs.existsSync(specsDir)) {
        for (const ent of fs.readdirSync(specsDir, { withFileTypes: true })) {
          if (ent.isDirectory()) flowIds.add(ent.name);
        }
      }
    }
    const commonDir = this.resolveCommonGitDir();
    if (commonDir && fs.existsSync(commonDir)) {
      const primaryStore = path.join(commonDir, this.feedbackStoreDirName);
      if (fs.existsSync(primaryStore)) {
        for (const ent of fs.readdirSync(primaryStore, { withFileTypes: true })) {
          if (ent.isDirectory()) flowIds.add(ent.name);
        }
      }
    }

    for (const fid of flowIds) {
      const comments = this.listForFlow(fid);
      for (const c of comments) {
        if (c.state !== "open" || c.commentKind === "approval") continue;
        const key = c.relPath || path.posix.join(this.bundleRel, "specs", fid, "spec.md");
        counts[key] = (counts[key] || 0) + 1;
      }
    }

    if (this.legacyReviewsDir && fs.existsSync(this.legacyReviewsDir)) {
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
      const extTag = c.externalSource?.label ? ` [${c.externalSource.label}]` : c.ghPrCommentId ? ` [PR comment]` : "";
      lines.push(`- **${loc}** [${c.commentKind}]${extTag} (${c.authorName || c.authorEmail}): ${c.body}`);
      if (c.quote) lines.push(`  > ${c.quote.replace(/\n/g, " ")}`);
    }
    return lines.join("\n");
  }

  #readAuthorRaw(flowId, slug) {
    let merged = [];
    for (const dir of this.candidateDirsForFlow(flowId)) {
      const filePath = path.join(dir, `${slug}.json`);
      if (!fs.existsSync(filePath)) continue;
      try {
        const list = parseFeedbackJsonText(fs.readFileSync(filePath, "utf8"));
        merged = SpecComment.merge(merged, list);
      } catch {
        // Ignore unreadable author feedback file.
      }
    }
    return merged.map((c) => SpecComment.stripDerived(c));
  }

  #normalizeRel(relPath) {
    const clean = String(relPath || "").replace(/\\/g, "/");
    if (!this.workspaceRoot) return clean.replace(/^\/+/, "");
    const baseRoot = clean.startsWith(".agents/") && this.agentsBaseRoot ? this.agentsBaseRoot : this.workspaceRoot;
    return normalizeRelPath(baseRoot, clean);
  }

  #legacyStorageFileFor(normRel) {
    if (!this.legacyReviewsDir) return null;
    const hash = crypto.createHash("sha256").update(normRel).digest("hex").slice(0, 12);
    const safeSlug = normRel.replace(/[^a-zA-Z0-9_-]+/g, "_").slice(-48);
    return path.join(this.legacyReviewsDir, `${safeSlug}-${hash}.json`);
  }

  #readLegacyForFlow(flowId, viewerEmail = null) {
    const collected = [];
    if (this.legacyReviewsDir && fs.existsSync(this.legacyReviewsDir)) {
      for (const name of fs.readdirSync(this.legacyReviewsDir)) {
        if (!name.endsWith(".json")) continue;
        const data = readJsonSafe(path.join(this.legacyReviewsDir, name));
        if (data?.relPath && this.inferFlowId(data.relPath) === flowId && Array.isArray(data.comments)) {
          collected.push(...data.comments.map((c) => SpecComment.normalize({ ...c, relPath: data.relPath }, { viewerEmail })));
        }
      }
    }
    const flat = this.legacyFlatCommentsFile ? readJsonSafe(this.legacyFlatCommentsFile) : null;
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
    if (!file) throw new Error("Cannot write legacy feedback without workspaceRoot");
    const existing = readJsonSafe(file);
    const list = Array.isArray(existing?.comments) ? existing.comments : [];
    const comment = SpecComment.normalize({ ...input, relPath: normRel });
    list.push(comment);
    writeJsonAtomic(file, { relPath: normRel, comments: list }, 2);
    return comment;
  }
}
