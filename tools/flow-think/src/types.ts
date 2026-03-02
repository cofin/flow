/**
 * Flow Think MCP - Core Type Definitions
 *
 * Defines the data structures for structured thinking steps,
 * history tracking, and configuration.
 */

/**
 * Structured action for tool integration.
 * Allows specifying tool calls with expected outputs.
 */
export interface StructuredAction {
  /** Name of tool to use (optional) */
  tool?: string;
  /** Specific action to perform (required) */
  action: string;
  /** Parameters to pass to the tool */
  parameters?: Record<string, unknown>;
  /** What you expect this action to return */
  expectedOutput?: string;
}

/**
 * A single reasoning step in the structured thinking process.
 * Core required fields capture the essence of each thought.
 */
export interface FlowThinkStep {
  // ─────────────────────────────────────────────────────────────
  // Required fields
  // ─────────────────────────────────────────────────────────────

  /** Sequential step number starting from 1 */
  step_number: number;

  /** Current estimate of total steps needed (can be adjusted) */
  estimated_total: number;

  /**
   * Category of this reasoning step.
   * Standard: planning, research, implement, debug, analysis,
   *           reflection, decision, validation, exploration
   * Custom strings allowed.
   */
  purpose: string;

  /** What is already known or has been completed */
  context: string;

  /** Your current reasoning process */
  thought: string;

  /** The expected or actual result from this step */
  outcome: string;

  /** What you will do next - simple string or structured action */
  next_action: string | StructuredAction;

  /** Why you chose this next action */
  rationale: string;

  // ─────────────────────────────────────────────────────────────
  // Metadata (added by server)
  // ─────────────────────────────────────────────────────────────

  /** ISO timestamp when step was recorded */
  timestamp?: string;

  /** Processing duration in milliseconds */
  duration_ms?: number;

  // ─────────────────────────────────────────────────────────────
  // Optional fields (for Chapter 2+)
  // ─────────────────────────────────────────────────────────────

  /** Confidence in this step (0-1 scale) */
  confidence?: number;

  /** Describe specific uncertainties or doubts */
  uncertainty_notes?: string;

  /** Step number you are revising */
  revises_step?: number;

  /** Why you are revising the earlier step */
  revision_reason?: string;

  /** Step number that revised this step (set by server) */
  revised_by?: number;

  /** Step number to branch from for alternative approach */
  branch_from?: number;

  /** Unique identifier for this branch */
  branch_id?: string;

  /** Human-readable name for this branch */
  branch_name?: string;

  /** Step numbers this step depends on */
  dependencies?: number[];

  /** Current hypothesis being tested */
  hypothesis?: string;

  /** Verification status of hypothesis */
  verification_status?: "pending" | "confirmed" | "refuted";

  /** Tools used during this step */
  tools_used?: string[];

  /** External data or tool outputs */
  external_context?: Record<string, unknown>;

  /** Session identifier for grouping reasoning chains */
  session_id?: string;

  /** Marks this as the final reasoning step */
  is_final_step?: boolean;

  // ─────────────────────────────────────────────────────────────
  // Flow-specific fields (for Chapter 3+)
  // ─────────────────────────────────────────────────────────────

  /** Current Flow context (flow_id) */
  flow_id?: string;

  /** Linked Beads task ID */
  beads_task_id?: string;

  /** Files examined during this step */
  files_referenced?: string[];

  /** Patterns discovered for learnings capture */
  patterns_discovered?: string[];
}

/**
 * History of reasoning steps with metadata.
 */
export interface FlowThinkHistory {
  /** All recorded steps */
  steps: FlowThinkStep[];

  /** Whether reasoning chain is complete */
  completed: boolean;

  /** ISO timestamp when history was created */
  created_at: string;

  /** ISO timestamp of last update */
  updated_at: string;

  /** Branches in the reasoning tree */
  branches?: Branch[];

  /** Aggregate metadata */
  metadata?: {
    /** Total reasoning duration */
    total_duration_ms?: number;
    /** Number of revisions made */
    revisions_count?: number;
    /** Number of branches created */
    branches_created?: number;
    /** All tools used across steps */
    tools_used?: string[];
    /** Current maximum branch depth */
    max_branch_depth?: number;
  };
}

