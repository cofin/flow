/**
 * Flow Think MCP - Server Implementation
 *
 * Core server class that handles step processing, validation, and history management.
 */

import type {
  FlowThinkStep,
  FlowThinkHistory,
  FlowThinkConfig,
  ValidationResult,
  MCPResponse,
  ConfidenceWarning,
  Branch,
  SessionEntry,
} from "./types.js";
import {
  getConfidenceLevel,
  validateRevisionTarget,
  validateBranchRequest,
  generateBranchId,
  validateDependencies,
} from "./types.js";
import { FlowThinkFormatter } from "./formatter.js";
import { SafeBeadsWrapper } from "./beads/index.js";

/**
 * Completion phrases that indicate reasoning is done.
 */
const COMPLETION_PHRASES = [
  "final conclusion",
  "in conclusion",
  "reasoning complete",
  "analysis complete",
  "task complete",
  "investigation complete",
] as const;

/**
 * FlowThink MCP Server.
 *
 * Handles structured reasoning step processing with history management.
 */
export class FlowThinkServer {
  private history: FlowThinkHistory;
  private config: FlowThinkConfig;
  private formatter: FlowThinkFormatter;
  private startTime: number;

  /** O(1) step lookup by number */
  private stepIndex: Map<number, FlowThinkStep> = new Map();

  /** Cached step numbers for validation */
  private stepNumbers: Set<number> = new Set();

  /** Branch index for O(1) lookup */
  private branchIndex: Map<string, Branch> = new Map();

  /** Sessions map for multi-session support */
  private sessions: Map<string, SessionEntry> = new Map();

  /** Current active session ID (null = default/main) */
  private currentSessionId: string | null = null;

  /** Beads integration wrapper */
  private beads: SafeBeadsWrapper;

  constructor(config: FlowThinkConfig) {
    this.config = config;
    this.formatter = new FlowThinkFormatter(config.outputFormat === "console");
    this.history = this.createNewHistory();
    this.startTime = Date.now();
    this.beads = new SafeBeadsWrapper({
      enabled: config.beadsSync ?? true,
    });
  }

  /**
   * Create a fresh history object.
   */
  private createNewHistory(): FlowThinkHistory {
    return {
      steps: [],
      completed: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      branches: [],
      metadata: {
        total_duration_ms: 0,
        revisions_count: 0,
        branches_created: 0,
        tools_used: [],
        max_branch_depth: 0,
      },
    };
  }

  /**
   * Get the depth of a branch (0 for main trunk).
   */
  private getBranchDepth(branchId: string | undefined): number {
    if (!branchId) return 0;
    const branch = this.branchIndex.get(branchId);
    if (!branch) return 0;
    return branch.depth;
  }

  /**
   * Get the current branch depth for a step.
   */
  private getStepBranchDepth(stepNumber: number): number {
    const step = this.stepIndex.get(stepNumber);
    if (!step || !step.branch_id) return 0;
    return this.getBranchDepth(step.branch_id);
  }

  /**
   * Validate that a value is a non-empty string.
   */
  private isNonEmptyString(value: unknown): value is string {
    return typeof value === "string" && value.trim().length > 0;
  }

  /**
   * Validate that a value is a positive integer.
   */
  private isPositiveInteger(value: unknown): value is number {
    return typeof value === "number" && Number.isInteger(value) && value >= 1;
  }

  /**
   * Validate confidence value if provided.
   * Returns error message if invalid, null if valid or not provided.
   */
  private validateConfidence(step: Record<string, unknown>): string | null {
    if (step.confidence === undefined) return null;

    const confidence = step.confidence;
    if (typeof confidence !== "number") {
      return "confidence must be a number";
    }
    if (confidence < 0 || confidence > 1) {
      return `confidence must be between 0 and 1, got ${confidence}`;
    }
    return null;
  }

