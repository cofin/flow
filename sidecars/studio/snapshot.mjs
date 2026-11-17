/**
 * Slim compatibility facade over `SpecEngine`, `SpecFeedbackStore`, `WorkspaceRegistry`,
 * and shared `core/` helpers. Preserves public exports consumed by `router.mjs`,
 * `vscode-extension/extension.mjs`, and existing integration tests.
 */

import fs from "node:fs";
import path from "node:path";

import { detectWorkspacePython } from "./bridges/python.mjs";
import {
  deriveWorkspaceId,
  isInternalSidecarPath,
  parseClaimIdentity,
  readJsonSafe,
  readStudioLiveState,
  runtimeBaseDir,
  toPosixRelative,
  uriToWorkspacePath,
  walkMarkdownFiles,
  workspaceRuntimeId,
} from "./core/fs-io.mjs";
import { extractTruthBlock, parseFrontmatter } from "./core/frontmatter.mjs";
import { resolveWorktreeContext } from "./core/worktree.mjs";
import { SpecFeedbackStore } from "./spec/feedback.mjs";
import { SpecEngine } from "./spec/spec-engine.mjs";
import { WorkspaceRegistry } from "./workspaces.mjs";

export {
  deriveWorkspaceId,
  extractTruthBlock,
  isInternalSidecarPath,
  parseClaimIdentity,
  parseFrontmatter,
  readStudioLiveState,
  resolveWorktreeContext,
  runtimeBaseDir,
  uriToWorkspacePath,
  WorkspaceRegistry,
  workspaceRuntimeId,
};

/**
 * Safely read bundle Markdown documents via `SpecEngine`.
 */
export class SpecMarkdownReader {
  /**
   * @param {string} workspaceRoot
   * @param {string} relPath
   */
  static read(workspaceRoot, relPath) {
    return new SpecEngine(workspaceRoot).readDocument(relPath);
  }
}

/**
 * Legacy wrapper delegating review comments to `SpecFeedbackStore`.
 */
export class ReviewCommentsStore extends SpecFeedbackStore {
  /**
   * @param {string} relPath
   * @param {string} commentId
   * @param {boolean} [resolved]
   */
  setResolved(relPath, commentId, resolved = true) {
    return this.setResolvedOrUpdate(relPath, commentId, resolved);
  }
}

/**
 * Legacy wrapper delegating spec scaffolding to `SpecEngine`.
 */
export class SpecScaffoldWriter {
  /**
   * @param {string} workspaceRoot
   * @param {Record<string, any>} payload
   */
  static create(workspaceRoot, payload) {
    return new SpecEngine(workspaceRoot).scaffold(payload);
  }
}

/**
 * Build a complete present-tense Studio bundle snapshot for `workspaceRoot`.
 */
