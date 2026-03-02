/**
 * Flow Think MCP - Flow Implement Hooks
 *
 * TDD-specific step templates and workflow helpers for the flow-implement command.
 * Provides structured reasoning steps for the Red-Green-Refactor-Verify TDD cycle.
 */

import type { FlowThinkStep, StructuredAction } from "../../types.js";

// ─────────────────────────────────────────────────────────────
// TDD Phase Types and Constants
// ─────────────────────────────────────────────────────────────

/**
 * TDD phase identifiers.
 */
export type TDDPhase = "red" | "green" | "refactor" | "verify";

/**
 * TDD phase metadata.
 */
export interface TDDPhaseInfo {
  /** Purpose category (always "implement") */
  purpose: "implement";
  /** Human-readable description of this phase */
  description: string;
  /** Expected actions in this phase */
  typical_actions: string[];
}

/**
 * TDD phase definitions with metadata.
 */
export const TDD_PHASES: Record<TDDPhase, TDDPhaseInfo> = {
  red: {
    purpose: "implement",
    description: "Write a failing test that defines the expected behavior",
    typical_actions: [
      "Write test case",
      "Run test to verify it fails",
      "Ensure test fails for the right reason",
    ],
  },
  green: {
    purpose: "implement",
    description: "Write the minimum code necessary to make the test pass",
    typical_actions: [
      "Implement just enough code",
      "Run tests to verify pass",
      "Avoid premature optimization",
    ],
  },
  refactor: {
    purpose: "implement",
    description: "Improve code quality while keeping tests green",
    typical_actions: [
      "Improve naming and structure",
      "Remove duplication (DRY)",
      "Run tests after each change",
    ],
  },
  verify: {
    purpose: "implement",
    description: "Verify coverage and overall code quality",
    typical_actions: [
      "Run coverage report",
      "Check coverage targets met",
      "Review test quality",
    ],
  },
};

/**
 * TDD phase execution order.
 */
export const TDD_PHASE_ORDER: readonly TDDPhase[] = [
  "red",
  "green",
  "refactor",
  "verify",
] as const;

// ─────────────────────────────────────────────────────────────
// Coverage Types
// ─────────────────────────────────────────────────────────────

/**
 * Code coverage information.
 */
export interface CoverageInfo {
  /** Overall coverage percentage */
  total: number;
  /** Statement coverage percentage */
  statements?: number;
  /** Branch coverage percentage */
  branches?: number;
  /** Function coverage percentage */
  functions?: number;
  /** Line coverage percentage */
  lines?: number;
}

// ─────────────────────────────────────────────────────────────
// TDD Cycle State Types
// ─────────────────────────────────────────────────────────────

/**
 * State of a TDD cycle for a task.
 */
export interface TDDCycleState {
  /** Task ID being implemented */
  task_id: string;
  /** Current TDD phase */
  current_phase: TDDPhase;
  /** Cycle number (for multiple iterations) */
  cycle_number: number;
  /** Phases completed in this cycle */
  phases_completed: TDDPhase[];
  /** When this cycle started */
  started_at: string;
  /** When this cycle completed (if done) */
  completed_at?: string;
}

/**
 * Outcome of a TDD implementation.
 */
export interface TDDOutcome {
  /** Task ID that was implemented */
  task_id: string;
  /** Task name/description */
  task_name: string;
  /** Whether implementation succeeded */
  success: boolean;
  /** Number of TDD cycles completed */
  cycles_completed: number;
  /** Final code coverage percentage */
  final_coverage: number;
  /** Number of tests added */
  tests_added: number;
  /** Files modified during implementation */
  files_modified: string[];
  /** Duration in milliseconds */
  duration_ms?: number;
  /** Failure reason if not successful */
  failure_reason?: string;
  /** Learnings captured during implementation */
  learnings?: string[];
}

/**
 * Validation result for TDD transitions.
 */
export interface TDDTransitionResult {
  /** Whether the transition is valid */
  valid: boolean;
  /** Error message if invalid */
  error?: string;
}

// ─────────────────────────────────────────────────────────────
// Step Creation Functions
// ─────────────────────────────────────────────────────────────

