/**
 * Flow Think MCP - Output Formatter
 *
 * Formats step output in console (colored), JSON, or Markdown formats.
 */

import type { FlowThinkStep, FlowThinkHistory, OutputFormat } from "./types.js";

/**
 * ANSI color codes for console output.
 */
const COLORS = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",

  // Foreground
  red: "\x1b[31m",
  green: "\x1b[32m",
  yellow: "\x1b[33m",
  blue: "\x1b[34m",
  magenta: "\x1b[35m",
  cyan: "\x1b[36m",
  white: "\x1b[37m",
  gray: "\x1b[90m",
} as const;

/**
 * Color a string for console output.
 */
function color(text: string, ...codes: (keyof typeof COLORS)[]): string {
  const colorCodes = codes.map((c) => COLORS[c]).join("");
  return `${colorCodes}${text}${COLORS.reset}`;
}

/**
 * Get color for purpose type.
 */
function getPurposeColor(purpose: string): keyof typeof COLORS {
  const purposeColors: Record<string, keyof typeof COLORS> = {
    planning: "blue",
    research: "cyan",
    implement: "green",
    debug: "red",
    analysis: "magenta",
    validation: "yellow",
    decision: "yellow",
    exploration: "cyan",
    reflection: "gray",
  };
  return purposeColors[purpose.toLowerCase()] ?? "white";
}

/**
 * Truncate string to max length with ellipsis.
 */
function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + "...";
}

/**
 * Output formatter for FlowThink steps.
 */
export class FlowThinkFormatter {
  private colorOutput: boolean;

  constructor(colorOutput: boolean = true) {
    this.colorOutput = colorOutput;
  }

  /**
   * Format a step based on output format.
   */
  format(step: FlowThinkStep, format: OutputFormat): string {
    switch (format) {
      case "json":
        return this.formatStepJSON(step);
      case "markdown":
        return this.formatStepMarkdown(step);
      default:
        return this.formatStepConsole(step);
    }
  }

  /**
   * Format step as colored console output.
   */
  formatStepConsole(step: FlowThinkStep): string {
    const lines: string[] = [];
    const purposeColor = getPurposeColor(step.purpose);

    // Header
    const progress = `${step.step_number}/${step.estimated_total}`;
    const header = this.colorOutput
      ? `${color("═".repeat(60), "dim")}\n${color("STEP", "bold")} ${color(progress, "cyan")} │ ${color(step.purpose.toUpperCase(), purposeColor, "bold")}`
      : `${"═".repeat(60)}\nSTEP ${progress} │ ${step.purpose.toUpperCase()}`;
    lines.push(header);

    // Timestamp
    if (step.timestamp) {
      const ts = this.colorOutput ? color(step.timestamp, "dim") : step.timestamp;
      lines.push(ts);
    }

    lines.push("");

    // Context (truncated)
    const contextLabel = this.colorOutput ? color("Context:", "bold") : "Context:";
    lines.push(`${contextLabel} ${truncate(step.context, 200)}`);

    // Thought
    const thoughtLabel = this.colorOutput ? color("Thought:", "bold") : "Thought:";
    lines.push(`${thoughtLabel} ${step.thought}`);

    // Outcome
    const outcomeLabel = this.colorOutput ? color("Outcome:", "bold") : "Outcome:";
    lines.push(`${outcomeLabel} ${step.outcome}`);

    // Next Action
    const nextActionLabel = this.colorOutput ? color("Next:", "bold", "green") : "Next:";
    const nextActionStr =
      typeof step.next_action === "string"
        ? step.next_action
        : `[${step.next_action.tool ?? "action"}] ${step.next_action.action}`;
    lines.push(`${nextActionLabel} ${nextActionStr}`);

    // Rationale
    const rationaleLabel = this.colorOutput ? color("Why:", "dim") : "Why:";
    lines.push(`${rationaleLabel} ${step.rationale}`);

    // Optional fields
    if (step.confidence !== undefined) {
      const confPercent = Math.round(step.confidence * 100);
      const confColor: keyof typeof COLORS =
        step.confidence < 0.5 ? "red" : step.confidence < 0.8 ? "yellow" : "green";
      const confStr = this.colorOutput
        ? color(`${confPercent}%`, confColor)
        : `${confPercent}%`;
      lines.push(`Confidence: ${confStr}`);
    }

    if (step.hypothesis) {
      const status = step.verification_status ?? "pending";
      const statusColor: keyof typeof COLORS =
        status === "confirmed" ? "green" : status === "refuted" ? "red" : "yellow";
      const statusStr = this.colorOutput ? color(status, statusColor) : status;
      lines.push(`Hypothesis: ${step.hypothesis} [${statusStr}]`);
    }

    if (step.revises_step) {
      const revisionStr = this.colorOutput
        ? color(`Revises step ${step.revises_step}`, "yellow")
        : `Revises step ${step.revises_step}`;
      lines.push(revisionStr);
    }

    if (step.branch_id) {
      const branchStr = this.colorOutput
        ? color(`Branch: ${step.branch_name ?? step.branch_id}`, "magenta")
        : `Branch: ${step.branch_name ?? step.branch_id}`;
      lines.push(branchStr);
    }

    if (step.is_final_step) {
      const finalStr = this.colorOutput
        ? color("✓ FINAL STEP", "green", "bold")
        : "✓ FINAL STEP";
      lines.push(finalStr);
    }

    // Footer
    lines.push(this.colorOutput ? color("═".repeat(60), "dim") : "═".repeat(60));

    return lines.join("\n");
  }

