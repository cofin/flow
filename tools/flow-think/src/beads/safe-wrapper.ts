/**
 * Flow Think MCP - Safe Beads Wrapper
 *
 * Provides graceful degradation for all Beads operations.
 * Never throws - logs warnings and continues.
 */

import type { FlowThinkStep } from "../types.js";
import { BeadsDetection } from "./detection.js";
import { BeadsSync, type SyncResult, type BeadsSyncOptions } from "./sync.js";
import { BeadsSessionManager, type SessionEpicMapping } from "./session-manager.js";
import { BeadsRestoration, type RestorationResult } from "./restoration.js";

/**
 * Beads operation result wrapper.
 */
export interface SafeResult<T> {
  /** Whether the operation succeeded */
  success: boolean;
  /** Result data if successful */
  data?: T;
  /** Warning message if degraded */
  warning?: string;
  /** Whether Beads was available */
  beads_available: boolean;
}

/**
 * Safe Beads integration that never throws.
 *
 * All operations gracefully degrade when Beads is unavailable.
 */
export class SafeBeadsWrapper {
  private detection: BeadsDetection;
  private sync: BeadsSync;
  private sessionManager: BeadsSessionManager;
  private restoration: BeadsRestoration;
  private enabled: boolean;
  private warningsLogged: Set<string> = new Set();

  constructor(options: BeadsSyncOptions = {}) {
    this.enabled = options.enabled ?? true;
    this.detection = new BeadsDetection();
    this.sync = new BeadsSync(options);
    this.sessionManager = new BeadsSessionManager(options.workingDirectory);
    this.restoration = new BeadsRestoration(options.workingDirectory);
  }

  /**
   * Check if Beads is available.
   */
  async isAvailable(): Promise<boolean> {
    if (!this.enabled) {
      return false;
    }

    try {
      const status = await this.detection.getBeadsStatus();
      return status.available;
    } catch {
      this.logWarningOnce("detection", "Failed to detect Beads availability");
      return false;
    }
  }

  /**
   * Safely sync a step to Beads.
   *
   * Never throws - returns a result indicating success or degradation.
   */
  async syncStep(
    step: FlowThinkStep,
    sessionId: string | undefined,
    stepEpicId?: string
  ): Promise<SafeResult<SyncResult>> {
    if (!this.enabled) {
      return {
        success: true,
        beads_available: false,
        warning: "Beads sync disabled",
      };
    }

    try {
      // Resolve epic ID
      const epicId = sessionId
        ? this.sessionManager.resolveEpicId(sessionId, stepEpicId, step.flow_id)
        : stepEpicId;

      if (!epicId) {
        return {
          success: true,
          beads_available: await this.isAvailable(),
          warning: "No epic ID for sync",
        };
      }

      const result = await this.sync.syncStep(step, epicId);

      // Record sync if successful
      if (result.status === "synced" && sessionId) {
        this.sessionManager.recordSync(sessionId);
      }

      return {
        success: result.status !== "failed",
        data: result,
        beads_available: true,
      };
    } catch (error) {
      this.logWarningOnce("sync", `Beads sync error: ${error}`);
      return {
        success: true, // Degraded but not failed
        beads_available: false,
        warning: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Safely restore context from Beads.
   *
   * Never throws - returns empty context if unavailable.
   */
  async restoreContext(epicId: string): Promise<SafeResult<RestorationResult>> {
    if (!this.enabled) {
      return {
        success: true,
        beads_available: false,
        warning: "Beads sync disabled",
      };
    }

    try {
      const result = await this.restoration.restoreFromEpic(epicId);
      return {
        success: result.success,
        data: result,
        beads_available: result.success || result.error !== "Beads not available",
      };
    } catch (error) {
      this.logWarningOnce("restore", `Beads restore error: ${error}`);
      return {
        success: true,
        beads_available: false,
        warning: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Safely register a session-epic mapping.
   */
  registerSession(sessionId: string, epicId: string): SafeResult<SessionEpicMapping> {
    try {
      const mapping = this.sessionManager.registerMapping(sessionId, epicId);
      return {
        success: true,
        data: mapping,
        beads_available: true,
      };
    } catch (error) {
      this.logWarningOnce("register", `Session registration error: ${error}`);
      return {
        success: false,
        beads_available: false,
        warning: error instanceof Error ? error.message : String(error),
      };
    }
  }

  /**
   * Get epic ID for a session.
   */
  getEpicForSession(sessionId: string): string | undefined {
    return this.sessionManager.getEpicForSession(sessionId);
  }

  /**
   * Get sync statistics.
   */
  getStats(): {
    sync: ReturnType<BeadsSync["getStats"]>;
    sessions: SessionEpicMapping[];
  } {
    return {
      sync: this.sync.getStats(),
      sessions: this.sessionManager.listMappings(),
    };
  }

  /**
   * Create context summary from restored steps.
   */
  createContextSummary(steps: Partial<FlowThinkStep>[]): string {
    return this.restoration.createContextSummary(steps);
  }

  /**
   * Log warning once per category.
   */
  private logWarningOnce(category: string, message: string): void {
    if (this.warningsLogged.has(category)) {
      return;
    }
    this.warningsLogged.add(category);
    console.error(`⚠️ [Beads] ${message}`);
  }

  /**
   * Reset warning tracking (useful for testing).
   */
  resetWarnings(): void {
    this.warningsLogged.clear();
  }
}
