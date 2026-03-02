/**
 * Flow Think MCP - Beads Type Definitions
 *
 * Types and utilities for Beads integration.
 */

import type { FlowThinkStep } from "../types.js";

/**
 * Sync status for a step with Beads.
 */
export type BeadsSyncStatus = "pending" | "synced" | "failed" | "skipped";

/**
 * All valid sync status values.
 */
export const BEADS_SYNC_STATUSES: BeadsSyncStatus[] = [
  "pending",
  "synced",
  "failed",
  "skipped",
];

/**
 * Beads-related metadata for a session.
 */
export interface BeadsSessionMetadata {
  /** Linked Beads epic ID */
  epic_id?: string;
  /** Last sync timestamp */
  last_synced_at?: string;
  /** Number of steps synced */
  synced_count: number;
  /** Number of sync failures */
  failed_count: number;
}

/**
 * Beads-related metadata for a step.
 */
export interface BeadsStepMetadata {
  /** Sync status */
  sync_status: BeadsSyncStatus;
  /** When synced (if successful) */
  synced_at?: string;
  /** Error message if failed */
  error?: string;
  /** Retry count */
  retries: number;
}

/**
 * Format a step for Beads notes.
 *
 * Creates a markdown-formatted note suitable for appending
 * to a Beads issue's notes field.
 */
export function formatStepForBeads(step: FlowThinkStep): string {
  const lines: string[] = [];

  // Header with step info
  lines.push(`## Step ${step.step_number}/${step.estimated_total}: ${step.purpose}`);

  // Timestamp if available
  if (step.timestamp) {
    lines.push(`*${step.timestamp}*`);
  }

  lines.push("");

  // Core fields
  lines.push(`**Context:** ${step.context}`);
  lines.push(`**Thought:** ${step.thought}`);
  lines.push(`**Outcome:** ${step.outcome}`);

  // Next action (handle both string and structured)
  if (typeof step.next_action === "string") {
    lines.push(`**Next:** ${step.next_action}`);
  } else {
    const tool = step.next_action.tool ? `[${step.next_action.tool}] ` : "";
    lines.push(`**Next:** ${tool}${step.next_action.action}`);
  }

  lines.push(`**Rationale:** ${step.rationale}`);

  // Optional fields
  if (step.confidence !== undefined) {
    lines.push("");
    lines.push(`**Confidence:** ${Math.round(step.confidence * 100)}%`);
  }

  if (step.hypothesis) {
    const status = step.verification_status ?? "pending";
    lines.push(`**Hypothesis:** ${step.hypothesis} [${status}]`);
  }

  if (step.files_referenced && step.files_referenced.length > 0) {
    lines.push(`**Files:** ${step.files_referenced.join(", ")}`);
  }

  if (step.patterns_discovered && step.patterns_discovered.length > 0) {
    lines.push(`**Patterns:** ${step.patterns_discovered.join(", ")}`);
  }

  // Branch info
  if (step.branch_id) {
    const branchInfo = step.branch_name
      ? `${step.branch_name} (${step.branch_id})`
      : step.branch_id;
    lines.push(`**Branch:** ${branchInfo}`);
  }

  // Revision info
  if (step.revises_step) {
    lines.push(`**Revises:** Step ${step.revises_step}`);
    if (step.revision_reason) {
      lines.push(`**Reason:** ${step.revision_reason}`);
    }
  }

  return lines.join("\n");
}

/**
 * Parse a Beads note back to a partial step object.
 *
 * Used for cross-session restoration.
 */
export function parseBeadsNote(note: string): Partial<FlowThinkStep> | null {
  // Match the header pattern
  const headerMatch = note.match(/^## Step (\d+)\/(\d+): (\w+)/m);
  if (!headerMatch) {
    return null;
  }

  const step: Partial<FlowThinkStep> = {
    step_number: parseInt(headerMatch[1], 10),
    estimated_total: parseInt(headerMatch[2], 10),
    purpose: headerMatch[3],
  };

  // Parse timestamp
  const timestampMatch = note.match(/^\*([^*]+)\*$/m);
  if (timestampMatch) {
    step.timestamp = timestampMatch[1];
  }

  // Parse core fields
  const contextMatch = note.match(/\*\*Context:\*\* (.+)$/m);
  if (contextMatch) step.context = contextMatch[1];

  const thoughtMatch = note.match(/\*\*Thought:\*\* (.+)$/m);
  if (thoughtMatch) step.thought = thoughtMatch[1];

  const outcomeMatch = note.match(/\*\*Outcome:\*\* (.+)$/m);
  if (outcomeMatch) step.outcome = outcomeMatch[1];

  const nextMatch = note.match(/\*\*Next:\*\* (.+)$/m);
  if (nextMatch) {
    // Check for tool prefix
    const toolMatch = nextMatch[1].match(/^\[(\w+)\] (.+)$/);
    if (toolMatch) {
      step.next_action = {
        tool: toolMatch[1],
        action: toolMatch[2],
      };
    } else {
      step.next_action = nextMatch[1];
    }
  }

  const rationaleMatch = note.match(/\*\*Rationale:\*\* (.+)$/m);
  if (rationaleMatch) step.rationale = rationaleMatch[1];

  // Parse optional fields
  const confidenceMatch = note.match(/\*\*Confidence:\*\* (\d+)%/m);
  if (confidenceMatch) {
    step.confidence = parseInt(confidenceMatch[1], 10) / 100;
  }

  const hypothesisMatch = note.match(/\*\*Hypothesis:\*\* (.+) \[(pending|confirmed|refuted)\]/m);
  if (hypothesisMatch) {
    step.hypothesis = hypothesisMatch[1];
    step.verification_status = hypothesisMatch[2] as "pending" | "confirmed" | "refuted";
  }

  const filesMatch = note.match(/\*\*Files:\*\* (.+)$/m);
  if (filesMatch) {
    step.files_referenced = filesMatch[1].split(", ");
  }

  const patternsMatch = note.match(/\*\*Patterns:\*\* (.+)$/m);
  if (patternsMatch) {
    step.patterns_discovered = patternsMatch[1].split(", ");
  }

  const branchMatch = note.match(/\*\*Branch:\*\* (.+)$/m);
  if (branchMatch) {
    // Try to extract branch_id from format "name (id)" or just "id"
    const branchParts = branchMatch[1].match(/(.+) \(([^)]+)\)$/);
    if (branchParts) {
      step.branch_name = branchParts[1];
      step.branch_id = branchParts[2];
    } else {
      step.branch_id = branchMatch[1];
    }
  }

  const revisesMatch = note.match(/\*\*Revises:\*\* Step (\d+)/m);
  if (revisesMatch) {
    step.revises_step = parseInt(revisesMatch[1], 10);
  }

  const reasonMatch = note.match(/\*\*Reason:\*\* (.+)$/m);
  if (reasonMatch) {
    step.revision_reason = reasonMatch[1];
  }

  return step;
}

/**
 * Create initial Beads session metadata.
 */
export function createBeadsSessionMetadata(epicId?: string): BeadsSessionMetadata {
  return {
    epic_id: epicId,
    synced_count: 0,
    failed_count: 0,
  };
}

/**
 * Create initial Beads step metadata.
 */
export function createBeadsStepMetadata(): BeadsStepMetadata {
  return {
    sync_status: "pending",
    retries: 0,
  };
}