  /**
   * Generate warning for low confidence.
   */
  private generateConfidenceWarning(confidence: number): ConfidenceWarning | null {
    const threshold = this.config.lowConfidenceThreshold ?? 0.5;
    if (confidence >= threshold) return null;

    const level = getConfidenceLevel(confidence);
    // Critical if confidence is less than 20% (very uncertain)
    const isCritical = confidence < 0.2;

    return {
      level: isCritical ? "critical" : "warning",
      message: `Low confidence (${Math.round(confidence * 100)}%) - below threshold of ${Math.round(threshold * 100)}%`,
      suggestion: this.getConfidenceSuggestion(level),
      confidence,
      threshold,
    };
  }

  /**
   * Get suggestion based on confidence level.
   */
  private getConfidenceSuggestion(level: string): string {
    switch (level) {
      case "low":
        return "Consider gathering more information or breaking the problem into smaller parts";
      case "medium":
        return "You may want to verify assumptions before proceeding";
      default:
        return "Review your reasoning to identify uncertainties";
    }
  }

  /**
   * Validate required fields with detailed error messages.
   */
  validateRequiredFields(step: unknown): ValidationResult {
    if (typeof step !== "object" || step === null) {
      return { valid: false, missing: ["step object"], error: "Input must be an object" };
    }

    const s = step as Record<string, unknown>;
    const missing: string[] = [];

    // Check integers
    if (!this.isPositiveInteger(s.step_number)) {
      missing.push("step_number (must be positive integer >= 1)");
    }
    if (!this.isPositiveInteger(s.estimated_total)) {
      missing.push("estimated_total (must be positive integer >= 1)");
    }

    // Check strings
    if (!this.isNonEmptyString(s.purpose)) missing.push("purpose");
    if (!this.isNonEmptyString(s.context)) missing.push("context");
    if (!this.isNonEmptyString(s.thought)) missing.push("thought");
    if (!this.isNonEmptyString(s.outcome)) missing.push("outcome");
    if (!this.isNonEmptyString(s.rationale)) missing.push("rationale");

    // Check next_action (string or object with action)
    if (typeof s.next_action === "string") {
      if (!this.isNonEmptyString(s.next_action)) {
        missing.push("next_action");
      }
    } else if (typeof s.next_action === "object" && s.next_action !== null) {
      const na = s.next_action as Record<string, unknown>;
      if (!this.isNonEmptyString(na.action)) {
        missing.push("next_action.action");
      }
    } else {
      missing.push("next_action");
    }

    if (missing.length > 0) {
      return {
        valid: false,
        missing,
        error: `Missing or invalid required fields: ${missing.join(", ")}`,
      };
    }

    return { valid: true, missing: [] };
  }

  /**
   * Check if thought contains completion phrases.
   */
  private detectCompletion(thought: string): boolean {
    const lower = thought.toLowerCase();
    return COMPLETION_PHRASES.some((phrase) => lower.includes(phrase));
  }

  /**
   * Trim history to max size, cleaning up indexes.
   */
  private trimHistory(): void {
    if (this.history.steps.length <= this.config.maxHistorySize) {
      return;
    }

    const toRemove = this.history.steps.length - this.config.maxHistorySize;
    const removedSteps = this.history.steps.slice(0, toRemove);

    // Update indexes
    for (const step of removedSteps) {
      this.stepIndex.delete(step.step_number);
      this.stepNumbers.delete(step.step_number);
    }

    this.history.steps = this.history.steps.slice(toRemove);
    console.error(`📋 History trimmed to ${this.config.maxHistorySize} steps`);
  }

  /**
   * Extract tools used from step.
   */
  private extractToolsUsed(step: FlowThinkStep): string[] {
    const tools: string[] = [];

    if (step.tools_used) {
      tools.push(...step.tools_used);
    }

    if (typeof step.next_action === "object" && step.next_action.tool) {
      tools.push(step.next_action.tool);
    }

    return [...new Set(tools)];
  }

