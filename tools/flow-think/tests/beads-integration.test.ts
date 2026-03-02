/**
 * Flow Think MCP - Beads Integration Tests
 *
 * Integration tests for Beads functionality with the server.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import { FlowThinkServer } from "../src/server.js";
import { getDefaultConfig } from "../src/config.js";
import { clearBeadsCache } from "../src/beads/detection.js";
import type { FlowThinkConfig } from "../src/types.js";

function createServer(configOverrides?: Partial<FlowThinkConfig>): FlowThinkServer {
  const config = { ...getDefaultConfig(), ...configOverrides };
  return new FlowThinkServer(config);
}

function createValidStep(overrides = {}) {
  return {
    step_number: 1,
    estimated_total: 3,
    purpose: "planning",
    context: "Starting a new task",
    thought: "I should analyze the requirements first",
    outcome: "Requirements understood",
    next_action: "Read the spec file",
    rationale: "Need to understand what to build",
    ...overrides,
  };
}

describe("Beads Integration", () => {
  beforeEach(() => {
    clearBeadsCache();
  });

  describe("server initialization", () => {
    test("creates server with beadsSync enabled by default", () => {
      const server = createServer();
      expect(server).toBeDefined();
    });

    test("creates server with beadsSync disabled", () => {
      const server = createServer({ beadsSync: false });
      expect(server).toBeDefined();
    });
  });

  describe("isBeadsAvailable", () => {
    test("returns boolean indicating Beads availability", async () => {
      const server = createServer();
      const available = await server.isBeadsAvailable();

      expect(typeof available).toBe("boolean");
    });

    test("returns false when beadsSync disabled", async () => {
      const server = createServer({ beadsSync: false });
      const available = await server.isBeadsAvailable();

      expect(available).toBe(false);
    });
  });

  describe("registerBeadsEpic", () => {
    test("registers session with epic", () => {
      const server = createServer();
      server.registerBeadsEpic("session-1", "epic-123");

      const stats = server.getBeadsStats();
      expect(stats.sessions).toHaveLength(1);
      expect(stats.sessions[0].session_id).toBe("session-1");
      expect(stats.sessions[0].epic_id).toBe("epic-123");
    });

    test("updates existing registration", () => {
      const server = createServer();
      server.registerBeadsEpic("session-1", "epic-123");
      server.registerBeadsEpic("session-1", "epic-456");

      const stats = server.getBeadsStats();
      expect(stats.sessions).toHaveLength(1);
      expect(stats.sessions[0].epic_id).toBe("epic-456");
    });
  });

  describe("getBeadsStats", () => {
    test("returns sync and session statistics", () => {
      const server = createServer({ beadsSync: false });
      server.registerBeadsEpic("session-1", "epic-1");
      server.registerBeadsEpic("session-2", "epic-2");

      const stats = server.getBeadsStats();

      expect(stats).toHaveProperty("sync");
      expect(stats).toHaveProperty("sessions");
      expect(stats.sync.total_attempts).toBe(0);
      expect(stats.sessions).toHaveLength(2);
    });
  });

  describe("restoreFromBeads", () => {
    test("returns failure when beadsSync disabled", async () => {
      const server = createServer({ beadsSync: false });
      const result = await server.restoreFromBeads("any-epic");

      expect(result.success).toBe(false);
      expect(result.steps_restored).toBe(0);
    });
  });

  describe("step processing with Beads", () => {
    test("processes step with beads_task_id", async () => {
      const server = createServer({ beadsSync: false });
      const step = createValidStep({
        beads_task_id: "task-123",
        session_id: "session-1",
      });

      const response = await server.processStep(step);

      expect(response.isError).toBeUndefined();
      const data = JSON.parse(response.content[0].text);
      expect(data.step_number).toBe(1);
    });

    test("processes step with flow_id", async () => {
      const server = createServer({ beadsSync: false });
      const step = createValidStep({
        flow_id: "flow-ri9.3",
        session_id: "session-1",
      });

      const response = await server.processStep(step);

      expect(response.isError).toBeUndefined();
    });

    test("processes step with patterns_discovered", async () => {
      const server = createServer({ beadsSync: false });
      const step = createValidStep({
        patterns_discovered: ["Pattern A", "Pattern B"],
      });

      const response = await server.processStep(step);

      expect(response.isError).toBeUndefined();
      const history = server.getHistory();
      expect(history.steps[0].patterns_discovered).toContain("Pattern A");
    });

    test("processes step with files_referenced", async () => {
      const server = createServer({ beadsSync: false });
      const step = createValidStep({
        files_referenced: ["src/server.ts", "src/types.ts"],
      });

      const response = await server.processStep(step);

      expect(response.isError).toBeUndefined();
      const history = server.getHistory();
      expect(history.steps[0].files_referenced).toContain("src/server.ts");
    });
  });

  describe("session-to-epic integration", () => {
    test("registers epic when processing step with beads_task_id", async () => {
      const server = createServer({ beadsSync: false });

      // Register epic for session
      server.registerBeadsEpic("session-1", "epic-main");

      // Process step in that session
      const response = await server.processStep(
        createValidStep({
          session_id: "session-1",
          beads_task_id: "task-123",
        })
      );

      expect(response.isError).toBeUndefined();

      const stats = server.getBeadsStats();
      expect(stats.sessions[0].epic_id).toBe("epic-main");
    });
  });

  describe("end-to-end workflow", () => {
    test("full reasoning chain with Beads fields", async () => {
      const server = createServer({ beadsSync: false });

      // Step 1: Planning
      await server.processStep(
        createValidStep({
          step_number: 1,
          purpose: "planning",
          flow_id: "flow-test",
          beads_task_id: "task-1",
          session_id: "session-1",
        })
      );

      // Step 2: Implementation with patterns
      await server.processStep(
        createValidStep({
          step_number: 2,
          purpose: "implement",
          flow_id: "flow-test",
          beads_task_id: "task-2",
          session_id: "session-1",
          files_referenced: ["src/main.ts"],
          patterns_discovered: ["Singleton pattern used"],
        })
      );

      // Step 3: Validation (final)
      const response = await server.processStep(
        createValidStep({
          step_number: 3,
          purpose: "validation",
          flow_id: "flow-test",
          beads_task_id: "task-3",
          session_id: "session-1",
          is_final_step: true,
        })
      );

      expect(response.isError).toBeUndefined();
      const data = JSON.parse(response.content[0].text);
      expect(data.completed).toBe(true);

      const history = server.getHistory();
      expect(history.steps).toHaveLength(3);
      expect(history.steps[1].patterns_discovered).toContain("Singleton pattern used");
    });

    test("session isolation with Beads epics", async () => {
      const server = createServer({ beadsSync: false });

      // Register different epics for different sessions
      server.registerBeadsEpic("session-a", "epic-a");
      server.registerBeadsEpic("session-b", "epic-b");

      // Process steps in session A
      await server.processStep(
        createValidStep({ session_id: "session-a", step_number: 1 })
      );
      await server.processStep(
        createValidStep({ session_id: "session-a", step_number: 2 })
      );

      // Process steps in session B
      await server.processStep(
        createValidStep({ session_id: "session-b", step_number: 1 })
      );

      // Verify isolation
      const historyA = server.getSessionHistory("session-a");
      const historyB = server.getSessionHistory("session-b");

      expect(historyA?.steps).toHaveLength(2);
      expect(historyB?.steps).toHaveLength(1);

      const stats = server.getBeadsStats();
      expect(stats.sessions).toHaveLength(2);
    });
  });
});
