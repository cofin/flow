/**
 * Flow Think MCP - PRD Integration Hooks
 *
 * Provides hooks that the flow-prd command can use with the flow_think MCP tool.
 * Includes step templates for planning, chapter decomposition, and progress tracking.
 */

import type { FlowThinkStep } from "../../types.js";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

/**
 * Purpose type for PRD-related planning steps.
 */
export const PRD_PURPOSE = "planning" as const;

/**
 * Minimum estimated steps for any PRD.
 */
const MIN_ESTIMATED_STEPS = 3;

/**
 * Base estimated steps before applying heuristics.
 */
const BASE_ESTIMATED_STEPS = 5;

/**
 * Characters per additional step heuristic.
 */
const CHARS_PER_STEP = 100;

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

/**
 * Context information for a PRD (Product Requirements Document).
 */
export interface PrdContext {
  /** Title of the PRD */
  prdTitle: string;

  /** Path to the PRD spec file */
  prdPath: string;

  /** Flow ID (track identifier) */
  flowId: string;

  /** Optional summary/description of the PRD */
  summary?: string;

  /** Optional Beads epic ID for tracking */
  beadsEpicId?: string;
}

/**
 * Information about a chapter/phase in the PRD breakdown.
 */
export interface ChapterInfo {
  /** Chapter number/ID */
  id: number;

  /** Chapter title */
  title: string;

  /** Chapter description */
  description: string;

  /** Optional list of tasks in this chapter */
  tasks?: string[];

  /** Optional estimated number of tasks */
  estimatedTasks?: number;
}

/**
 * Progress tracking for a chapter.
 */
export interface ChapterProgress {
  /** Chapter ID being tracked */
  chapterId: number;

  /** Chapter title */
  chapterTitle: string;

  /** Current status */
  status: "pending" | "in_progress" | "completed" | "blocked";

  /** Number of completed tasks */
  tasksCompleted: number;

  /** Total number of tasks */
  tasksTotal: number;

  /** When the chapter was started */
  startedAt?: string;

  /** When the chapter was completed */
  completedAt?: string;

  /** Reason for being blocked (if status is blocked) */
  blockedReason?: string;
}

/**
 * Options for creating a planning step.
 */
export interface PlanningStepOptions {
  /** Override the step number (default: 1) */
  stepNumber?: number;

  /** Override the estimated total steps */
  estimatedTotal?: number;
}

// ─────────────────────────────────────────────────────────────
// Helper Functions
// ─────────────────────────────────────────────────────────────

/**
 * Estimate the total number of steps based on PRD complexity.
 * Uses a simple heuristic based on summary length.
 */
function estimateTotalSteps(summary?: string): number {
  if (!summary) {
    return BASE_ESTIMATED_STEPS;
  }

  const additionalSteps = Math.floor(summary.length / CHARS_PER_STEP);
  return Math.max(MIN_ESTIMATED_STEPS, BASE_ESTIMATED_STEPS + additionalSteps);
}

/**
 * Calculate progress percentage.
 */
function calculateProgress(completed: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((completed / total) * 100);
}

// ─────────────────────────────────────────────────────────────
// Context Generation
// ─────────────────────────────────────────────────────────────

/**
 * Generate a context string from PRD context.
 * Used as the "context" field in flow_think steps.
 */
export function generatePrdContext(prdContext: PrdContext): string {
  const lines: string[] = [
    `PRD: ${prdContext.prdTitle}`,
    `Flow ID: ${prdContext.flowId}`,
    `Path: ${prdContext.prdPath}`,
  ];

  if (prdContext.beadsEpicId) {
    lines.push(`Beads Epic: ${prdContext.beadsEpicId}`);
  }

  if (prdContext.summary) {
    lines.push("");
    lines.push(`Summary: ${prdContext.summary}`);
  }

  return lines.join("\n");
}

// ─────────────────────────────────────────────────────────────
// Step Templates
// ─────────────────────────────────────────────────────────────

/**
 * Create the initial planning step for a PRD.
 * This is typically the first step when starting flow-prd.
 */
export function createPlanningStep(
  prdContext: PrdContext,
  options: PlanningStepOptions = {}
): FlowThinkStep {
  const stepNumber = options.stepNumber ?? 1;
  const estimatedTotal = options.estimatedTotal ?? estimateTotalSteps(prdContext.summary);

  const step: FlowThinkStep = {
    step_number: stepNumber,
    estimated_total: estimatedTotal,
    purpose: PRD_PURPOSE,
    context: generatePrdContext(prdContext),
    thought: `Beginning PRD analysis for "${prdContext.prdTitle}". Need to breakdown the requirements into logical chapters/phases that can be implemented incrementally. Each chapter should be cohesive and testable.`,
    outcome: `Identified PRD "${prdContext.prdTitle}" as the target for structured planning. Will decompose into chapters with clear tasks.`,
    next_action: "Analyze PRD requirements and identify chapter structure for implementation",
    rationale: "Breaking down a PRD into chapters enables incremental development, clear progress tracking, and manageable work units that follow TDD principles.",
    flow_id: prdContext.flowId,
  };

  if (prdContext.beadsEpicId) {
    step.beads_task_id = prdContext.beadsEpicId;
  }

  return step;
}

