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
} from "./types.js";
import { FlowThinkFormatter } from "./formatter.js";

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

  constructor(config: FlowThinkConfig) {
    this.config = config;
    this.formatter = new FlowThinkFormatter(config.outputFormat === "console");
    this.history = this.createNewHistory();
    this.startTime = Date.now();
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
      metadata: {
        total_duration_ms: 0,
        revisions_count: 0,
        branches_created: 0,
        tools_used: [],
      },
    };
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

      const step = input as FlowThinkStep;

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
      }
      if (step.hypothesis) {
        response.hypothesis = {
          text: step.hypothesis,
          status: step.verification_status ?? "pending",
        };
      }
      if (step.revises_step) {
        response.revised_step = step.revises_step;
      }
      if (step.branch_id) {
        response.branch = {
          id: step.branch_id,
          name: step.branch_name,
          from: step.branch_from,
        };
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
}
