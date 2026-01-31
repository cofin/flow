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