/**
 * Options for creating a TDD step.
 */
export interface TDDStepOptions {
  /** TDD phase for this step */
  phase: TDDPhase;
  /** Step number in the reasoning sequence */
  step_number: number;
  /** Estimated total steps */
  estimated_total?: number;
  /** Current context */
  context: string;
  /** Current thought process */
  thought: string;
  /** Expected/actual outcome */
  outcome: string;
  /** Next action to take */
  next_action: string | StructuredAction;
  /** Rationale for next action */
  rationale: string;
  /** Optional confidence level */
  confidence?: number;
  /** Files referenced in this step */
  files_referenced?: string[];
  /** Beads task ID */
  beads_task_id?: string;
  /** Flow ID */
  flow_id?: string;
  /** Whether this is the final step */
  is_final_step?: boolean;
  /** Additional external context */
  additional_external_context?: Record<string, unknown>;
}

/**
 * Create a TDD step with standard implement purpose.
 */
export function createTDDStep(options: TDDStepOptions): FlowThinkStep {
  const phaseInfo = TDD_PHASES[options.phase];

  const step: FlowThinkStep = {
    step_number: options.step_number,
    estimated_total: options.estimated_total ?? 4,
    purpose: phaseInfo.purpose,
    context: options.context,
    thought: options.thought,
    outcome: options.outcome,
    next_action: options.next_action,
    rationale: options.rationale,
    confidence: options.confidence,
    files_referenced: options.files_referenced,
    beads_task_id: options.beads_task_id,
    flow_id: options.flow_id,
    external_context: {
      tdd_phase: options.phase,
      tdd_phase_description: phaseInfo.description,
      ...options.additional_external_context,
    },
  };

  if (options.is_final_step) {
    step.is_final_step = options.is_final_step;
  }

  return step;
}

/**
 * Options for creating a red phase step.
 */
export interface RedPhaseOptions {
  /** Step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total?: number;
  /** Description of the test being written */
  test_description: string;
  /** Path to the test file */
  test_file: string;
  /** Current context */
  context: string;
  /** Optional confidence level */
  confidence?: number;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional Flow ID */
  flow_id?: string;
}

/**
 * Create a step for the red phase (write failing test).
 */
export function createRedPhaseStep(options: RedPhaseOptions): FlowThinkStep {
  return createTDDStep({
    phase: "red",
    step_number: options.step_number,
    estimated_total: options.estimated_total ?? 4,
    context: options.context,
    thought: `Writing a failing test to define expected behavior. The test should clearly express the requirement: "${options.test_description}"`,
    outcome: `Test created: ${options.test_description}`,
    next_action: {
      tool: "Bash",
      action: "Run test to verify it fails",
      expectedOutput: "Test should fail with clear error message",
    },
    rationale:
      "TDD requires writing a failing test first to clearly define the expected behavior before implementation",
    confidence: options.confidence,
    files_referenced: [options.test_file],
    beads_task_id: options.beads_task_id,
    flow_id: options.flow_id,
  });
}

/**
 * Options for creating a green phase step.
 */
export interface GreenPhaseOptions {
  /** Step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total?: number;
  /** Approach for implementation */
  implementation_approach: string;
  /** Target file for implementation */
  target_file: string;
  /** Current context */
  context: string;
  /** Optional confidence level */
  confidence?: number;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional Flow ID */
  flow_id?: string;
}

/**
 * Create a step for the green phase (implement to pass).
 */
export function createGreenPhaseStep(options: GreenPhaseOptions): FlowThinkStep {
  return createTDDStep({
    phase: "green",
    step_number: options.step_number,
    estimated_total: options.estimated_total ?? 4,
    context: options.context,
    thought:
      "Implementing the minimum code necessary to make the test pass. Focus on simplicity over optimization.",
    outcome: `Implementation approach: ${options.implementation_approach}`,
    next_action: {
      tool: "Bash",
      action: "Run tests to verify they pass",
      expectedOutput: "All tests should pass",
    },
    rationale:
      "Write just enough code to make the test pass. Premature optimization is the root of all evil.",
    confidence: options.confidence,
    files_referenced: [options.target_file],
    beads_task_id: options.beads_task_id,
    flow_id: options.flow_id,
  });
}

