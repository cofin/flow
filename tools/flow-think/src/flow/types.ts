/**
 * Flow Think MCP - Flow-Specific Type Definitions
 *
 * Defines Flow-specific purpose types, context structures, and utilities
 * that map to Flow commands and workflow concepts.
 */

// ─────────────────────────────────────────────────────────────
// Flow Purpose Types
// ─────────────────────────────────────────────────────────────

/**
 * Flow-specific purpose types with descriptions.
 * These map to specific Flow commands and workflow phases.
 */
export const FLOW_PURPOSE_TYPES = {
  planning: "Creating PRD and implementation plan via flow-prd",
  research: "Pre-PRD research and investigation via flow-research",
  implement: "TDD implementation workflow via flow-implement",
  debug: "Debugging and troubleshooting issues",
  analysis: "Code analysis and architecture review",
  reflection: "Pattern extraction and learnings capture",
  decision: "Making architectural or implementation decisions",
  validation: "Validating project integrity via flow-validate",
} as const;

export type FlowPurpose = keyof typeof FLOW_PURPOSE_TYPES;

/**
 * Maps Flow purposes to their corresponding Flow commands.
 */
export const FLOW_PURPOSE_TO_COMMAND: Record<FlowPurpose, string[]> = {
  planning: ["flow-prd", "flow-plan"],
  research: ["flow-research"],
  implement: ["flow-implement"],
  debug: ["flow-debug"],
  analysis: ["flow-analyze"],
  reflection: ["flow-archive", "flow-distill"],
  decision: ["flow-revise", "flow-decide"],
  validation: ["flow-validate"],
};

/**
 * Check if a string is a valid Flow purpose.
 */
export function isFlowPurpose(purpose: string): purpose is FlowPurpose {
  if (typeof purpose !== "string") return false;
  return purpose in FLOW_PURPOSE_TYPES;
}

/**
 * Get Flow commands for a given purpose.
 */
export function getFlowCommand(purpose: string): string[] | undefined {
  if (!isFlowPurpose(purpose)) return undefined;
  return FLOW_PURPOSE_TO_COMMAND[purpose];
}

/**
 * Get the description for a Flow purpose.
 */
export function getFlowPurposeDescription(purpose: string): string | undefined {
  if (!isFlowPurpose(purpose)) return undefined;
  return FLOW_PURPOSE_TYPES[purpose];
}

// ─────────────────────────────────────────────────────────────
// Flow Status Types
// ─────────────────────────────────────────────────────────────

/**
 * Flow phase status values.
 */
export const FLOW_PHASE_STATUSES = [
  "pending",
  "in_progress",
  "completed",
  "blocked",
  "skipped",
] as const;

export type FlowPhaseStatus = (typeof FLOW_PHASE_STATUSES)[number];

/**
 * Flow task status values.
 * Maps to markdown markers:
 * - [ ] pending
 * - [~] in_progress
 * - [x] completed
 * - [!] blocked
 * - [-] skipped
 */
export const FLOW_TASK_STATUSES = [
  "pending",
  "in_progress",
  "completed",
  "blocked",
  "skipped",
] as const;

export type FlowTaskStatus = (typeof FLOW_TASK_STATUSES)[number];

/**
 * Flow track status values.
 */
export const FLOW_TRACK_STATUSES = [
  "pending",
  "in_progress",
  "completed",
  "blocked",
  "archived",
] as const;

export type FlowTrackStatus = (typeof FLOW_TRACK_STATUSES)[number];

// ─────────────────────────────────────────────────────────────
// Flow Context Types
// ─────────────────────────────────────────────────────────────

/**
 * Current Flow execution context.
 * Tracks which track, phase, and task are active.
 */
export interface FlowContext {
  /** Current track ID (format: shortname_YYYYMMDD) */
  track_id: string;

  /** Current phase number */
  current_phase: number;

  /** Current task ID (format: phase.task, e.g., "1.2") */
  current_task: string;

  /** Path to spec directory */
  spec_path: string;

  /** Linked Beads epic ID (optional) */
  beads_epic_id?: string;
}

/**
 * Create a FlowContext with required and optional fields.
 */