/**
 * Create a step documenting the chapter decomposition.
 * Used after analyzing the PRD and identifying chapters.
 */
export function createChapterDecompositionStep(
  prdContext: PrdContext,
  chapters: ChapterInfo[],
  stepNumber: number
): FlowThinkStep {
  const chapterList = chapters
    .map((ch) => `  ${ch.id}. ${ch.title}: ${ch.description}`)
    .join("\n");

  const chapterContext = chapters.length > 0
    ? `\n\nChapters identified:\n${chapterList}`
    : "\n\nNo chapters identified yet.";

  const step: FlowThinkStep = {
    step_number: stepNumber,
    estimated_total: stepNumber + chapters.length + 2, // Chapters + validation + completion
    purpose: PRD_PURPOSE,
    context: generatePrdContext(prdContext) + chapterContext,
    thought: `Decomposed PRD into ${chapters.length} chapter(s). Each chapter represents a logical phase of implementation with clear boundaries and testable outcomes.`,
    outcome: `PRD decomposed into ${chapters.length} chapter(s) for structured implementation.`,
    next_action: chapters.length > 0
      ? `Begin implementation of Chapter 1: ${chapters[0]?.title ?? "TBD"}`
      : "Define chapters for this PRD",
    rationale: "Chapter decomposition provides clear milestones, enables progress tracking, and ensures each phase can be independently verified before proceeding.",
    flow_id: prdContext.flowId,
  };

  if (prdContext.beadsEpicId) {
    step.beads_task_id = prdContext.beadsEpicId;
  }

  return step;
}

/**
 * Create a step tracking chapter progress.
 * Used to record progress on a specific chapter.
 */
export function trackChapterProgress(
  prdContext: PrdContext,
  progress: ChapterProgress,
  stepNumber: number
): FlowThinkStep {
  const percentage = calculateProgress(progress.tasksCompleted, progress.tasksTotal);
  const isComplete = progress.status === "completed";
  const isBlocked = progress.status === "blocked";

  let thought: string;
  if (isBlocked && progress.blockedReason) {
    thought = `Chapter ${progress.chapterId} is blocked: ${progress.blockedReason}. Need to resolve blocker before proceeding.`;
  } else if (isComplete) {
    thought = `Chapter ${progress.chapterId} "${progress.chapterTitle}" completed successfully. All ${progress.tasksTotal} tasks finished.`;
  } else {
    thought = `Tracking progress on Chapter ${progress.chapterId} "${progress.chapterTitle}". Currently ${progress.tasksCompleted}/${progress.tasksTotal} tasks completed (${percentage}%).`;
  }

  let outcome: string;
  if (isComplete) {
    outcome = `Chapter ${progress.chapterId} complete (100%). All tasks verified and passing.`;
  } else if (isBlocked) {
    outcome = `Chapter ${progress.chapterId} blocked at ${percentage}% (${progress.tasksCompleted}/${progress.tasksTotal} tasks).`;
  } else {
    outcome = `Chapter ${progress.chapterId} progress: ${percentage}% (${progress.tasksCompleted}/${progress.tasksTotal} tasks).`;
  }

  const step: FlowThinkStep = {
    step_number: stepNumber,
    estimated_total: stepNumber + (progress.tasksTotal - progress.tasksCompleted) + 1,
    purpose: PRD_PURPOSE,
    context: `${generatePrdContext(prdContext)}\n\nChapter ${progress.chapterId}: ${progress.chapterTitle}\nStatus: ${progress.status}\nProgress: ${progress.tasksCompleted}/${progress.tasksTotal} (${percentage}%)`,
    thought,
    outcome,
    next_action: isComplete
      ? "Proceed to next chapter or finalize PRD"
      : isBlocked
        ? `Resolve blocker: ${progress.blockedReason ?? "Unknown"}`
        : `Continue with remaining ${progress.tasksTotal - progress.tasksCompleted} tasks`,
    rationale: "Tracking chapter progress enables visibility into implementation status, helps identify blockers early, and provides data for project planning.",
    flow_id: prdContext.flowId,
  };

  if (prdContext.beadsEpicId) {
    step.beads_task_id = prdContext.beadsEpicId;
  }

  return step;
}