/**
 * Options for creating a refactor phase step.
 */
export interface RefactorPhaseOptions {
  /** Step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total?: number;
  /** Goals for refactoring */
  refactor_goals: string[];
  /** Files affected by refactoring */
  affected_files: string[];
  /** Current context */
  context: string;
  /** Optional confidence level */
  confidence?: number;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional Flow ID */
  flow_id?: string;
}

/**
 * Create a step for the refactor phase.
 */
export function createRefactorPhaseStep(
  options: RefactorPhaseOptions
): FlowThinkStep {
  const goalsText =
    options.refactor_goals.length > 0
      ? `Refactoring goals: ${options.refactor_goals.join(", ")}`
      : "No refactoring needed - code is clean";

  return createTDDStep({
    phase: "refactor",
    step_number: options.step_number,
    estimated_total: options.estimated_total ?? 4,
    context: options.context,
    thought:
      "Improving code quality while tests pass. Running tests after each change to ensure nothing breaks.",
    outcome: goalsText,
    next_action: {
      tool: "Bash",
      action: "Run tests after refactoring",
      expectedOutput: "All tests should still pass",
    },
    rationale:
      "Refactoring improves code quality without changing behavior. Tests ensure we don't break anything.",
    confidence: options.confidence,
    files_referenced: options.affected_files,
    beads_task_id: options.beads_task_id,
    flow_id: options.flow_id,
  });
}

/**
 * Options for creating a coverage verification step.
 */
export interface CoverageVerificationOptions {
  /** Step number */
  step_number: number;
  /** Estimated total steps */
  estimated_total?: number;
  /** Coverage information */
  coverage: CoverageInfo;
  /** Target coverage percentage (default: 80) */
  target_coverage?: number;
  /** Current context */
  context: string;
  /** Optional Beads task ID */
  beads_task_id?: string;
  /** Optional Flow ID */
  flow_id?: string;
}

/**
 * Create a step for coverage verification.
 */
export function createCoverageVerificationStep(
  options: CoverageVerificationOptions
): FlowThinkStep {
  const target = options.target_coverage ?? 80;
  const coverageMet = options.coverage.total >= target;
  const confidence = coverageMet ? 0.9 : 0.5;

  const thought = coverageMet
    ? `Coverage of ${options.coverage.total}% meets target of ${target}%. TDD cycle complete.`
    : `Coverage of ${options.coverage.total}% is below target of ${target}%. Need to add more tests.`;

  const nextAction = coverageMet
    ? "Mark task complete and update plan.md"
    : "Write additional tests to improve coverage";

  return createTDDStep({
    phase: "verify",
    step_number: options.step_number,
    estimated_total: options.estimated_total ?? 4,
    context: options.context,
    thought,
    outcome: `Coverage: ${options.coverage.total}% (target: ${target}%)`,
    next_action: nextAction,
    rationale: coverageMet
      ? "Coverage target met. Implementation is complete with adequate test coverage."
      : "Coverage target not met. Need additional tests to ensure code quality.",
    confidence,
    is_final_step: coverageMet,
    beads_task_id: options.beads_task_id,
    flow_id: options.flow_id,
    additional_external_context: {
      coverage: options.coverage,
      target_coverage: target,
      coverage_met: coverageMet,
    },
  });
}

// ─────────────────────────────────────────────────────────────
// TDD Cycle State Management
// ─────────────────────────────────────────────────────────────

/**
 * Create initial TDD cycle state for a task.
 */
export function createTDDCycleState(
  taskId: string,
  cycleNumber: number = 1
): TDDCycleState {
  return {
    task_id: taskId,
    current_phase: "red",
    cycle_number: cycleNumber,
    phases_completed: [],
    started_at: new Date().toISOString(),
  };
}

/**
 * Advance to the next TDD phase.
 */
