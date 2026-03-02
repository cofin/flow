/**
 * Flow Think MCP - Formatter Unit Tests
 *
 * Tests for output formatting in console, JSON, and Markdown formats.
 */

import { describe, test, expect } from "bun:test";
import { FlowThinkFormatter } from "../src/formatter.js";
import type { FlowThinkStep, FlowThinkHistory } from "../src/types.js";

function createStep(overrides: Partial<FlowThinkStep> = {}): FlowThinkStep {
  return {
    step_number: 1,
    estimated_total: 3,
    purpose: "planning",
    context: "Starting a new task",
    thought: "I should analyze the requirements first",
    outcome: "Requirements understood",
    next_action: "Read the spec file",
    rationale: "Need to understand what to build",
    timestamp: "2026-01-30T12:00:00.000Z",
    ...overrides,
  };
}

function createHistory(steps: FlowThinkStep[] = []): FlowThinkHistory {
  return {
    steps,
    completed: false,
    created_at: "2026-01-30T12:00:00.000Z",
    updated_at: "2026-01-30T12:00:00.000Z",
    metadata: {
      total_duration_ms: 1000,
      revisions_count: 0,
      branches_created: 0,
      tools_used: [],
    },
  };
}

describe("FlowThinkFormatter", () => {
  describe("formatStepJSON", () => {
    test("formats step as valid JSON", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.formatStepJSON(step);

      const parsed = JSON.parse(output);
      expect(parsed.step_number).toBe(1);
      expect(parsed.purpose).toBe("planning");
    });

    test("includes all step fields", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({ confidence: 0.9, hypothesis: "Test" });
      const output = formatter.formatStepJSON(step);

      const parsed = JSON.parse(output);
      expect(parsed.confidence).toBe(0.9);
      expect(parsed.hypothesis).toBe("Test");
    });
  });

  describe("formatStepMarkdown", () => {
    test("includes header with step number and purpose", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("## Step 1/3: planning");
    });

    test("includes timestamp when present", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("*2026-01-30T12:00:00.000Z*");
    });

    test("includes all content sections", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("**Context:**");
      expect(output).toContain("**Thought:**");
      expect(output).toContain("**Outcome:**");
      expect(output).toContain("**Next Action:**");
      expect(output).toContain("**Rationale:**");
    });

    test("formats structured next_action", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({
        next_action: {
          tool: "Read",
          action: "Read the file",
          expectedOutput: "File contents",
        },
      });
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("- Tool: `Read`");
      expect(output).toContain("- Action: Read the file");
      expect(output).toContain("- Expected: File contents");
    });

    test("includes metadata when present", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({
        confidence: 0.85,
        hypothesis: "The bug is here",
        verification_status: "pending",
        revises_step: 2,
        branch_id: "alt-1",
        branch_name: "Alternative",
      });
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("Confidence: 85%");
      expect(output).toContain("Hypothesis: The bug is here (pending)");
      expect(output).toContain("Revises: Step 2");
      expect(output).toContain("Branch: Alternative");
    });

    test("shows FINAL STEP indicator", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({ is_final_step: true });
      const output = formatter.formatStepMarkdown(step);

      expect(output).toContain("**FINAL STEP**");
    });
  });

  describe("formatStepConsole", () => {
    test("includes step progress without colors", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("STEP 1/3");
      expect(output).toContain("PLANNING");
    });

    test("includes step progress with colors", () => {
      const formatter = new FlowThinkFormatter(true);
      const step = createStep();
      const output = formatter.formatStepConsole(step);

      // Should contain ANSI codes
      expect(output).toContain("\x1b[");
      expect(output).toContain("1/3");
    });

    test("truncates long context", () => {
      const formatter = new FlowThinkFormatter(false);
      const longContext = "A".repeat(300);
      const step = createStep({ context: longContext });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("...");
      expect(output.length).toBeLessThan(longContext.length + 500);
    });

    test("formats structured next_action", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({
        next_action: { tool: "Bash", action: "Run tests" },
      });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("[Bash]");
      expect(output).toContain("Run tests");
    });

    test("shows confidence with color coding", () => {
      const formatter = new FlowThinkFormatter(true);

      const lowConf = createStep({ confidence: 0.3 });
      const lowOutput = formatter.formatStepConsole(lowConf);
      expect(lowOutput).toContain("30%");

      const highConf = createStep({ confidence: 0.9 });
      const highOutput = formatter.formatStepConsole(highConf);
      expect(highOutput).toContain("90%");
    });

    test("shows hypothesis with status", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({
        hypothesis: "The issue is in auth",
        verification_status: "confirmed",
      });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("Hypothesis: The issue is in auth [confirmed]");
    });

    test("shows revision indicator", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({ revises_step: 2 });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("Revises step 2");
    });

    test("shows branch info", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({
        branch_id: "b1",
        branch_name: "Alternative approach",
      });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("Branch: Alternative approach");
    });

    test("shows final step indicator", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep({ is_final_step: true });
      const output = formatter.formatStepConsole(step);

      expect(output).toContain("FINAL STEP");
    });
  });

  describe("format", () => {
    test("dispatches to JSON format", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.format(step, "json");

      expect(() => JSON.parse(output)).not.toThrow();
    });

    test("dispatches to markdown format", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.format(step, "markdown");

      expect(output).toContain("## Step");
    });

    test("dispatches to console format", () => {
      const formatter = new FlowThinkFormatter(false);
      const step = createStep();
      const output = formatter.format(step, "console");

      expect(output).toContain("════════");
    });
  });

  describe("formatHistorySummary", () => {
    test("includes step count", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory([createStep(), createStep({ step_number: 2 })]);
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Steps: 2");
    });

    test("includes completion status", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory();
      history.completed = true;
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Completed: Yes");
    });

    test("includes timestamps", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory();
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Created: 2026-01-30T12:00:00.000Z");
      expect(output).toContain("Updated: 2026-01-30T12:00:00.000Z");
    });

    test("includes duration when present", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory();
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Duration: 1000ms");
    });

    test("includes revisions count when non-zero", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory();
      history.metadata!.revisions_count = 3;
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Revisions: 3");
    });

    test("includes branches count when non-zero", () => {
      const formatter = new FlowThinkFormatter(false);
      const history = createHistory();
      history.metadata!.branches_created = 2;
      const output = formatter.formatHistorySummary(history);

      expect(output).toContain("Branches: 2");
    });
  });
});
