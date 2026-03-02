/**
 * Flow Think MCP - Beads Sync
 *
 * Synchronizes reasoning steps to Beads notes.
 */

import type { FlowThinkStep } from "../types.js";
import { BeadsDetection } from "./detection.js";
import { formatStepForBeads, type BeadsSyncStatus } from "./types.js";

/**
 * Result of a sync operation.
 */
export interface SyncResult {
  /** Status of the sync */
  status: BeadsSyncStatus;
  /** Reason if skipped or failed */
  reason?: string;
  /** When synced (if successful) */
  synced_at?: string;
  /** Step number that was synced */
  step_number: number;
}

/**
 * Options for BeadsSync.
 */
export interface BeadsSyncOptions {
  /** Whether sync is enabled */
  enabled?: boolean;
  /** Maximum retry attempts */
  maxRetries?: number;
  /** Delay between retries in ms */
  retryDelayMs?: number;
  /** Directory to check for Beads initialization */
  workingDirectory?: string;
}

/**
 * Sync statistics.
 */
export interface SyncStats {
  /** Total sync attempts */
  total_attempts: number;
  /** Successfully synced */
  synced_count: number;
  /** Failed syncs */
  failed_count: number;
  /** Skipped syncs */
  skipped_count: number;
  /** Last sync timestamp */
  last_sync_at?: string;
}

/**
 * Beads synchronization service.
 *
 * Handles syncing reasoning steps to Beads notes.
 */
export class BeadsSync {
  private detection: BeadsDetection;
  private enabled: boolean;
  private maxRetries: number;
  private retryDelayMs: number;
  private workingDirectory?: string;

  // Statistics
  private stats: SyncStats = {
    total_attempts: 0,
    synced_count: 0,
    failed_count: 0,
    skipped_count: 0,
  };

  constructor(options: BeadsSyncOptions = {}) {
    this.detection = new BeadsDetection();
    this.enabled = options.enabled ?? true;
    this.maxRetries = options.maxRetries ?? 3;
    this.retryDelayMs = options.retryDelayMs ?? 1000;
    this.workingDirectory = options.workingDirectory;
  }

  /**
   * Check if sync is enabled and Beads is available.
   */
  async isEnabled(): Promise<boolean> {
    if (!this.enabled) {
      return false;
    }

    const status = await this.detection.getBeadsStatus(this.workingDirectory);
    return status.available;
  }

  /**
   * Format a step for Beads notes.
   */
  formatStep(step: FlowThinkStep): string {
    return formatStepForBeads(step);
  }

  /**
   * Sync a single step to Beads.
   *
   * @param step - The step to sync
   * @param epicId - The Beads epic ID to sync to
   */
  async syncStep(step: FlowThinkStep, epicId: string | undefined): Promise<SyncResult> {
    this.stats.total_attempts++;

    // Check if sync is enabled
    if (!this.enabled) {
      this.stats.skipped_count++;
      return {
        status: "skipped",
        reason: "Beads sync disabled",
        step_number: step.step_number,
      };
    }

    // Check if epic ID is provided
    if (!epicId) {
      this.stats.skipped_count++;
      return {
        status: "skipped",
        reason: "No epic ID provided",
        step_number: step.step_number,
      };
    }

    // Check if Beads is available
    const available = await this.isEnabled();
    if (!available) {
      this.stats.skipped_count++;
      return {
        status: "skipped",
        reason: "Beads not available",
        step_number: step.step_number,
      };
    }

    // Format the step
    const note = this.formatStep(step);

    // Try to sync with retries
    let lastError: Error | undefined;
    for (let attempt = 0; attempt < this.maxRetries; attempt++) {
      try {
        await this.executeSync(epicId, note);
        this.stats.synced_count++;
        this.stats.last_sync_at = new Date().toISOString();

        return {
          status: "synced",
          synced_at: this.stats.last_sync_at,
          step_number: step.step_number,
        };
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Wait before retry (except on last attempt)
        if (attempt < this.maxRetries - 1) {
          await this.delay(this.retryDelayMs);
        }
      }
    }

    this.stats.failed_count++;
    return {
      status: "failed",
      reason: lastError?.message ?? "Unknown error",
      step_number: step.step_number,
    };
  }

  /**
   * Sync multiple steps to Beads.
   */
  async syncSession(steps: FlowThinkStep[], epicId: string | undefined): Promise<SyncResult[]> {
    const results: SyncResult[] = [];

    for (const step of steps) {
      const result = await this.syncStep(step, epicId);
      results.push(result);
    }

    return results;
  }

  /**
   * Execute the actual sync to Beads.
   *
   * Uses `bd update --append-notes` to add the note.
   */
  private async executeSync(epicId: string, note: string): Promise<void> {
    // Escape the note for shell
    const escapedNote = note.replace(/'/g, "'\\''");

    const proc = Bun.spawn(["bd", "update", epicId, "--append-notes", escapedNote], {
      stdout: "pipe",
      stderr: "pipe",
      cwd: this.workingDirectory,
    });

    const exitCode = await proc.exited;

    if (exitCode !== 0) {
      const stderr = await new Response(proc.stderr).text();
      throw new Error(`bd update failed: ${stderr}`);
    }

    console.error(`📝 Synced step to Beads epic ${epicId}`);
  }

  /**
   * Get sync statistics.
   */
  getStats(): SyncStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      total_attempts: 0,
      synced_count: 0,
      failed_count: 0,
      skipped_count: 0,
    };
  }

  /**
   * Delay helper for retries.
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