  /**
   * Process a reasoning step.
   *
   * Validates the step, adds it to history, and returns a response.
   */
  async processStep(input: unknown): Promise<MCPResponse> {
    const stepStartTime = Date.now();

    try {
      // Get session_id early to switch context before validation
      const inputObj = input as Record<string, unknown>;
      const sessionId = inputObj.session_id as string | undefined;

      // Switch to session context (affects stepNumbers, stepIndex, etc.)
      this.switchToSession(sessionId);

      // Validate required fields
      const validation = this.validateRequiredFields(input);
      if (!validation.valid) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  error: validation.error,
                  status: "failed",
                  missing_fields: validation.missing,
                },
                null,
                2
              ),
            },
          ],
          isError: true,
        };
      }

      // Validate confidence if provided
      const confidenceError = this.validateConfidence(input as Record<string, unknown>);
      if (confidenceError) {
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                {
                  error: confidenceError,
                  status: "failed",
                },
                null,
                2
              ),
            },
          ],
          isError: true,
        };
      }

      const step = input as FlowThinkStep;

      // Check for low confidence and generate warning
      let confidenceWarning: ConfidenceWarning | null = null;
      if (step.confidence !== undefined) {
        confidenceWarning = this.generateConfidenceWarning(step.confidence);
        if (confidenceWarning) {
          const emoji = confidenceWarning.level === "critical" ? "🚨" : "⚠️";
          console.error(`${emoji} ${confidenceWarning.message}`);
          if (confidenceWarning.suggestion) {
            console.error(`   💡 ${confidenceWarning.suggestion}`);
          }
        }
      }

      // Validate revision target if provided
      if (step.revises_step !== undefined) {
        const revisionResult = validateRevisionTarget(step.revises_step, this.stepNumbers);
        if (!revisionResult.valid) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    error: revisionResult.error,
                    status: "failed",
                  },
                  null,
                  2
                ),
              },
            ],
            isError: true,
          };
        }
      }

      // Validate branch request if provided
      if (step.branch_from !== undefined) {
        const currentDepth = this.getStepBranchDepth(step.branch_from);
        const maxDepth = this.config.maxBranchDepth ?? 5;
        const branchResult = validateBranchRequest(
          step.branch_from,
          this.stepNumbers,
          currentDepth,
          maxDepth
        );
        if (!branchResult.valid) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    error: branchResult.error,
                    status: "failed",
                  },
                  null,
                  2
                ),
              },
            ],
            isError: true,
          };
        }

        // Auto-generate branch_id if not provided
        if (!step.branch_id) {
          step.branch_id = generateBranchId();
        }
      }

      // Validate dependencies if provided
      if (step.dependencies && step.dependencies.length > 0) {
        const depResult = validateDependencies(
          step.step_number,
          step.dependencies,
          this.stepNumbers
        );
        if (!depResult.valid) {
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    error: depResult.error,
                    status: "failed",
                    invalid_steps: depResult.invalid_steps,
                  },
                  null,
                  2
                ),
              },
            ],
            isError: true,
          };
        }
      }

      // Add timestamp
      step.timestamp = new Date().toISOString();

      // Check for completion
      if (step.is_final_step === true) {
        this.history.completed = true;
      } else if (this.detectCompletion(step.thought)) {
        this.history.completed = true;
      }

      // Track tools used
      const toolsUsed = this.extractToolsUsed(step);
      if (this.history.metadata && toolsUsed.length > 0) {
        const existing = new Set(this.history.metadata.tools_used ?? []);
        for (const tool of toolsUsed) {
          existing.add(tool);
        }
        this.history.metadata.tools_used = [...existing];
      }

      // Handle revision: mark original step as revised
      if (step.revises_step !== undefined) {
        const originalStep = this.stepIndex.get(step.revises_step);
        if (originalStep) {
          originalStep.revised_by = step.step_number;
        }
        // Increment revisions count
        if (this.history.metadata) {
          this.history.metadata.revisions_count =
            (this.history.metadata.revisions_count ?? 0) + 1;
        }
        console.error(`🔄 Step ${step.step_number} revises step ${step.revises_step}`);
      }

      // Log hypothesis verification state changes
      if (step.hypothesis && step.verification_status) {
        const emoji =
          step.verification_status === "confirmed"
            ? "✅"
            : step.verification_status === "refuted"
              ? "❌"
              : "🔬";
        console.error(`${emoji} Hypothesis: "${step.hypothesis}" [${step.verification_status}]`);
      }

      // Handle branching: create or update branch
      if (step.branch_id) {
        let branch = this.branchIndex.get(step.branch_id);
        if (!branch) {
          // New branch
          const parentStep = step.branch_from !== undefined
            ? this.stepIndex.get(step.branch_from)
            : undefined;
          const parentBranch = parentStep?.branch_id;
          const depth = step.branch_from !== undefined
            ? this.getStepBranchDepth(step.branch_from) + 1
            : 0;

          branch = {
            id: step.branch_id,
            name: step.branch_name,
            from_step: step.branch_from ?? 0,
            steps: [step.step_number],
            status: "active",
            depth,
            parent_branch: parentBranch,
            created_at: new Date().toISOString(),
          };

          this.branchIndex.set(step.branch_id, branch);
          if (!this.history.branches) {
            this.history.branches = [];
          }
          this.history.branches.push(branch);

          // Increment branches count
          if (this.history.metadata) {
            this.history.metadata.branches_created =
              (this.history.metadata.branches_created ?? 0) + 1;
            this.history.metadata.max_branch_depth = Math.max(
              this.history.metadata.max_branch_depth ?? 0,
              depth
            );
          }

          console.error(`🌿 Created branch "${step.branch_name || step.branch_id}" from step ${step.branch_from}`);
        } else {
          // Existing branch - add step
          branch.steps.push(step.step_number);
        }
      }

      // Add to history and indexes
      this.history.steps.push(step);
      this.stepIndex.set(step.step_number, step);
      this.stepNumbers.add(step.step_number);

      // Calculate duration
      step.duration_ms = Date.now() - stepStartTime;
      if (this.history.metadata) {
        this.history.metadata.total_duration_ms = Date.now() - this.startTime;
      }

      // Update timestamp
      this.history.updated_at = new Date().toISOString();

      // Trim if needed
      this.trimHistory();

      // Format and log output
      const formattedOutput = this.formatter.format(step, this.config.outputFormat);
      console.error(formattedOutput);

      // Sync to Beads (fire-and-forget, non-blocking)
      // Don't await - let it run in background
      this.beads.syncStep(step, step.session_id, step.beads_task_id).catch(() => {
        // Errors are handled internally by SafeBeadsWrapper
      });

      // Build response
      const response: Record<string, unknown> = {
        status: this.history.completed ? "flow_think_complete" : "flow_think_in_progress",
        step_number: step.step_number,
        estimated_total: step.estimated_total,
        completed: this.history.completed,
        total_steps_recorded: this.history.steps.length,
        next_action: step.next_action,
      };

      // Add optional response fields
      if (step.confidence !== undefined) {
        response.confidence = step.confidence;
        if (confidenceWarning) {
          response.warning = confidenceWarning;
        }
      }
      if (step.hypothesis) {
        response.hypothesis = {
          text: step.hypothesis,
          status: step.verification_status ?? "pending",
        };
      }
      if (step.revises_step) {
        response.revised_step = step.revises_step;
        response.revision = {
          revises: step.revises_step,
          reason: step.revision_reason,
        };
      }
      if (step.branch_id) {
        response.branch = {
          id: step.branch_id,
          name: step.branch_name,
          from: step.branch_from,
        };
      }
      if (step.dependencies && step.dependencies.length > 0) {
        response.dependencies = step.dependencies;
      }
      if (step.session_id) {
        response.session_id = step.session_id;
      }

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error(`❌ Error processing step: ${errorMessage}`);

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(
              {
                error: errorMessage,
                status: "failed",
              },
              null,
              2
            ),
          },
        ],
        isError: true,
      };
    }
  }

  /**
   * Clear all history.
   */
  clearHistory(): void {
    this.history = this.createNewHistory();
    this.stepIndex.clear();
    this.stepNumbers.clear();
    this.branchIndex.clear();
    this.startTime = Date.now();
    console.error("🔄 Flow Think history cleared");
  }

  /**
   * Get the current history.
   */
  getHistory(): FlowThinkHistory {
    return this.history;
  }

  /**
   * Get a step by number.
   */
  getStep(stepNumber: number): FlowThinkStep | undefined {
    return this.stepIndex.get(stepNumber);
  }

  /**
   * Check if a step number exists.
   */
  hasStep(stepNumber: number): boolean {
    return this.stepNumbers.has(stepNumber);
  }

  /**
   * Get history summary.
   */
  getHistorySummary(): string {
    return this.formatter.formatHistorySummary(this.history);
  }

  // ─────────────────────────────────────────────────────────────
  // Session Management
  // ─────────────────────────────────────────────────────────────

  /**
   * Get or create a session by ID.
   */
  private getOrCreateSession(sessionId: string): SessionEntry {
    let session = this.sessions.get(sessionId);
    if (!session) {
      session = {
        id: sessionId,
        history: this.createNewHistory(),
        created_at: new Date().toISOString(),
        last_accessed: new Date().toISOString(),
        stepIndex: new Map(),
        stepNumbers: new Set(),
        branchIndex: new Map(),
      };
      this.sessions.set(sessionId, session);
      console.error(`📦 Created new session: ${sessionId}`);
    }
    session.last_accessed = new Date().toISOString();
    return session;
  }

  /**
   * Switch to a session's context.
   */
  private switchToSession(sessionId: string | undefined): void {
    if (!sessionId) {
      // Use default session (main history)
      this.currentSessionId = null;
      return;
    }

    if (this.currentSessionId === sessionId) {
      return; // Already in this session
    }

    const session = this.getOrCreateSession(sessionId);
    this.currentSessionId = sessionId;

    // Switch context to session's indexes
    this.history = session.history;
    this.stepIndex = session.stepIndex;
    this.stepNumbers = session.stepNumbers;
    this.branchIndex = session.branchIndex;
  }

  /**
   * Get history for a specific session.
   */
  getSessionHistory(sessionId: string): FlowThinkHistory | undefined {
    const session = this.sessions.get(sessionId);
    return session?.history;
  }

  /**
   * List all sessions.
   */
  listSessions(): Array<{ id: string; created_at: string; last_accessed: string; step_count: number }> {
    return Array.from(this.sessions.values()).map((session) => ({
      id: session.id,
      created_at: session.created_at,
      last_accessed: session.last_accessed,
      step_count: session.history.steps.length,
    }));
  }

  /**
   * Clear a specific session.
   */
  clearSession(sessionId: string): boolean {
    const deleted = this.sessions.delete(sessionId);
    if (deleted && this.currentSessionId === sessionId) {
      // Reset to default
      this.currentSessionId = null;
      this.history = this.createNewHistory();
      this.stepIndex.clear();
      this.stepNumbers.clear();
      this.branchIndex.clear();
    }
    return deleted;
  }

  /**
   * Export history in specified format.
   */
  exportHistory(format: "json" | "markdown" | "text" = "json"): string {
    switch (format) {
      case "markdown":
        return this.history.steps
          .map((step) => this.formatter.formatStepMarkdown(step))
          .join("\n\n---\n\n");
      case "text":
        return this.history.steps
          .map((step) => this.formatter.formatStepConsole(step))
          .join("\n\n");
      default:
        return JSON.stringify(this.history, null, 2);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Beads Integration
  // ─────────────────────────────────────────────────────────────

  /**
   * Register a session with a Beads epic.
   */
  registerBeadsEpic(sessionId: string, epicId: string): void {
    this.beads.registerSession(sessionId, epicId);
  }

  /**
   * Get Beads sync statistics.
   */
  getBeadsStats(): ReturnType<SafeBeadsWrapper["getStats"]> {
    return this.beads.getStats();
  }

  /**
   * Check if Beads is available.
   */
  async isBeadsAvailable(): Promise<boolean> {
    return this.beads.isAvailable();
  }

  /**
   * Restore reasoning context from Beads epic.
   */
  async restoreFromBeads(epicId: string): Promise<{
    success: boolean;
    steps_restored: number;
    context_summary?: string;
  }> {
    const result = await this.beads.restoreContext(epicId);

    if (!result.success || !result.data) {
      return {
        success: false,
        steps_restored: 0,
      };
    }

    const summary = result.data.steps
      ? this.beads.createContextSummary(result.data.steps)
      : undefined;

    return {
      success: true,
      steps_restored: result.data.steps_restored,
      context_summary: summary,
    };
  }
}