/**
 * Output format options.
 */
export type OutputFormat = "console" | "json" | "markdown";

/**
 * Server configuration loaded from environment.
 */
export interface FlowThinkConfig {
  /** How to format output (console, json, markdown) */
  outputFormat: OutputFormat;

  /** Maximum steps to retain in history */
  maxHistorySize: number;

  /** Session timeout in minutes (for Chapter 2) */
  sessionTimeout?: number;

  /** Maximum branch depth (for Chapter 2) */
  maxBranchDepth?: number;

  /** Whether to sync to Beads (for Chapter 3) */
  beadsSync?: boolean;

  /** Low confidence threshold for warnings (for Chapter 2) */
  lowConfidenceThreshold?: number;
}

/**
 * Result of validating a step's required fields.
 */
export interface ValidationResult {
  /** Whether validation passed */
  valid: boolean;

  /** List of missing or invalid fields */
  missing: string[];

  /** Detailed error message if invalid */
  error?: string;
}

/**
 * MCP response content item.
 */
export interface MCPTextContent {
  type: "text";
  text: string;
}

/**
 * Response from processStep().
 * Uses index signature for MCP SDK compatibility.
 */
export interface MCPResponse {
  [key: string]: unknown;
  content: MCPTextContent[];
  isError?: boolean;
}

/**
 * Required fields that must be present in every step.
 */
export const REQUIRED_STEP_FIELDS = [
  "step_number",
  "estimated_total",
  "purpose",
  "context",
  "thought",
  "outcome",
  "next_action",
  "rationale",
] as const;

/**
 * Standard purpose types with descriptions.
 */
export const PURPOSE_TYPES = {
  planning: "Outlining approach, breaking down tasks",
  research: "Investigating, gathering information",
  implement: "Writing code, making changes",
  debug: "Investigating errors, troubleshooting",
  analysis: "Examining code/architecture",
  reflection: "Reviewing progress, extracting patterns",
  decision: "Making a choice between options",
  validation: "Checking results, verifying hypothesis",
  exploration: "Investigating options, trying approaches",
} as const;

export type StandardPurpose = keyof typeof PURPOSE_TYPES;

// ─────────────────────────────────────────────────────────────
// Chapter 2: Confidence Tracking Types
// ─────────────────────────────────────────────────────────────

/**
 * Semantic confidence levels.
 */
export type ConfidenceLevel = "low" | "medium" | "high" | "very_high";

/**
 * Confidence thresholds for categorization.
 */
export const CONFIDENCE_THRESHOLDS = {
  low: 0.3,
  medium: 0.5,
  high: 0.8,
  very_high: 0.95,
} as const;

/**
 * Warning generated when confidence is below threshold.
 */
export interface ConfidenceWarning {
  /** Warning severity level */
  level: "info" | "warning" | "critical";
  /** Human-readable message */
  message: string;
  /** Suggested action to increase confidence */
  suggestion?: string;
  /** The confidence value that triggered this warning */
  confidence: number;
  /** The threshold that was not met */
  threshold: number;
}

/**
 * Get semantic confidence level from numeric value.
 */
export function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= CONFIDENCE_THRESHOLDS.very_high) return "very_high";
  if (confidence >= CONFIDENCE_THRESHOLDS.high) return "high";
  if (confidence >= CONFIDENCE_THRESHOLDS.medium) return "medium";
  return "low";
}

// ─────────────────────────────────────────────────────────────
// Chapter 2: Revision Tracking Types
// ─────────────────────────────────────────────────────────────

/**
 * Tracks a revision relationship between steps.
 */
export interface RevisionInfo {
  /** Step number that was revised */
  original_step: number;
  /** Step number containing the revision */
  revised_by: number;
  /** Reason for the revision */
  reason: string;
  /** When the revision was made */
  timestamp: string;
}

/**
 * Result of validating a revision request.
 */
export interface RevisionValidationResult {
  /** Whether the revision is valid */
  valid: boolean;
  /** Error message if invalid */
  error?: string;
}

/**
 * Validate that a revision target exists.
 */
