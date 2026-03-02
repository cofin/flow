/**
 * Flow Think MCP - Beads Session Manager
 *
 * Manages mapping between MCP sessions and Beads epics.
 */

import { BeadsDetection } from "./detection.js";

/**
 * Mapping between session and Beads epic.
 */
export interface SessionEpicMapping {
  /** MCP session ID */
  session_id: string;
  /** Linked Beads epic ID */
  epic_id: string;
  /** When mapping was created */
  created_at: string;
  /** Last sync timestamp */
  last_synced_at?: string;
  /** Number of steps synced */
  synced_count: number;
}

/**
 * Epic info from Beads.
 */
export interface EpicInfo {
  /** Epic ID */
  id: string;
  /** Epic title */
  title?: string;
  /** Epic notes */
  notes?: string;
  /** Epic status */
  status?: string;
}

/**
 * Manages session-to-epic mappings for Beads integration.
 */
export class BeadsSessionManager {
  private mappings: Map<string, SessionEpicMapping> = new Map();
  private detection: BeadsDetection;
  private workingDirectory?: string;

  constructor(workingDirectory?: string) {
    this.detection = new BeadsDetection();
    this.workingDirectory = workingDirectory;
  }

  /**
   * Register a mapping between session and epic.
   */
  registerMapping(sessionId: string, epicId: string): SessionEpicMapping {
    const existing = this.mappings.get(sessionId);
    if (existing) {
      // Update existing mapping
      existing.epic_id = epicId;
      return existing;
    }

    const mapping: SessionEpicMapping = {
      session_id: sessionId,
      epic_id: epicId,
      created_at: new Date().toISOString(),
      synced_count: 0,
    };

    this.mappings.set(sessionId, mapping);
    console.error(`🔗 Mapped session ${sessionId} to epic ${epicId}`);
    return mapping;
  }

  /**
   * Get the epic ID for a session.
   */
  getEpicForSession(sessionId: string): string | undefined {
    return this.mappings.get(sessionId)?.epic_id;
  }

  /**
   * Get the mapping for a session.
   */
  getMapping(sessionId: string): SessionEpicMapping | undefined {
    return this.mappings.get(sessionId);
  }

  /**
   * Update sync stats for a mapping.
   */
  recordSync(sessionId: string): void {
    const mapping = this.mappings.get(sessionId);
    if (mapping) {
      mapping.synced_count++;
      mapping.last_synced_at = new Date().toISOString();
    }
  }

  /**
   * Remove a mapping.
   */
  removeMapping(sessionId: string): boolean {
    return this.mappings.delete(sessionId);
  }

  /**
   * List all mappings.
   */
  listMappings(): SessionEpicMapping[] {
    return Array.from(this.mappings.values());
  }

  /**
   * Fetch epic info from Beads.
   */
  async getEpicInfo(epicId: string): Promise<EpicInfo | null> {
    const status = await this.detection.getBeadsStatus(this.workingDirectory);
    if (!status.available) {
      return null;
    }

    try {
      const proc = Bun.spawn(["bd", "show", epicId, "--format", "json"], {
        stdout: "pipe",
        stderr: "pipe",
        cwd: this.workingDirectory,
      });

      const exitCode = await proc.exited;
      if (exitCode !== 0) {
        return null;
      }

      const stdout = await new Response(proc.stdout).text();
      const data = JSON.parse(stdout);

      return {
        id: epicId,
        title: data.title,
        notes: data.notes,
        status: data.status,
      };
    } catch {
      return null;
    }
  }

  /**
   * Try to auto-discover epic from session context.
   *
   * Checks if there's a beads_epic_id in step or session metadata.
   */
  resolveEpicId(
    sessionId: string,
    stepEpicId?: string,
    _flowId?: string
  ): string | undefined {
    // Priority: step-level override > registered mapping > flow-based lookup
    if (stepEpicId) {
      // Register this mapping for future steps
      this.registerMapping(sessionId, stepEpicId);
      return stepEpicId;
    }

    const registered = this.getEpicForSession(sessionId);
    if (registered) {
      return registered;
    }

    // Could attempt flow-based lookup here if flowId is provided
    // For now, return undefined if no mapping exists
    return undefined;
  }

  /**
   * Clear all mappings.
   */
  clear(): void {
    this.mappings.clear();
  }
}
