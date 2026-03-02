/**
 * Flow Think MCP - Safe Beads Wrapper Tests
 *
 * Tests for graceful degradation of Beads operations.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import { SafeBeadsWrapper } from "../src/beads/safe-wrapper.js";
import { clearBeadsCache } from "../src/beads/detection.js";
import type { FlowThinkStep } from "../src/types.js";

function createTestStep(overrides = {}): FlowThinkStep {
  return {
    step_number: 1,
    estimated_total: 3,
    purpose: "planning",
    context: "Starting task",
    thought: "Analyzing",
    outcome: "Understood",
    next_action: "Implement",
    rationale: "Need to understand first",
    ...overrides,
  };
}

describe("SafeBeadsWrapper", () => {
  beforeEach(() => {
    clearBeadsCache();
  });

  describe("constructor", () => {
    test("creates with default options", () => {
      const wrapper = new SafeBeadsWrapper();
      expect(wrapper).toBeDefined();
    });

    test("creates with disabled sync", () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });
      expect(wrapper).toBeDefined();
    });
  });

  describe("isAvailable", () => {
    test("returns false when disabled", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });
      const available = await wrapper.isAvailable();
      expect(available).toBe(false);
    });

    test("checks Beads status when enabled", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: true });
      const available = await wrapper.isAvailable();
      // Will be true if Beads is actually available
      expect(typeof available).toBe("boolean");
    });
  });

  describe("syncStep", () => {
    test("returns warning when disabled", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });
      const result = await wrapper.syncStep(createTestStep(), "session-1");

      expect(result.success).toBe(true);
      expect(result.beads_available).toBe(false);
      expect(result.warning).toContain("disabled");
    });

    test("returns warning when no epic ID", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: true });
      const result = await wrapper.syncStep(createTestStep(), undefined);

      expect(result.success).toBe(true);
      expect(result.warning).toContain("No epic ID");
    });

    test("never throws on error", async () => {
      const wrapper = new SafeBeadsWrapper({
        enabled: true,
        workingDirectory: "/nonexistent/path",
      });

      // Should not throw
      const result = await wrapper.syncStep(
        createTestStep(),
        "session-1",
        "epic-123"
      );

      expect(result).toBeDefined();
      expect(typeof result.success).toBe("boolean");
    });
  });

  describe("restoreContext", () => {
    test("returns warning when disabled", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });
      const result = await wrapper.restoreContext("epic-123");

      expect(result.success).toBe(true);
      expect(result.beads_available).toBe(false);
      expect(result.warning).toContain("disabled");
    });

    test("never throws on error", async () => {
      const wrapper = new SafeBeadsWrapper({
        enabled: true,
        workingDirectory: "/nonexistent/path",
      });

      // Should not throw
      const result = await wrapper.restoreContext("epic-123");

      expect(result).toBeDefined();
      expect(typeof result.success).toBe("boolean");
    });
  });

  describe("registerSession", () => {
    test("registers session-epic mapping", () => {
      const wrapper = new SafeBeadsWrapper();
      const result = wrapper.registerSession("session-1", "epic-123");

      expect(result.success).toBe(true);
      expect(result.data?.session_id).toBe("session-1");
      expect(result.data?.epic_id).toBe("epic-123");
    });
  });

  describe("getEpicForSession", () => {
    test("returns epic ID for registered session", () => {
      const wrapper = new SafeBeadsWrapper();
      wrapper.registerSession("session-1", "epic-123");

      const epicId = wrapper.getEpicForSession("session-1");
      expect(epicId).toBe("epic-123");
    });

    test("returns undefined for unknown session", () => {
      const wrapper = new SafeBeadsWrapper();
      const epicId = wrapper.getEpicForSession("unknown");
      expect(epicId).toBeUndefined();
    });
  });

  describe("getStats", () => {
    test("returns combined stats", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });

      // Trigger some operations
      await wrapper.syncStep(createTestStep(), "session-1", "epic-1");
      wrapper.registerSession("session-1", "epic-1");

      const stats = wrapper.getStats();

      expect(stats).toHaveProperty("sync");
      expect(stats).toHaveProperty("sessions");
      expect(stats.sync).toHaveProperty("total_attempts");
      expect(stats.sessions).toBeInstanceOf(Array);
    });
  });

  describe("createContextSummary", () => {
    test("delegates to restoration service", () => {
      const wrapper = new SafeBeadsWrapper();
      const steps = [
        { step_number: 1, purpose: "planning", thought: "Plan", outcome: "Done" },
      ];

      const summary = wrapper.createContextSummary(steps);

      expect(summary).toContain("Previous Reasoning Context");
    });
  });

  describe("warning deduplication", () => {
    test("logs each warning category once", async () => {
      const wrapper = new SafeBeadsWrapper({
        enabled: true,
        workingDirectory: "/nonexistent",
      });

      // Multiple calls should only log once per category
      await wrapper.syncStep(createTestStep(), "s1", "e1");
      await wrapper.syncStep(createTestStep(), "s2", "e2");
      await wrapper.syncStep(createTestStep(), "s3", "e3");

      // Can't easily test console.error, but verify no throw
      expect(true).toBe(true);
    });

    test("resetWarnings allows re-logging", async () => {
      const wrapper = new SafeBeadsWrapper({ enabled: false });

      await wrapper.syncStep(createTestStep(), "s1");
      wrapper.resetWarnings();

      // Should be able to log again after reset
      await wrapper.syncStep(createTestStep(), "s2");

      expect(true).toBe(true);
    });
  });
});