export function validateRevisionTarget(
  targetStep: number,
  existingSteps: Set<number>
): RevisionValidationResult {
  if (targetStep < 1) {
    return {
      valid: false,
      error: `revises_step must be >= 1, got ${targetStep}`,
    };
  }
  if (!existingSteps.has(targetStep)) {
    return {
      valid: false,
      error: `Cannot revise step ${targetStep}: step does not exist`,
    };
  }
  return { valid: true };
}

// ─────────────────────────────────────────────────────────────
// Chapter 2: Branching Types
// ─────────────────────────────────────────────────────────────

/**
 * Branch status in the reasoning tree.
 */
export type BranchStatus = "active" | "merged" | "abandoned";

/**
 * A branch in the reasoning tree.
 * Represents an alternative exploration path.
 */
export interface Branch {
  /** Unique branch identifier */
  id: string;
  /** Human-readable name */
  name?: string;
  /** Step number this branch diverged from */
  from_step: number;
  /** Step numbers in this branch */
  steps: number[];
  /** Current branch status */
  status: BranchStatus;
  /** Nesting depth (0 = main trunk, 1 = first branch, etc.) */
  depth: number;
  /** Parent branch ID if nested */
  parent_branch?: string;
  /** When branch was created */
  created_at: string;
}

/**
 * Result of validating a branch request.
 */
export interface BranchValidationResult {
  /** Whether the branch is valid */
  valid: boolean;
  /** Error message if invalid */
  error?: string;
}

/**
 * Validate a branch request.
 */
export function validateBranchRequest(
  fromStep: number,
  existingSteps: Set<number>,
  currentDepth: number,
  maxDepth: number
): BranchValidationResult {
  if (fromStep < 1) {
    return {
      valid: false,
      error: `branch_from must be >= 1, got ${fromStep}`,
    };
  }
  if (!existingSteps.has(fromStep)) {
    return {
      valid: false,
      error: `Cannot branch from step ${fromStep}: step does not exist`,
    };
  }
  if (currentDepth >= maxDepth) {
    return {
      valid: false,
      error: `Maximum branch depth (${maxDepth}) exceeded`,
    };
  }
  return { valid: true };
}

/**
 * Generate a unique branch ID.
 */
export function generateBranchId(prefix = "branch"): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2, 6);
  return `${prefix}-${timestamp}-${random}`;
}

// ─────────────────────────────────────────────────────────────
// Chapter 2: Dependency Tracking Types
// ─────────────────────────────────────────────────────────────

/**
 * Result of validating dependencies.
 */
export interface DependencyValidationResult {
  /** Whether dependencies are valid */
  valid: boolean;
  /** Error message if invalid */
  error?: string;
  /** List of invalid step references */
  invalid_steps?: number[];
}

/**
 * Validate step dependencies.
 */
export function validateDependencies(
  stepNumber: number,
  dependencies: number[],
  existingSteps: Set<number>
): DependencyValidationResult {
  const invalidSteps: number[] = [];

  for (const dep of dependencies) {
    if (dep < 1) {
      return {
        valid: false,
        error: `Dependency step must be >= 1, got ${dep}`,
      };
    }
    if (dep === stepNumber) {
      return {
        valid: false,
        error: `Step ${stepNumber} cannot depend on itself`,
      };
    }
    if (!existingSteps.has(dep)) {
      invalidSteps.push(dep);
    }
  }

  if (invalidSteps.length > 0) {
    return {
      valid: false,
      error: `Dependencies [${invalidSteps.join(", ")}] do not exist`,
      invalid_steps: invalidSteps,
    };
  }

  return { valid: true };
}

// ─────────────────────────────────────────────────────────────
// Chapter 2: Session Management Types
// ─────────────────────────────────────────────────────────────

/**
 * A reasoning session containing its own history.
 */
export interface SessionEntry {
  /** Session identifier */
  id: string;
  /** History for this session */
  history: FlowThinkHistory;
  /** When session was created */
  created_at: string;
  /** When session was last accessed */
  last_accessed: string;
  /** Step index for this session */
  stepIndex: Map<number, FlowThinkStep>;
  /** Step numbers for this session */
  stepNumbers: Set<number>;
  /** Branch index for this session */
  branchIndex: Map<string, Branch>;
}

/**
 * Generate a unique session ID.
 */
export function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).slice(2, 8);
  return `session-${timestamp}-${random}`;
}
