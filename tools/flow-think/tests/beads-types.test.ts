/**
 * Flow Think MCP - Beads Types Tests
 *
 * Tests for Beads-related type definitions and utilities.
 */

import { describe, test, expect } from "bun:test";
import type {
  BeadsSyncStatus,
  BeadsSessionMetadata,
  BeadsStepMetadata,
} from "../src/beads/types.js";
import {
  formatStepForBeads,
  parseBeadsNote,
  BEADS_SYNC_STATUSES,
} from "../src/beads/types.js";

describe("Beads Types", () => {
  describe("BeadsSyncStatus", () => {
    test("has expected status values", () => {
      expect(BEADS_SYNC_STATUSES).toContain("pending");
      expect(BEADS_SYNC_STATUSES).toContain("synced");
      expect(BEADS_SYNC_STATUSES).toContain("failed");
      expect(BEADS_SYNC_STATUSES).toContain("skipped");
    });
  });

  describe("formatStepForBeads", () => {
    test("formats step with all fields", () => {
      const step = {
        step_number: 1,
        estimated_total: 5,
        purpose: "planning",
        context: "Starting task",
        thought: "Need to analyze requirements",
        outcome: "Requirements understood",
        next_action: "Read spec file",
        rationale: "Must understand before implementing",
        confidence: 0.8,
        hypothesis: "The feature needs X",
        verification_status: "pending" as const,
      };

      const formatted = formatStepForBeads(step);

      expect(formatted).toContain("## Step 1/5: planning");
      expect(formatted).toContain("**Confidence:** 80%");
      expect(formatted).toContain("**Hypothesis:** The feature needs X");
      expect(formatted).toContain("Starting task");
      expect(formatted).toContain("Need to analyze requirements");
    });

    test("formats step without optional fields", () => {
      const step = {
        step_number: 1,
        estimated_total: 3,
        purpose: "debug",
        context: "Found bug",
        thought: "Investigating",
        outcome: "Root cause found",
        next_action: "Fix it",
        rationale: "Bug must be fixed",
      };

      const formatted = formatStepForBeads(step);

      expect(formatted).toContain("## Step 1/3: debug");
      expect(formatted).not.toContain("**Confidence:**");
      expect(formatted).not.toContain("**Hypothesis:**");
    });

    test("formats structured next_action", () => {
      const step = {
        step_number: 2,
        estimated_total: 4,
        purpose: "implement",
        context: "Ready to code",
        thought: "Will use Edit tool",
        outcome: "File modified",
        next_action: {
          tool: "Edit",
          action: "Update the handler",
          expectedOutput: "Handler updated",
        },
        rationale: "Need to modify handler",
      };

      const formatted = formatStepForBeads(step);

      expect(formatted).toContain("**Next:** [Edit] Update the handler");
    });

    test("includes timestamp when provided", () => {
      const step = {
        step_number: 1,
        estimated_total: 2,
        purpose: "analysis",
        context: "Reviewing",
        thought: "Looking at code",
        outcome: "Found pattern",
        next_action: "Document it",
        rationale: "For future reference",
        timestamp: "2026-01-31T10:00:00Z",
      };

      const formatted = formatStepForBeads(step);

      expect(formatted).toContain("2026-01-31T10:00:00Z");
    });
  });

  describe("parseBeadsNote", () => {
    test("parses formatted step back to object", () => {
      const note = `## Step 3/5: debug
*2026-01-31T10:00:00Z*

**Context:** Found the bug in auth module
**Thought:** The session is not being cleared
**Outcome:** Need to add session.clear()
**Next:** Edit the auth handler
**Rationale:** Session leak causes issues

**Confidence:** 85%
**Hypothesis:** Session not cleared [pending]
`;

      const parsed = parseBeadsNote(note);

      expect(parsed).not.toBeNull();
      expect(parsed?.step_number).toBe(3);
      expect(parsed?.estimated_total).toBe(5);
      expect(parsed?.purpose).toBe("debug");
      expect(parsed?.confidence).toBe(0.85);
    });

    test("returns null for invalid note", () => {
      const note = "This is not a valid step note";
      const parsed = parseBeadsNote(note);

      expect(parsed).toBeNull();
    });

    test("handles note without optional fields", () => {
      const note = `## Step 1/2: planning
**Context:** Starting
**Thought:** Planning approach
**Outcome:** Plan ready
**Next:** Implement
**Rationale:** Need a plan
`;

      const parsed = parseBeadsNote(note);

      expect(parsed).not.toBeNull();
      expect(parsed?.confidence).toBeUndefined();
      expect(parsed?.hypothesis).toBeUndefined();
    });
  });
});
