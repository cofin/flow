/**
 * Flow Think MCP - Plan Hooks
 *
 * Integration hooks for the flow-plan command.
 * Provides plan-specific step templates for task breakdown,
 * phase organization, and dependency tracking.
 *
 * @module flow/hooks/plan
 */

import type { FlowThinkStep, StructuredAction } from "../../types.js";

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

/**
 * The purpose type for planning steps.
 */
export const PLAN_PURPOSE = "planning" as const;

/**
 * Step template configuration for planning workflows.
 */
export interface PlanStepTemplate {
  /** Purpose type (always "planning" for plan hooks) */
  purpose: typeof PLAN_PURPOSE;
  /** Human-readable description of this template */
  description: string;
  /** Hints for context field content */
  contextHints: string[];
}

/**
 * Pre-defined step templates for planning workflows.
 */
export const PLAN_STEP_TEMPLATES: Record<string, PlanStepTemplate> = {
  task_breakdown: {
    purpose: PLAN_PURPOSE,
    description: "Break down PRD into implementable tasks",
    contextHints: [
      "PRD summary or key requirements",
      "Scope boundaries",
      "Known constraints",
    ],
  },
  phase_organization: {
    purpose: PLAN_PURPOSE,
    description: "Organize tasks into logical phases for incremental delivery",
    contextHints: [
      "List of identified tasks",
      "Dependencies between tasks",
      "Delivery milestones",
    ],
  },
  dependency_tracking: {
    purpose: PLAN_PURPOSE,
    description: "Map and track dependencies between tasks",
    contextHints: [
      "Task relationships",
      "Blocking dependencies",
      "Critical path identification",
    ],
  },
};

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

/**
 * Task status values matching Flow workflow markers.
 */
export type TaskStatus =
  | "pending"
  | "in_progress"
  | "completed"
  | "blocked"
  | "skipped";

/**
 * Status markers used in plan.md files.
 */
export const STATUS_MARKERS: Record<TaskStatus, string> = {
  pending: "[ ]",
  in_progress: "[~]",
  completed: "[x]",
  blocked: "[!]",
  skipped: "[-]",
};

/**
 * Base input for creating plan steps.
 */
export interface PlanStepInput {
  /** Sequential step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total: number;
  /** Current context */
  context: string;
  /** Reasoning process */
  thought: string;
  /** Expected/actual outcome */
  outcome: string;
  /** Next action (string or structured) */
  next_action: string | StructuredAction;
  /** Rationale for next action */
  rationale: string;
  /** Optional flow ID */
  flow_id?: string;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional confidence (0-1) */
  confidence?: number;
  /** Optional files referenced */
  files_referenced?: string[];
  /** Optional session ID */
  session_id?: string;
}

/**
 * Input for task breakdown step.
 */
export interface TaskBreakdownInput {
  /** Sequential step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total: number;
  /** Summary of the PRD/requirements */
  prd_summary: string;
  /** List of identified tasks */
  identified_tasks: string[];
  /** Optional priority ordering */
  priority_order?: string[];
  /** Next action */
  next_action: string | StructuredAction;
  /** Rationale */
  rationale: string;
  /** Optional flow ID */
  flow_id?: string;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional confidence */
  confidence?: number;
}

/**
 * Phase definition for phase organization.
 */
export interface PhaseDefinition {
  /** Phase name (e.g., "Phase 1: Setup") */
  name: string;
  /** Tasks in this phase */
  tasks: string[];
  /** Optional phase description */
  description?: string;
  /** Whether tasks can run in parallel */
  parallel?: boolean;
}

/**
 * Input for phase organization step.
 */
export interface PhaseOrganizationInput {
  /** Sequential step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total: number;
  /** Defined phases */
  phases: PhaseDefinition[];
  /** Next action */
  next_action: string | StructuredAction;
  /** Rationale */
  rationale: string;
  /** Optional flow ID */
  flow_id?: string;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional confidence */
  confidence?: number;
}

/**
 * Task dependency definition.
 */
export interface TaskDependency {
  /** Task that has dependencies */
  task: string;
  /** Tasks it depends on */
  depends_on: string[];
}

/**
 * Blocked task information.
 */
export interface BlockedTask {
  /** Task that is blocked */
  task: string;
  /** Reason for being blocked */
  reason: string;
}

/**
 * Input for dependency tracking step.
 */
export interface DependencyTrackingInput {
  /** Sequential step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total: number;
  /** Task dependencies */
  dependencies: TaskDependency[];
  /** Optional blocked tasks */
  blocked_by?: BlockedTask[];
  /** Optional critical path */
  critical_path?: string[];
  /** Next action */
  next_action: string | StructuredAction;
  /** Rationale */
  rationale: string;
  /** Optional flow ID */
  flow_id?: string;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional confidence */
  confidence?: number;
}

/**
 * Input for updating task status.
 */
export interface TaskStatusUpdate {
  /** Unique task identifier */
  task_id: string;
  /** Task name/description */
  task_name: string;
  /** New status */
  status: TaskStatus;
  /** Optional reason (for blocked/skipped) */
  reason?: string;
  /** Optional commit SHA (for completed) */
  commit_sha?: string;
  /** Optional Beads ID */
  beads_id?: string;
}

/**
 * Result of task status update.
 */
export interface TaskStatusResult {
  /** Task identifier */
  task_id: string;
  /** Task name */
  task_name: string;
  /** New status */
  status: TaskStatus;
  /** Markdown marker for status */
  marker: string;
  /** Timestamp of update */
  timestamp: string;
  /** Optional reason */
  reason?: string;
  /** Optional commit SHA */
  commit_sha?: string;
  /** Optional Beads ID */
  beads_id?: string;
}