export function advanceTDDCycle(state: TDDCycleState): TDDCycleState {
  const newState = { ...state };
  const currentIndex = TDD_PHASE_ORDER.indexOf(state.current_phase);

  // Mark current phase as completed
  if (!newState.phases_completed.includes(state.current_phase)) {
    newState.phases_completed = [...newState.phases_completed, state.current_phase];
  }

  // Move to next phase or complete
  if (currentIndex < TDD_PHASE_ORDER.length - 1) {
    newState.current_phase = TDD_PHASE_ORDER[currentIndex + 1];
  } else {
    // Cycle complete
    newState.completed_at = new Date().toISOString();
  }

  return newState;
}

/**
 * Get progress percentage for a TDD cycle.
 */
export function getTDDCycleProgress(state: TDDCycleState): number {
  return Math.round((state.phases_completed.length / TDD_PHASE_ORDER.length) * 100);
}

/**
 * Validate a TDD phase transition.
 */
export function validateTDDTransition(
  from: TDDPhase,
  to: TDDPhase
): TDDTransitionResult {
  // Always allow going back to red (start new iteration)
  if (to === "red") {
    return { valid: true };
  }

  // Normal forward progression
  const fromIndex = TDD_PHASE_ORDER.indexOf(from);
  const toIndex = TDD_PHASE_ORDER.indexOf(to);

  if (toIndex === fromIndex + 1) {
    return { valid: true };
  }

  return {
    valid: false,
    error: `Invalid transition from ${from} to ${to}. Expected ${TDD_PHASE_ORDER[fromIndex + 1]} or red.`,
  };
}

/**
 * Check if a TDD cycle is complete.
 */
export function isTDDComplete(state: TDDCycleState): boolean {
  return (
    state.phases_completed.length === TDD_PHASE_ORDER.length &&
    state.completed_at !== undefined
  );
}

// ─────────────────────────────────────────────────────────────
// Output Formatting
// ─────────────────────────────────────────────────────────────

/**
 * Format a TDD outcome for display.
 */
export function formatTDDOutcome(outcome: TDDOutcome): string {
  const lines: string[] = [];
  const status = outcome.success ? "SUCCESS" : "FAILED";

  lines.push(`## TDD Implementation: ${outcome.task_name}`);
  lines.push("");
  lines.push(`**Task ID:** ${outcome.task_id}`);
  lines.push(`**Status:** ${status}`);
  lines.push(`**Cycles Completed:** ${outcome.cycles_completed}`);
  lines.push(`**Coverage:** ${outcome.final_coverage}%`);
  lines.push(`**Tests Added:** ${outcome.tests_added} tests`);

  if (outcome.duration_ms !== undefined) {
    const seconds = Math.round(outcome.duration_ms / 1000);
    lines.push(`**Duration:** ${seconds}s`);
  }

  if (outcome.files_modified.length > 0) {
    lines.push("");
    lines.push("**Files Modified:**");
    for (const file of outcome.files_modified) {
      lines.push(`- ${file}`);
    }
  }

  if (!outcome.success && outcome.failure_reason) {
    lines.push("");
    lines.push(`**Failure Reason:** ${outcome.failure_reason}`);
  }

  if (outcome.learnings && outcome.learnings.length > 0) {
    lines.push("");
    lines.push("**Learnings:**");
    for (const learning of outcome.learnings) {
      lines.push(`- ${learning}`);
    }
  }

  return lines.join("\n");
}

/**
 * Format a coverage report for display.
 */
export function formatCoverageReport(
  coverage: CoverageInfo,
  target: number
): string {
  const lines: string[] = [];
  const passed = coverage.total >= target;
  const status = passed ? "PASS" : "FAIL";

  lines.push(`## Coverage Report [${status}]`);
  lines.push("");
  lines.push(`**Total:** ${coverage.total}% (target: ${target}%)`);

  if (coverage.statements !== undefined) {
    lines.push(`**Statements:** ${coverage.statements}%`);
  }
  if (coverage.branches !== undefined) {
    lines.push(`**Branches:** ${coverage.branches}%`);
  }
  if (coverage.functions !== undefined) {
    lines.push(`**Functions:** ${coverage.functions}%`);
  }
  if (coverage.lines !== undefined) {
    lines.push(`**Lines:** ${coverage.lines}%`);
  }

  return lines.join("\n");
}
