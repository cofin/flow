/**
 * Flow Think MCP - Beads Restoration Tests
 *
 * Tests for cross-session restoration from Beads.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import { BeadsRestoration } from "../src/beads/restoration.js";
import { clearBeadsCache } from "../src/beads/detection.js";
import type { FlowThinkStep } from "../src/types.js";

describe("BeadsRestoration", () => {
  let restoration: BeadsRestoration;

  beforeEach(() => {
    clearBeadsCache();
    restoration = new BeadsRestoration();
  });

  describe("parseStepsFromNotes", () => {
    test("parses single step", () => {
      const notes = `## Step 1/3: planning
*2026-01-31T10:00:00Z*

**Context:** Starting task
**Thought:** Analyzing requirements
**Outcome:** Requirements understood
**Next:** Read spec
**Rationale:** Need to understand first
`;

      const steps = restoration.parseStepsFromNotes(notes);

      expect(steps).toHaveLength(1);
      expect(steps[0].step_number).toBe(1);
      expect(steps[0].purpose).toBe("planning");
    });

    test("parses multiple steps", () => {
      const notes = `## Step 1/3: planning
**Context:** Starting
**Thought:** Planning approach
**Outcome:** Plan ready
**Next:** Implement
**Rationale:** Need plan

## Step 2/3: implement
**Context:** Plan ready
**Thought:** Writing code
**Outcome:** Code written
**Next:** Test
**Rationale:** Follow plan

## Step 3/3: validation
**Context:** Code ready
**Thought:** Testing
**Outcome:** Tests pass
**Next:** Done
**Rationale:** Verify correctness
`;

      const steps = restoration.parseStepsFromNotes(notes);

      expect(steps).toHaveLength(3);
      expect(steps[0].step_number).toBe(1);
      expect(steps[1].step_number).toBe(2);
      expect(steps[2].step_number).toBe(3);
    });

    test("sorts steps by step number", () => {
      const notes = `## Step 3/3: validation
**Context:** Testing
**Thought:** Running tests
**Outcome:** Pass
**Next:** Done
**Rationale:** Verify

## Step 1/3: planning
**Context:** Starting
**Thought:** Planning
**Outcome:** Plan
**Next:** Code
**Rationale:** Plan first
`;

      const steps = restoration.parseStepsFromNotes(notes);

      expect(steps[0].step_number).toBe(1);
      expect(steps[1].step_number).toBe(3);
    });

    test("handles empty notes", () => {
      const steps = restoration.parseStepsFromNotes("");
      expect(steps).toHaveLength(0);
    });

    test("handles notes without step format", () => {
      const notes = "Just some random notes without step formatting.";
      const steps = restoration.parseStepsFromNotes(notes);
      expect(steps).toHaveLength(0);
    });
  });

  describe("createContextSummary", () => {
    test("creates summary from steps", () => {
      const steps = [
        {
          step_number: 1,
          purpose: "planning",
          thought: "Planning the approach",
          outcome: "Plan created",
        },
        {
          step_number: 2,
          purpose: "implement",
          thought: "Writing code",
          outcome: "Code complete",
          next_action: "Run tests",
        },
      ];

      const summary = restoration.createContextSummary(steps);

      expect(summary).toContain("Previous Reasoning Context (2 steps)");
      expect(summary).toContain("Step 1: planning");
      expect(summary).toContain("Planning the approach");
      expect(summary).toContain("Last State");
      expect(summary).toContain("Pending action: Run tests");
    });

    test("handles empty steps", () => {
      const summary = restoration.createContextSummary([]);
      expect(summary).toContain("No previous reasoning context found");
    });

    test("includes hypothesis in summary", () => {
      const steps = [
        {
          step_number: 1,
          purpose: "debug",
          thought: "Investigating",
          outcome: "Found issue",
          hypothesis: "Memory leak in handler",
          verification_status: "confirmed" as const,
        },
      ];

      const summary = restoration.createContextSummary(steps);

      expect(summary).toContain("Memory leak in handler");
      expect(summary).toContain("[confirmed]");
    });
  });

  describe("mergeIntoHistory", () => {
    test("merges non-conflicting steps", () => {
      const existing: FlowThinkStep[] = [
        {
          step_number: 1,
          estimated_total: 3,
          purpose: "planning",
          context: "Starting",
          thought: "Planning",
          outcome: "Plan ready",
          next_action: "Code",
          rationale: "Need plan",
        },
      ];

      const restored = [
        {
          step_number: 2,
          estimated_total: 3,
          purpose: "implement",
          context: "Plan ready",
          thought: "Coding",
          outcome: "Code done",
          next_action: "Test",
          rationale: "Follow plan",
        },
      ];

      const { merged, conflicts } = restoration.mergeIntoHistory(existing, restored);

      expect(merged).toHaveLength(2);
      expect(conflicts).toHaveLength(0);
    });

    test("detects conflicting step numbers", () => {
      const existing: FlowThinkStep[] = [
        {
          step_number: 1,
          estimated_total: 2,
          purpose: "planning",
          context: "Start",
          thought: "Plan",
          outcome: "Done",
          next_action: "Next",
          rationale: "Reason",
        },
      ];

      const restored = [
        {
          step_number: 1,
          estimated_total: 2,
          purpose: "different",
          context: "Other",
          thought: "Other",
          outcome: "Other",
          next_action: "Other",
          rationale: "Other",
        },
      ];

      const { merged, conflicts } = restoration.mergeIntoHistory(existing, restored);

      expect(merged).toHaveLength(1);
      expect(conflicts).toContain(1);
    });

    test("skips incomplete restored steps", () => {
      const existing: FlowThinkStep[] = [];
      const restored = [
        {
          step_number: 1,
          purpose: "planning",
          // Missing required fields
        },
      ];

      const { merged, conflicts } = restoration.mergeIntoHistory(existing, restored);

      expect(merged).toHaveLength(0);
      expect(conflicts).toHaveLength(0);
    });

    test("sorts merged result by step number", () => {
      const existing: FlowThinkStep[] = [
        {
          step_number: 3,
          estimated_total: 4,
          purpose: "test",
          context: "Code",
          thought: "Testing",
          outcome: "Pass",
          next_action: "Done",
          rationale: "Verify",
        },
      ];

      const restored = [
        {
          step_number: 1,
          estimated_total: 4,
          purpose: "planning",
          context: "Start",
          thought: "Plan",
          outcome: "Ready",
          next_action: "Code",
          rationale: "First",
        },
        {
          step_number: 2,
          estimated_total: 4,
          purpose: "implement",
          context: "Plan",
          thought: "Code",
          outcome: "Done",
          next_action: "Test",
          rationale: "Build",
        },
      ];

      const { merged } = restoration.mergeIntoHistory(existing, restored);

      expect(merged.map((s) => s.step_number)).toEqual([1, 2, 3]);
    });
  });

  describe("restoreFromEpic", () => {
    test("returns error when Beads not available", async () => {
      // Use non-existent directory
      const r = new BeadsRestoration("/tmp/nonexistent-dir-12345");
      const result = await r.restoreFromEpic("any-epic");

      expect(result.success).toBe(false);
      expect(result.error).toContain("not available");
    });
  });
});
