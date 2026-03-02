/**
 * Flow Think MCP - Beads Cross-Session Restoration
 *
 * Restores previous reasoning context from Beads notes.
 */

import type { FlowThinkStep } from "../types.js";
import { BeadsDetection } from "./detection.js";
import { parseBeadsNote } from "./types.js";

/**
 * Result of a restoration attempt.
 */
export interface RestorationResult {
  /** Whether restoration was successful */
  success: boolean;
  /** Number of steps restored */
  steps_restored: number;
  /** Error message if failed */
  error?: string;
  /** Restored steps */
  steps?: Partial<FlowThinkStep>[];
}

/**
 * Beads restoration service.
 *
 * Handles restoring previous reasoning context from Beads.
 */
export class BeadsRestoration {
  private detection: BeadsDetection;
  private workingDirectory?: string;

  constructor(workingDirectory?: string) {
    this.detection = new BeadsDetection();
    this.workingDirectory = workingDirectory;
  }

  /**
   * Restore reasoning context from a Beads epic.
   *
   * Fetches the epic's notes and parses any reasoning steps.
   */
  async restoreFromEpic(epicId: string): Promise<RestorationResult> {
    const status = await this.detection.getBeadsStatus(this.workingDirectory);
    if (!status.available) {
      return {
        success: false,
        steps_restored: 0,
        error: "Beads not available",
      };
    }

    try {
      // Fetch epic notes
      const notes = await this.fetchEpicNotes(epicId);
      if (!notes) {
        return {
          success: true,
          steps_restored: 0,
          steps: [],
        };
      }

      // Parse steps from notes
      const steps = this.parseStepsFromNotes(notes);

      console.error(`📥 Restored ${steps.length} steps from Beads epic ${epicId}`);

      return {
        success: true,
        steps_restored: steps.length,
        steps,
      };
    } catch (error) {
      return {
        success: false,
        steps_restored: 0,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Fetch notes from a Beads epic.
   */
  private async fetchEpicNotes(epicId: string): Promise<string | null> {
    try {
      const proc = Bun.spawn(["bd", "show", epicId], {
        stdout: "pipe",
        stderr: "pipe",
        cwd: this.workingDirectory,
      });

      const exitCode = await proc.exited;
      if (exitCode !== 0) {
        return null;
      }

      const stdout = await new Response(proc.stdout).text();

      // Extract notes section from output
      // bd show output format includes a "Notes:" section
      const notesMatch = stdout.match(/Notes:\s*\n([\s\S]*?)(?=\n\w+:|$)/);
      return notesMatch ? notesMatch[1].trim() : null;
    } catch {
      return null;
    }
  }

  /**
   * Parse reasoning steps from Beads notes.
   *
   * Notes may contain multiple step entries separated by "---".
   */
  parseStepsFromNotes(notes: string): Partial<FlowThinkStep>[] {
    const steps: Partial<FlowThinkStep>[] = [];

    // Split by step headers (## Step N/M:)
    const stepSections = notes.split(/(?=^## Step \d+\/\d+:)/m);

    for (const section of stepSections) {
      if (!section.trim()) continue;

      const parsed = parseBeadsNote(section);
      if (parsed) {
        steps.push(parsed);
      }
    }

    // Sort by step number
    steps.sort((a, b) => (a.step_number ?? 0) - (b.step_number ?? 0));

    return steps;
  }

  /**
   * Create a history summary from restored steps.
   *
   * Useful for providing context to new reasoning sessions.
   */
  createContextSummary(steps: Partial<FlowThinkStep>[]): string {
    if (steps.length === 0) {
      return "No previous reasoning context found.";
    }

    const lines: string[] = [
      `# Previous Reasoning Context (${steps.length} steps)`,
      "",
    ];

    for (const step of steps) {
      lines.push(`## Step ${step.step_number}: ${step.purpose}`);
      if (step.thought) {
        lines.push(`- ${step.thought}`);
      }
      if (step.outcome) {
        lines.push(`  → ${step.outcome}`);
      }
      lines.push("");
    }

    // Add summary of final state
    const lastStep = steps[steps.length - 1];
    if (lastStep) {
      lines.push("## Last State");
      if (lastStep.hypothesis) {
        const status = lastStep.verification_status ?? "pending";
        lines.push(`- Hypothesis: ${lastStep.hypothesis} [${status}]`);
      }
      if (lastStep.next_action) {
        const action = typeof lastStep.next_action === "string"
          ? lastStep.next_action
          : lastStep.next_action.action;
        lines.push(`- Pending action: ${action}`);
      }
    }

    return lines.join("\n");
  }

  /**
   * Merge restored steps into existing history.
   *
   * Useful when resuming a session with existing steps.
   */
  mergeIntoHistory(
    existingSteps: FlowThinkStep[],
    restoredSteps: Partial<FlowThinkStep>[]
  ): {
    merged: FlowThinkStep[];
    conflicts: number[];
  } {
    const existingNumbers = new Set(existingSteps.map((s) => s.step_number));
    const merged: FlowThinkStep[] = [...existingSteps];
    const conflicts: number[] = [];

    for (const restored of restoredSteps) {
      if (restored.step_number === undefined) continue;

      if (existingNumbers.has(restored.step_number)) {
        conflicts.push(restored.step_number);
      } else {
        // Only add if it has all required fields
        if (this.isCompleteStep(restored)) {
          merged.push(restored as FlowThinkStep);
        }
      }
    }

    // Sort by step number
    merged.sort((a, b) => a.step_number - b.step_number);

    return { merged, conflicts };
  }

  /**
   * Check if a partial step has all required fields.
   */
  private isCompleteStep(step: Partial<FlowThinkStep>): boolean {
    return !!(
      step.step_number !== undefined &&
      step.estimated_total !== undefined &&
      step.purpose &&
      step.context &&
      step.thought &&
      step.outcome &&
      step.next_action &&
      step.rationale
    );
  }
}