export function createFlowContext(params: FlowContext): FlowContext {
  return {
    track_id: params.track_id,
    current_phase: params.current_phase,
    current_task: params.current_task,
    spec_path: params.spec_path,
    beads_epic_id: params.beads_epic_id,
  };
}

// ─────────────────────────────────────────────────────────────
// Flow Task Types
// ─────────────────────────────────────────────────────────────

/**
 * A task within a Flow phase.
 */
export interface FlowTask {
  /** Task ID (format: phase.task, e.g., "1.2") */
  id: string;

  /** Task description */
  description: string;

  /** Current task status */
  status: FlowTaskStatus;

  /** Phase number this task belongs to */
  phase: number;

  /** Commit SHA if task is completed */
  commit_sha?: string;

  /** Files affected by this task */
  files?: string[];

  /** Task IDs this task depends on */
  dependencies?: string[];

  /** Linked Beads task ID */
  beads_task_id?: string;

  /** Reason if task is blocked */
  blocked_reason?: string;

  /** Reason if task is skipped */
  skip_reason?: string;
}

/**
 * Create a FlowTask with defaults.
 */
export function createFlowTask(
  params: Omit<FlowTask, "status"> & { status?: FlowTaskStatus }
): FlowTask {
  return {
    id: params.id,
    description: params.description,
    status: params.status ?? "pending",
    phase: params.phase,
    commit_sha: params.commit_sha,
    files: params.files,
    dependencies: params.dependencies,
    beads_task_id: params.beads_task_id,
    blocked_reason: params.blocked_reason,
    skip_reason: params.skip_reason,
  };
}

// ─────────────────────────────────────────────────────────────
// Flow Phase Types
// ─────────────────────────────────────────────────────────────

/**
 * Execution mode for a phase.
 */
export type FlowPhaseExecutionMode = "sequential" | "parallel";

/**
 * A phase within a Flow track.
 */
export interface FlowPhase {
  /** Phase number */
  number: number;

  /** Phase name */
  name: string;

  /** Current phase status */
  status: FlowPhaseStatus;

  /** Tasks in this phase */
  tasks: FlowTask[];

  /** Execution mode (sequential or parallel) */
  execution_mode: FlowPhaseExecutionMode;

  /** Git tag created at phase checkpoint */
  checkpoint_tag?: string;
}

/**
 * Create a FlowPhase with defaults.
 */
export function createFlowPhase(
  params: Pick<FlowPhase, "number" | "name"> &
    Partial<Omit<FlowPhase, "number" | "name">>
): FlowPhase {
  return {
    number: params.number,
    name: params.name,
    status: params.status ?? "pending",
    tasks: params.tasks ?? [],
    execution_mode: params.execution_mode ?? "sequential",
    checkpoint_tag: params.checkpoint_tag,
  };
}

/**
 * Check if all tasks in a phase are complete.
 * A phase is complete if all tasks are either completed or skipped.
 */
export function isFlowPhaseComplete(phase: FlowPhase): boolean {
  if (phase.tasks.length === 0) return true;

  return phase.tasks.every(
    (task) => task.status === "completed" || task.status === "skipped"
  );
}

/**
 * Calculate phase progress as a percentage.
 * Completed and skipped tasks count towards progress.
 */
export function getFlowPhaseProgress(phase: FlowPhase): number {
  if (phase.tasks.length === 0) return 100;

  const completedCount = phase.tasks.filter(
    (task) => task.status === "completed" || task.status === "skipped"
  ).length;

  return (completedCount / phase.tasks.length) * 100;
}

// ─────────────────────────────────────────────────────────────
// Flow Track Types
// ─────────────────────────────────────────────────────────────

/**
 * A Flow track (feature, bug fix, refactor, etc.).
 */
export interface FlowTrack {
  /** Track ID (format: shortname_YYYYMMDD) */
  id: string;

  /** Human-readable track name */
  name: string;

  /** Current track status */
  status: FlowTrackStatus;

  /** ISO timestamp when track was created */
  created_at: string;

  /** ISO timestamp when track was completed */
  completed_at?: string;

  /** Phases in this track */
  phases: FlowPhase[];

  /** Linked Beads epic ID */
  beads_epic_id?: string;

  /** Path to spec directory */
  spec_path?: string;
}