  /**
   * Format step as JSON.
   */
  formatStepJSON(step: FlowThinkStep): string {
    return JSON.stringify(step, null, 2);
  }

  /**
   * Format step as Markdown.
   */
  formatStepMarkdown(step: FlowThinkStep): string {
    const lines: string[] = [];

    // Header
    lines.push(`## Step ${step.step_number}/${step.estimated_total}: ${step.purpose}`);
    if (step.timestamp) {
      lines.push(`*${step.timestamp}*`);
    }
    lines.push("");

    // Sections
    lines.push(`**Context:** ${step.context}`);
    lines.push("");
    lines.push(`**Thought:** ${step.thought}`);
    lines.push("");
    lines.push(`**Outcome:** ${step.outcome}`);
    lines.push("");

    // Next Action
    if (typeof step.next_action === "string") {
      lines.push(`**Next Action:** ${step.next_action}`);
    } else {
      lines.push(`**Next Action:**`);
      if (step.next_action.tool) {
        lines.push(`- Tool: \`${step.next_action.tool}\``);
      }
      lines.push(`- Action: ${step.next_action.action}`);
      if (step.next_action.expectedOutput) {
        lines.push(`- Expected: ${step.next_action.expectedOutput}`);
      }
    }
    lines.push("");

    lines.push(`**Rationale:** ${step.rationale}`);

    // Optional metadata
    const metadata: string[] = [];
    if (step.confidence !== undefined) {
      metadata.push(`Confidence: ${Math.round(step.confidence * 100)}%`);
    }
    if (step.hypothesis) {
      metadata.push(`Hypothesis: ${step.hypothesis} (${step.verification_status ?? "pending"})`);
    }
    if (step.revises_step) {
      metadata.push(`Revises: Step ${step.revises_step}`);
    }
    if (step.branch_id) {
      metadata.push(`Branch: ${step.branch_name ?? step.branch_id}`);
    }
    if (step.is_final_step) {
      metadata.push("**FINAL STEP**");
    }

    if (metadata.length > 0) {
      lines.push("");
      lines.push("---");
      lines.push(metadata.join(" | "));
    }

    return lines.join("\n");
  }

  /**
   * Format history summary.
   */
  formatHistorySummary(history: FlowThinkHistory): string {
    const lines: string[] = [];

    lines.push(this.colorOutput ? color("History Summary", "bold") : "History Summary");
    lines.push(`Steps: ${history.steps.length}`);
    lines.push(`Completed: ${history.completed ? "Yes" : "No"}`);
    lines.push(`Created: ${history.created_at}`);
    lines.push(`Updated: ${history.updated_at}`);

    if (history.metadata) {
      if (history.metadata.total_duration_ms !== undefined) {
        lines.push(`Duration: ${history.metadata.total_duration_ms}ms`);
      }
      if (history.metadata.revisions_count !== undefined && history.metadata.revisions_count > 0) {
        lines.push(`Revisions: ${history.metadata.revisions_count}`);
      }
      if (history.metadata.branches_created !== undefined && history.metadata.branches_created > 0) {
        lines.push(`Branches: ${history.metadata.branches_created}`);
      }
    }

    return lines.join("\n");
  }
}