export class BundleSnapshotBuilder {
  /**
   * @param {string} workspaceRoot
   */
  static build(workspaceRoot) {
    const engine = new SpecEngine(workspaceRoot);
    const root = engine.workspace;
    const worktree = engine.worktree;
    const agentsBaseRoot = engine.effectiveRoot;
    const workspaceId = deriveWorkspaceId(root);
    const agentsDir = path.join(agentsBaseRoot, ".agents");
    const setupState = readJsonSafe(path.join(agentsDir, "setup-state.json")) || {};
    const bundleRel = engine.bundleRel;
    const bundleRoot = engine.bundleDir;
    const hasBundle = fs.existsSync(bundleRoot);
    const pythonInfo = detectWorkspacePython(
      worktree.mainWorktree && !fs.existsSync(path.join(root, ".venv")) ? worktree.mainWorktree : root,
    );
    const liveState = readStudioLiveState(agentsBaseRoot, { agentsDir });
    const feedbackStore = engine.feedback;
    const commentCounts = feedbackStore.countByRelPath();

    const rawSpecs = engine.listSpecs({ includeArchived: false });
    const specs = rawSpecs.map((spec) => {
      const chapters = spec.chapters.map((ch) => ({
        chapterId: ch.chapter_id,
        title: ch.title,
        state: ch.state,
        planningStatus: ch.planning_status,
        planningQuality: ch.planning_quality,
        planningDegradedReason: ch.planning_degraded_reason,
        dependsOnChapters: ch.depends_on_chapters,
        lastReviewedCommit: ch.last_reviewed_commit,
        relPath: ch.rel_path,
        unresolvedComments: ch.rel_path ? commentCounts[ch.rel_path] || 0 : 0,
        tasks: ch.tasks.map(formatSnapshotTask),
        completedTasks: ch.task_counts.completed,
        totalTasks: ch.task_counts.total,
      }));
      const directTasks = spec.tasks.map(formatSnapshotTask);
      const allTasks = chapters.length > 0 ? chapters.flatMap((c) => c.tasks) : directTasks;
      const nextChapter =
        chapters.find((c) => c.chapterId === spec.current_chapter && c.state !== "completed") ||
        chapters.find((c) => c.state === "active" || c.state === "in_progress") ||
        chapters.find((c) => c.state !== "completed") ||
        null;

      return {
        flowId: spec.flow_id,
        title: spec.title,
        type: spec.type,
        description: spec.description,
        state: spec.state,
        status: spec.status,
        planningQuality: spec.planning_quality,
        planningDegradedReason: spec.planning_degraded_reason,
        plannedWithModel: spec.planned_with_model,
        parentPrd: spec.parent_prd,
        hasChapters: spec.has_chapters,
        currentChapter: spec.current_chapter,
        lastReviewedCommit: spec.last_reviewed_commit,
        relPath: spec.rel_path,
        unresolvedComments: commentCounts[spec.rel_path] || 0,
        chapters,
        tasks: directTasks,
        completedTasks: spec.task_counts.completed,
        totalTasks: spec.task_counts.total,
        recommendedAction: buildRecommendedAction(spec.flow_id, spec.type, spec.state, chapters, nextChapter, allTasks),
      };
    });

    const knowledge = [];
    for (const sub of ["knowledge", "decisions", "research", "wiki"]) {
      const subDir = path.join(bundleRoot, sub);
      for (const mdFile of walkMarkdownFiles(subDir)) {
        if (path.basename(mdFile) === "index.md") continue;
        const raw = fs.readFileSync(mdFile, "utf8");
        const { frontmatter, body } = parseFrontmatter(raw);
        const relPath = toPosixRelative(agentsBaseRoot, mdFile);
        const conceptId = toPosixRelative(bundleRoot, mdFile).replace(/\.md$/i, "");
        knowledge.push({
          entryId: `${workspaceId}:${conceptId}`,
          conceptId,
          type: String(frontmatter.type || (sub === "decisions" ? "Decision" : sub === "research" ? "Research" : "Concept")),
          title: String(frontmatter.title || body.match(/^#\s+(.+?)\s*$/m)?.[1] || path.basename(mdFile, ".md")),
          description: String(frontmatter.description || ""),
          status: String(frontmatter.status || "draft"),
          tags: Array.isArray(frontmatter.tags) ? frontmatter.tags.map(String) : [],
          truthBlock: extractTruthBlock(body),
          sourcesCount: Array.isArray(frontmatter.sources) ? frontmatter.sources.length : 0,
          relPath,
          unresolvedComments: commentCounts[relPath] || 0,
        });
      }
    }

    const activeSpec = specs.find((s) => s.state === "active" || s.state === "in_progress") || specs[0] || null;
    return {
      generatedAt: new Date().toISOString(),
      workspaceId,
      repoName: path.basename(root),
      workspaceRoot: root,
      worktree,
      bundleInitialized: hasBundle,
      bundleRoot: bundleRel,
      setupState,
      python: pythonInfo,
      liveState,
      activeFlowId: activeSpec?.flowId || null,
      specs,
      knowledge,
      counts: {
        specs: specs.length,
        activeSpecs: specs.filter((s) => s.state === "active" || s.state === "in_progress").length,
        degradedSpecs: specs.filter((s) => s.planningQuality === "degraded").length,
        knowledge: knowledge.length,
        unresolvedComments: Object.values(commentCounts).reduce((acc, v) => acc + v, 0),
      },
    };
  }
}

function formatSnapshotTask(t) {
  return {
    id: t.id,
    shortId: t.short_id,
    slug: t.filename ? t.filename.replace(/\.md$/i, "") : t.stem,
    title: t.title,
    state: t.state,
    claimedBy: t.claimed_by,
    claimedAt: t.claimed_at,
    claimIdentity: parseClaimIdentity(t.claimed_by),
    commitSha: t.commit,
    verificationStrategy: t.verification_strategy,
    files: t.files,
    readSet: t.read_set,
    relPath: t.rel_path,
  };
}

function buildRecommendedAction(flowId, docKind, state, chapters, nextChapter, allTasks) {
  if (docKind.toUpperCase() === "PRD") {
    return { label: "Spec Next Child Flow", command: `/flow:spec --parent ${flowId}` };
  }
  if (allTasks.length === 0 && chapters.length === 0) {
    return { label: "Generate Spec Blueprint", command: `/flow:spec ${flowId}` };
  }
  const completed = allTasks.filter((t) => t.state === "completed").length;
  if (allTasks.length > 0 && completed === allTasks.length && state !== "completed") {
    return { label: "Run Zero-Context Review", command: `/flow:review ${flowId}` };
  }
  if (nextChapter) {
    return {
      label: `Implement ${nextChapter.chapterId}`,
      command: `/flow:implement ${flowId} ${nextChapter.chapterId}`,
      chapterId: nextChapter.chapterId,
    };
  }
  if (state === "completed") {
    return { label: "Finish & Resynthesize", command: `/flow:finish ${flowId}` };
  }
  return { label: "Implement Next Slice", command: `/flow:implement ${flowId}` };
}
