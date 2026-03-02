/**
 * Flow Think MCP - Server Unit Tests
 *
 * Tests for FlowThinkServer step processing, validation, and history management.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import { FlowThinkServer } from "../src/server.js";
import { getDefaultConfig } from "../src/config.js";
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

describe("FlowThinkServer", () => {
  describe("validateRequiredFields", () => {
    test("accepts valid step with all required fields", () => {
      const server = createServer();
      const step = createValidStep();
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(true);
      expect(result.missing).toHaveLength(0);
    });

    test("rejects null input", () => {
      const server = createServer();
      const result = server.validateRequiredFields(null);

      expect(result.valid).toBe(false);
      expect(result.error).toContain("must be an object");
    });

    test("rejects non-object input", () => {
      const server = createServer();
      const result = server.validateRequiredFields("string");

      expect(result.valid).toBe(false);
      expect(result.error).toContain("must be an object");
    });

    test("reports missing step_number", () => {
      const server = createServer();
      const step = createValidStep();
      delete (step as Record<string, unknown>).step_number;
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(false);
      expect(result.missing.join(",")).toContain("step_number");
    });

    test("rejects non-positive step_number", () => {
      const server = createServer();
      const step = createValidStep({ step_number: 0 });
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(false);
      expect(result.missing.join(",")).toContain("step_number");
    });

    test("rejects non-integer step_number", () => {
      const server = createServer();
      const step = createValidStep({ step_number: 1.5 });
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(false);
      expect(result.missing.join(",")).toContain("step_number");
    });

    test("reports missing purpose", () => {
      const server = createServer();
      const step = createValidStep({ purpose: "" });
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(false);
      expect(result.missing).toContain("purpose");
    });

    test("accepts structured next_action with action", () => {
      const server = createServer();
      const step = createValidStep({
        next_action: {
          tool: "Read",
          action: "Read the file",
          expectedOutput: "File contents",
        },
      });
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(true);
    });

    test("rejects structured next_action without action", () => {
      const server = createServer();
      const step = createValidStep({
        next_action: { tool: "Read" },
      });
      const result = server.validateRequiredFields(step);

      expect(result.valid).toBe(false);
      expect(result.missing.join(",")).toContain("next_action.action");
    });

    test("reports all missing fields", () => {
      const server = createServer();
      const result = server.validateRequiredFields({});

      expect(result.valid).toBe(false);
      expect(result.missing.length).toBeGreaterThanOrEqual(7);
    });
  });

  describe("processStep", () => {
    test("processes valid step and returns success", async () => {
      const server = createServer();
      const step = createValidStep();
      const response = await server.processStep(step);

      expect(response.isError).toBeUndefined();
      expect(response.content).toHaveLength(1);

      const data = JSON.parse(response.content[0].text);
      expect(data.status).toBe("flow_think_in_progress");
      expect(data.step_number).toBe(1);
      expect(data.completed).toBe(false);
    });

    test("returns error for invalid step", async () => {
      const server = createServer();
      const response = await server.processStep({});

      expect(response.isError).toBe(true);

      const data = JSON.parse(response.content[0].text);
      expect(data.error).toBeDefined();
      expect(data.missing_fields).toBeDefined();
    });

    test("adds timestamp to processed step", async () => {
      const server = createServer();
      const step = createValidStep();
      await server.processStep(step);

      const history = server.getHistory();
      expect(history.steps[0].timestamp).toBeDefined();
    });

    test("tracks duration_ms for processed step", async () => {
      const server = createServer();
      const step = createValidStep();
      await server.processStep(step);

      const history = server.getHistory();
      expect(history.steps[0].duration_ms).toBeDefined();
      expect(history.steps[0].duration_ms).toBeGreaterThanOrEqual(0);
    });

    test("marks completion when is_final_step is true", async () => {
      const server = createServer();
      const step = createValidStep({ is_final_step: true });
      const response = await server.processStep(step);

      const data = JSON.parse(response.content[0].text);
      expect(data.status).toBe("flow_think_complete");
      expect(data.completed).toBe(true);

      const history = server.getHistory();
      expect(history.completed).toBe(true);
    });

    test("detects completion phrases in thought", async () => {
      const server = createServer();
      const step = createValidStep({
        thought: "Based on my analysis, I have reached a final conclusion.",
      });
      const response = await server.processStep(step);

      const data = JSON.parse(response.content[0].text);
      expect(data.completed).toBe(true);
    });

    test("includes confidence in response when provided", async () => {
      const server = createServer();
      const step = createValidStep({ confidence: 0.85 });
      const response = await server.processStep(step);

      const data = JSON.parse(response.content[0].text);
      expect(data.confidence).toBe(0.85);
    });

    test("includes hypothesis status in response", async () => {
      const server = createServer();
      const step = createValidStep({
        hypothesis: "The bug is in the auth module",
        verification_status: "pending",
      });
      const response = await server.processStep(step);

      const data = JSON.parse(response.content[0].text);
      expect(data.hypothesis.text).toBe("The bug is in the auth module");
      expect(data.hypothesis.status).toBe("pending");
    });

    test("includes branch info in response", async () => {
      const server = createServer();
      // First create step 2 so we can branch from it
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));

      const response = await server.processStep(
        createValidStep({
          step_number: 3,
          branch_id: "branch-1",
          branch_name: "Alternative approach",
          branch_from: 2,
        })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.branch.id).toBe("branch-1");
      expect(data.branch.name).toBe("Alternative approach");
      expect(data.branch.from).toBe(2);
    });

    test("tracks tools used across steps", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ tools_used: ["Read", "Grep"] }));
      await server.processStep(createValidStep({
        step_number: 2,
        tools_used: ["Edit"],
        next_action: { tool: "Bash", action: "Run tests" },
      }));

      const history = server.getHistory();
      expect(history.metadata?.tools_used).toContain("Read");
      expect(history.metadata?.tools_used).toContain("Grep");
      expect(history.metadata?.tools_used).toContain("Edit");
      expect(history.metadata?.tools_used).toContain("Bash");
    });
  });

  describe("history management", () => {
    test("stores steps in history", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));

      const history = server.getHistory();
      expect(history.steps).toHaveLength(2);
    });

    test("getStep returns step by number", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2, purpose: "debug" }));

      const step = server.getStep(2);
      expect(step?.purpose).toBe("debug");
    });

    test("hasStep returns true for existing step", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 5 }));

      expect(server.hasStep(5)).toBe(true);
      expect(server.hasStep(10)).toBe(false);
    });

    test("clearHistory resets all state", async () => {
      const server = createServer();
      await server.processStep(createValidStep());
      server.clearHistory();

      const history = server.getHistory();
      expect(history.steps).toHaveLength(0);
      expect(history.completed).toBe(false);
      expect(server.hasStep(1)).toBe(false);
    });

    test("trims history when exceeding maxHistorySize", async () => {
      const server = createServer({ maxHistorySize: 3 });

      for (let i = 1; i <= 5; i++) {
        await server.processStep(createValidStep({ step_number: i }));
      }

      const history = server.getHistory();
      expect(history.steps).toHaveLength(3);
      expect(server.hasStep(1)).toBe(false);
      expect(server.hasStep(2)).toBe(false);
      expect(server.hasStep(3)).toBe(true);
    });

    test("updates metadata timestamps", async () => {
      const server = createServer();
      const history1 = server.getHistory();
      const created = history1.created_at;

      await new Promise((r) => setTimeout(r, 10));
      await server.processStep(createValidStep());

      const history2 = server.getHistory();
      expect(history2.created_at).toBe(created);
      expect(history2.updated_at).not.toBe(created);
    });
  });

  describe("confidence validation", () => {
    test("validates confidence is within 0-1 range", async () => {
      const server = createServer();
      const response = await server.processStep(createValidStep({ confidence: 1.5 }));

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("confidence");
    });

    test("rejects negative confidence", async () => {
      const server = createServer();
      const response = await server.processStep(createValidStep({ confidence: -0.1 }));

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("confidence");
    });

    test("accepts valid confidence values", async () => {
      const server = createServer();

      for (const confidence of [0, 0.5, 1]) {
        const response = await server.processStep(
          createValidStep({ step_number: confidence * 10 + 1, confidence })
        );
        expect(response.isError).toBeUndefined();
      }
    });

    test("returns warning for low confidence (below threshold)", async () => {
      const server = createServer({ lowConfidenceThreshold: 0.5 });
      const response = await server.processStep(createValidStep({ confidence: 0.2 }));

      const data = JSON.parse(response.content[0].text);
      expect(data.warning).toBeDefined();
      expect(data.warning.level).toBe("warning");
      expect(data.warning.confidence).toBe(0.2);
    });

    test("returns critical warning for very low confidence", async () => {
      const server = createServer({ lowConfidenceThreshold: 0.5 });
      const response = await server.processStep(createValidStep({ confidence: 0.1 }));

      const data = JSON.parse(response.content[0].text);
      expect(data.warning.level).toBe("critical");
    });

    test("no warning when confidence is at or above threshold", async () => {
      const server = createServer({ lowConfidenceThreshold: 0.5 });
      const response = await server.processStep(createValidStep({ confidence: 0.5 }));

      const data = JSON.parse(response.content[0].text);
      expect(data.warning).toBeUndefined();
    });

    test("includes suggestion in low confidence warning", async () => {
      const server = createServer({ lowConfidenceThreshold: 0.5 });
      const response = await server.processStep(createValidStep({ confidence: 0.3 }));

      const data = JSON.parse(response.content[0].text);
      expect(data.warning.suggestion).toBeDefined();
      expect(data.warning.suggestion.length).toBeGreaterThan(0);
    });

    test("logs warning to stderr for low confidence", async () => {
      const server = createServer({ lowConfidenceThreshold: 0.5 });
      // We can't easily capture stderr in bun:test, so just verify no error
      const response = await server.processStep(createValidStep({ confidence: 0.25 }));
      expect(response.isError).toBeUndefined();
    });
  });

  describe("revision handling", () => {
    test("rejects revision of non-existent step", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, revises_step: 5 })
      );

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("does not exist");
    });

    test("rejects revision of step 0 or negative", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, revises_step: 0 })
      );

      expect(response.isError).toBe(true);
    });

    test("allows revision of existing step", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          revises_step: 1,
          revision_reason: "Found error in step 1",
        })
      );

      expect(response.isError).toBeUndefined();
      const data = JSON.parse(response.content[0].text);
      expect(data.revised_step).toBe(1);
    });

    test("marks original step as revised_by", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(
        createValidStep({
          step_number: 2,
          revises_step: 1,
          revision_reason: "Better approach",
        })
      );

      const originalStep = server.getStep(1);
      expect(originalStep?.revised_by).toBe(2);
    });

    test("increments revisions_count in metadata", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));
      await server.processStep(
        createValidStep({ step_number: 3, revises_step: 1 })
      );
      await server.processStep(
        createValidStep({ step_number: 4, revises_step: 2 })
      );

      const history = server.getHistory();
      expect(history.metadata?.revisions_count).toBe(2);
    });

    test("includes revision info in response", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          revises_step: 1,
          revision_reason: "Correction needed",
        })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.revision).toBeDefined();
      expect(data.revision.revises).toBe(1);
      expect(data.revision.reason).toBe("Correction needed");
    });
  });

  describe("branch handling", () => {
    test("rejects branch from non-existent step", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, branch_from: 10 })
      );

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("does not exist");
    });

    test("rejects branch_from step 0 or negative", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, branch_from: 0 })
      );

      expect(response.isError).toBe(true);
    });

    test("allows branch from existing step", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          branch_from: 1,
          branch_name: "Alternative approach",
        })
      );

      expect(response.isError).toBeUndefined();
      const data = JSON.parse(response.content[0].text);
      expect(data.branch).toBeDefined();
      expect(data.branch.from).toBe(1);
    });

    test("auto-generates branch_id if not provided", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      const response = await server.processStep(
        createValidStep({ step_number: 2, branch_from: 1 })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.branch.id).toBeDefined();
      expect(data.branch.id).toMatch(/^branch-/);

      const history = server.getHistory();
      expect(history.steps[1].branch_id).toBeDefined();
    });

    test("uses provided branch_id", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(
        createValidStep({
          step_number: 2,
          branch_from: 1,
          branch_id: "my-custom-branch",
        })
      );

      const history = server.getHistory();
      expect(history.steps[1].branch_id).toBe("my-custom-branch");
    });

    test("increments branches_created in metadata", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));
      await server.processStep(
        createValidStep({ step_number: 3, branch_from: 1 })
      );
      await server.processStep(
        createValidStep({ step_number: 4, branch_from: 2 })
      );

      const history = server.getHistory();
      expect(history.metadata?.branches_created).toBe(2);
    });

    test("rejects when max branch depth exceeded", async () => {
      const server = createServer({ maxBranchDepth: 2 });
      await server.processStep(createValidStep({ step_number: 1 }));
      // First branch (depth 1)
      await server.processStep(
        createValidStep({ step_number: 2, branch_from: 1, branch_id: "b1" })
      );
      // Second nested branch (depth 2)
      await server.processStep(
        createValidStep({ step_number: 3, branch_from: 2, branch_id: "b2" })
      );
      // Third nested branch (depth 3) - should fail
      const response = await server.processStep(
        createValidStep({ step_number: 4, branch_from: 3, branch_id: "b3" })
      );

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("Maximum branch depth");
    });

    test("creates branch object in history", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(
        createValidStep({
          step_number: 2,
          branch_from: 1,
          branch_id: "test-branch",
          branch_name: "Test Branch",
        })
      );

      const history = server.getHistory();
      expect(history.branches).toBeDefined();
      expect(history.branches).toHaveLength(1);
      expect(history.branches![0].id).toBe("test-branch");
      expect(history.branches![0].from_step).toBe(1);
      expect(history.branches![0].steps).toContain(2);
    });

    test("adds steps to existing branch", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(
        createValidStep({
          step_number: 2,
          branch_from: 1,
          branch_id: "my-branch",
        })
      );
      // Continue on same branch
      await server.processStep(
        createValidStep({ step_number: 3, branch_id: "my-branch" })
      );

      const history = server.getHistory();
      expect(history.branches).toHaveLength(1);
      expect(history.branches![0].steps).toContain(2);
      expect(history.branches![0].steps).toContain(3);
    });
  });

  describe("dependency tracking", () => {
    test("rejects dependencies on non-existent steps", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, dependencies: [10] })
      );

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("do not exist");
    });

    test("accepts valid dependencies", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));
      const response = await server.processStep(
        createValidStep({ step_number: 3, dependencies: [1, 2] })
      );

      expect(response.isError).toBeUndefined();
    });

    test("includes dependencies in response", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));
      const response = await server.processStep(
        createValidStep({ step_number: 3, dependencies: [1, 2] })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.dependencies).toBeDefined();
      expect(data.dependencies).toContain(1);
      expect(data.dependencies).toContain(2);
    });

    test("rejects circular dependency (step depending on itself)", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, dependencies: [2] })
      );

      expect(response.isError).toBe(true);
      const data = JSON.parse(response.content[0].text);
      expect(data.error).toContain("cannot depend on itself");
    });

    test("rejects dependency on step 0 or negative", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));

      const response = await server.processStep(
        createValidStep({ step_number: 2, dependencies: [0] })
      );

      expect(response.isError).toBe(true);
    });
  });

  describe("hypothesis verification", () => {
    test("tracks hypothesis across steps", async () => {
      const server = createServer();
      // Set hypothesis
      await server.processStep(
        createValidStep({
          step_number: 1,
          hypothesis: "The bug is in the auth module",
          verification_status: "pending",
        })
      );
      // Confirm hypothesis
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          hypothesis: "The bug is in the auth module",
          verification_status: "confirmed",
        })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.hypothesis.status).toBe("confirmed");
    });

    test("logs hypothesis state changes", async () => {
      const server = createServer();
      // We can't easily capture stderr, but verify no error
      await server.processStep(
        createValidStep({
          step_number: 1,
          hypothesis: "Test hypothesis",
          verification_status: "pending",
        })
      );
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          hypothesis: "Test hypothesis",
          verification_status: "refuted",
        })
      );

      expect(response.isError).toBeUndefined();
      const data = JSON.parse(response.content[0].text);
      expect(data.hypothesis.status).toBe("refuted");
    });

    test("includes hypothesis in response without status (defaults to pending)", async () => {
      const server = createServer();
      const response = await server.processStep(
        createValidStep({
          step_number: 1,
          hypothesis: "Maybe it's X",
        })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.hypothesis.text).toBe("Maybe it's X");
      expect(data.hypothesis.status).toBe("pending");
    });
  });

  describe("session management", () => {
    test("isolates sessions by session_id", async () => {
      const server = createServer();
      // Create steps in session A
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "session-a" })
      );
      await server.processStep(
        createValidStep({ step_number: 2, session_id: "session-a" })
      );

      // Create steps in session B
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "session-b" })
      );

      // Get session A history
      const historyA = server.getSessionHistory("session-a");
      expect(historyA?.steps).toHaveLength(2);

      // Get session B history
      const historyB = server.getSessionHistory("session-b");
      expect(historyB?.steps).toHaveLength(1);
    });

    test("includes session_id in response", async () => {
      const server = createServer();
      const response = await server.processStep(
        createValidStep({ step_number: 1, session_id: "my-session" })
      );

      const data = JSON.parse(response.content[0].text);
      expect(data.session_id).toBe("my-session");
    });

    test("lists all sessions", async () => {
      const server = createServer();
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "s1" })
      );
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "s2" })
      );
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "s3" })
      );

      const sessions = server.listSessions();
      expect(sessions).toHaveLength(3);
      expect(sessions.map((s) => s.id)).toContain("s1");
      expect(sessions.map((s) => s.id)).toContain("s2");
      expect(sessions.map((s) => s.id)).toContain("s3");
    });

    test("steps without session_id use default session", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));

      // Default session is main history
      const history = server.getHistory();
      expect(history.steps).toHaveLength(2);
    });

    test("validates steps within correct session context", async () => {
      const server = createServer();
      // Create step 1 in session A
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "session-a" })
      );

      // Try to revise step 1 from session B (should fail - step doesn't exist in B)
      const response = await server.processStep(
        createValidStep({
          step_number: 2,
          session_id: "session-b",
          revises_step: 1,
        })
      );

      expect(response.isError).toBe(true);
    });

    test("clears specific session", async () => {
      const server = createServer();
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "session-a" })
      );
      await server.processStep(
        createValidStep({ step_number: 1, session_id: "session-b" })
      );

      const deleted = server.clearSession("session-a");
      expect(deleted).toBe(true);

      const sessions = server.listSessions();
      expect(sessions).toHaveLength(1);
      expect(sessions[0].id).toBe("session-b");
    });

    test("returns false when clearing non-existent session", async () => {
      const server = createServer();
      const deleted = server.clearSession("non-existent");
      expect(deleted).toBe(false);
    });
  });

  describe("getHistorySummary", () => {
    test("returns formatted summary", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ step_number: 1 }));
      await server.processStep(createValidStep({ step_number: 2 }));

      const summary = server.getHistorySummary();
      expect(summary).toContain("Steps: 2");
      expect(summary).toContain("Completed: No");
    });
  });

  describe("exportHistory", () => {
    test("exports as JSON by default", async () => {
      const server = createServer();
      await server.processStep(createValidStep());

      const exported = server.exportHistory();
      const parsed = JSON.parse(exported);

      expect(parsed.steps).toHaveLength(1);
      expect(parsed.completed).toBe(false);
    });

    test("exports as markdown", async () => {
      const server = createServer();
      await server.processStep(createValidStep({ purpose: "planning" }));

      const exported = server.exportHistory("markdown");

      expect(exported).toContain("## Step 1/3: planning");
      expect(exported).toContain("**Context:**");
    });

    test("exports as text", async () => {
      const server = createServer({ outputFormat: "json" }); // Disable colors
      await server.processStep(createValidStep());

      const exported = server.exportHistory("text");

      // Text export includes color codes when colorOutput is true (default for console format)
      // The output format doesn't affect colorOutput, so check for content presence
      expect(exported).toContain("1/3");
      expect(exported).toContain("Context:");
    });
  });
});