// ─────────────────────────────────────────────────────────────
// Helper Functions
// ─────────────────────────────────────────────────────────────

/**
 * Create a generic plan step with planning purpose.
 *
 * @param input - Step input parameters
 * @returns FlowThinkStep configured for planning
 */
export function createPlanStep(input: PlanStepInput): FlowThinkStep {
  const step: FlowThinkStep = {
    step_number: input.step_number,
    estimated_total: input.estimated_total,
    purpose: PLAN_PURPOSE,
    context: input.context,
    thought: input.thought,
    outcome: input.outcome,
    next_action: input.next_action,
    rationale: input.rationale,
  };

  // Add optional fields
  if (input.flow_id) {
    step.flow_id = input.flow_id;
  }
  if (input.beads_task_id) {
    step.beads_task_id = input.beads_task_id;
  }
  if (input.confidence !== undefined) {
    step.confidence = input.confidence;
  }
  if (input.files_referenced) {
    step.files_referenced = input.files_referenced;
  }
  if (input.session_id) {
    step.session_id = input.session_id;
  }

  return step;
}

/**
 * Create a task breakdown step from PRD analysis.
 *
 * @param input - Task breakdown input
 * @returns FlowThinkStep for task breakdown
 */
export function createTaskBreakdownStep(input: TaskBreakdownInput): FlowThinkStep {
  const taskCount = input.identified_tasks.length;
  const taskList = input.identified_tasks
    .map((task, i) => `${i + 1}. ${task}`)
    .join("\n");

  let outcome = `${taskCount} tasks identified:\n${taskList}`;

  if (input.priority_order && input.priority_order.length > 0) {
    const priorityList = input.priority_order
      .map((task, i) => `${i + 1}. ${task}`)
      .join("\n");
    outcome += `\n\nPriority order:\n${priorityList}`;
  }

  return createPlanStep({
    step_number: input.step_number,
    estimated_total: input.estimated_total,
    context: `Analyzing PRD: ${input.prd_summary}`,
    thought: `Need to break down the requirements into implementable tasks. Identifying atomic units of work that can be tested and committed independently.`,
    outcome,
    next_action: input.next_action,
    rationale: input.rationale,
    flow_id: input.flow_id,
    beads_task_id: input.beads_task_id,
    confidence: input.confidence,
  });
}

/**
 * Create a phase organization step.
 *
 * @param input - Phase organization input
 * @returns FlowThinkStep for phase organization
 */
export function createPhaseOrganizationStep(input: PhaseOrganizationInput): FlowThinkStep {
  const phaseCount = input.phases.length;
  const phaseDetails = input.phases
    .map((phase) => {
      let detail = `- ${phase.name} (${phase.tasks.length} tasks)`;
      if (phase.description) {
        detail += `\n  ${phase.description}`;
      }
      if (phase.parallel) {
        detail += ` [parallel execution]`;
      }
      return detail;
    })
    .join("\n");

  return createPlanStep({
    step_number: input.step_number,
    estimated_total: input.estimated_total,
    context: `After identifying tasks, now organizing tasks into logical phases for incremental delivery.`,
    thought: `Grouping related tasks into phases enables incremental testing, easier review, and better progress tracking. Each phase should be a coherent unit of functionality.`,
    outcome: `${phaseCount} phase${phaseCount === 1 ? "" : "s"} defined:\n${phaseDetails}`,
    next_action: input.next_action,
    rationale: input.rationale,
    flow_id: input.flow_id,
    beads_task_id: input.beads_task_id,
    confidence: input.confidence,
  });
}

/**
 * Create a dependency tracking step.
 *
 * @param input - Dependency tracking input
 * @returns FlowThinkStep for dependency tracking
 */
export function createDependencyTrackingStep(input: DependencyTrackingInput): FlowThinkStep {
  let outcome: string;

  if (input.dependencies.length === 0) {
    outcome = "No task dependencies identified. All tasks can be executed independently.";
  } else {
    const depList = input.dependencies
      .map((dep) => `- ${dep.task} depends on: ${dep.depends_on.join(", ")}`)
      .join("\n");
    outcome = `Task dependencies:\n${depList}`;
  }

  if (input.blocked_by && input.blocked_by.length > 0) {
    const blockedList = input.blocked_by
      .map((b) => `- ${b.task}: ${b.reason}`)
      .join("\n");
    outcome += `\n\nBlocked tasks:\n${blockedList}`;
  }

  if (input.critical_path && input.critical_path.length > 0) {
    outcome += `\n\nCritical path: ${input.critical_path.join(" -> ")}`;
  }

  return createPlanStep({
    step_number: input.step_number,
    estimated_total: input.estimated_total,
    context: `Mapping dependencies between tasks to ensure correct execution order.`,
    thought: `Need to track which tasks depend on others to prevent blocked work and identify the critical path for minimum completion time.`,
    outcome,
    next_action: input.next_action,
    rationale: input.rationale,
    flow_id: input.flow_id,
    beads_task_id: input.beads_task_id,
    confidence: input.confidence,
  });
}

/**
 * Update task status with marker and timestamp.
 *
 * @param update - Task status update
 * @returns Task status result with marker
 */
export function updateTaskStatus(update: TaskStatusUpdate): TaskStatusResult {
  const result: TaskStatusResult = {
    task_id: update.task_id,
    task_name: update.task_name,
    status: update.status,
    marker: STATUS_MARKERS[update.status],
    timestamp: new Date().toISOString(),
  };

  if (update.reason) {
    result.reason = update.reason;
  }
  if (update.commit_sha) {
    result.commit_sha = update.commit_sha;
  }
  if (update.beads_id) {
    result.beads_id = update.beads_id;
  }

  return result;
}
