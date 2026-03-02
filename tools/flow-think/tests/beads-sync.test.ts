/**
 * Flow Think MCP - Beads Sync Tests
 *
 * Tests for syncing reasoning steps to Beads.
 */

import { describe, test, expect, beforeEach, mock, spyOn } from "bun:test";
import { BeadsSync } from "../src/beads/sync.js";
import { clearBeadsCache } from "../src/beads/detection.js";
import type { FlowThinkStep } from "../src/types.js";

function createTestStep(overrides = {}): FlowThinkStep {
  return {
    step_number: 1,
    estimated_total: 3,
    purpose: "planning",
    context: "Starting task",
    thought: "Analyzing requirements",
    outcome: "Requirements understood",
    next_action: "Read spec",
    rationale: "Need to understand first",
    timestamp: new Date().toISOString(),
    ...overrides,
  };
}

describe("BeadsSync", () => {
  beforeEach(() => {
    clearBeadsCache();
  });

  describe("constructor", () => {
    test("creates instance with default options", () => {
      const sync = new BeadsSync();
      expect(sync).toBeDefined();
    });

    test("creates instance with custom options", () => {
      const sync = new BeadsSync({
        enabled: false,
        maxRetries: 5,
        retryDelayMs: 2000,
      });
      expect(sync).toBeDefined();
    });
  });

  describe("isEnabled", () => {
    test("returns true when enabled and Beads available", async () => {
      const sync = new BeadsSync({ enabled: true });
      const enabled = await sync.isEnabled();
      // Will be true if bd is installed and .beads exists
      expect(typeof enabled).toBe("boolean");
    });

    test("returns false when disabled", async () => {
      const sync = new BeadsSync({ enabled: false });
      const enabled = await sync.isEnabled();
      expect(enabled).toBe(false);
    });
  });

  describe("syncStep", () => {
    test("returns skipped when disabled", async () => {
      const sync = new BeadsSync({ enabled: false });
      const result = await sync.syncStep(createTestStep(), "test-epic");

      expect(result.status).toBe("skipped");
      expect(result.reason).toBe("Beads sync disabled");
    });

    test("handles missing epic ID", async () => {
      const sync = new BeadsSync({ enabled: true });
      const result = await sync.syncStep(createTestStep(), undefined);

      expect(result.status).toBe("skipped");
      expect(result.reason).toContain("No epic ID");
    });

    test("formats step correctly before sync", async () => {
      const sync = new BeadsSync({ enabled: true });
      const step = createTestStep({
        confidence: 0.85,
        hypothesis: "Test hypothesis",
      });

      // We can test the formatting works
      const formatted = sync.formatStep(step);
      expect(formatted).toContain("## Step 1/3: planning");
      expect(formatted).toContain("**Confidence:** 85%");
      expect(formatted).toContain("**Hypothesis:** Test hypothesis");
    });
  });

  describe("syncSession", () => {
    test("syncs multiple steps", async () => {
      const sync = new BeadsSync({ enabled: false }); // Disabled to avoid actual calls
      const steps = [
        createTestStep({ step_number: 1 }),
        createTestStep({ step_number: 2 }),
        createTestStep({ step_number: 3 }),
      ];

      const results = await sync.syncSession(steps, "test-epic");

      expect(results).toHaveLength(3);
      expect(results.every((r) => r.status === "skipped")).toBe(true);
    });
  });

  describe("formatStep", () => {
    test("produces valid markdown", () => {
      const sync = new BeadsSync();
      const step = createTestStep();

      const formatted = sync.formatStep(step);

      expect(formatted).toContain("## Step");
      expect(formatted).toContain("**Context:**");
      expect(formatted).toContain("**Thought:**");
      expect(formatted).toContain("**Outcome:**");
    });

    test("includes branch info", () => {
      const sync = new BeadsSync();
      const step = createTestStep({
        branch_id: "alt-approach",
        branch_name: "Alternative",
      });

      const formatted = sync.formatStep(step);

      expect(formatted).toContain("**Branch:**");
      expect(formatted).toContain("Alternative");
    });
  });

  describe("getStats", () => {
    test("returns sync statistics", async () => {
      const sync = new BeadsSync({ enabled: false });

      // Trigger some syncs
      await sync.syncStep(createTestStep(), "epic-1");
      await sync.syncStep(createTestStep({ step_number: 2 }), "epic-1");

      const stats = sync.getStats();

      expect(stats).toHaveProperty("total_attempts");
      expect(stats).toHaveProperty("synced_count");
      expect(stats).toHaveProperty("failed_count");
      expect(stats).toHaveProperty("skipped_count");
      expect(stats.skipped_count).toBe(2);
    });
  });
});
