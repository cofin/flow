/**
 * Flow Think MCP - Integration Tests
 *
 * Tests the full MCP workflow including tool registration and step processing.
 */

import { describe, test, expect } from "bun:test";
import { FLOW_THINK_TOOL } from "../src/schema.js";
import { FlowThinkServer } from "../src/server.js";
import { getDefaultConfig } from "../src/config.js";

describe("MCP Integration", () => {
  describe("Tool Schema", () => {
    test("tool has correct name", () => {
      expect(FLOW_THINK_TOOL.name).toBe("flow_think");
    });

    test("tool has description", () => {
      expect(FLOW_THINK_TOOL.description).toBeDefined();
      expect(FLOW_THINK_TOOL.description.length).toBeGreaterThan(100);
    });

    test("schema defines required fields", () => {
      const schema = FLOW_THINK_TOOL.inputSchema as {
        required: string[];
        properties: Record<string, unknown>;
      };

      expect(schema.required).toContain("step_number");
      expect(schema.required).toContain("estimated_total");
      expect(schema.required).toContain("purpose");
      expect(schema.required).toContain("context");
      expect(schema.required).toContain("thought");
      expect(schema.required).toContain("outcome");
      expect(schema.required).toContain("next_action");
      expect(schema.required).toContain("rationale");
    });

    test("schema defines optional fields", () => {
      const schema = FLOW_THINK_TOOL.inputSchema as {
        properties: Record<string, unknown>;
      };

      expect(schema.properties.confidence).toBeDefined();
      expect(schema.properties.hypothesis).toBeDefined();
      expect(schema.properties.revises_step).toBeDefined();
      expect(schema.properties.branch_id).toBeDefined();
      expect(schema.properties.is_final_step).toBeDefined();
      expect(schema.properties.tools_used).toBeDefined();
      expect(schema.properties.beads_task_id).toBeDefined();
    });
  });

  describe("End-to-End Workflow", () => {
    test("completes a multi-step reasoning chain", async () => {
      const server = new FlowThinkServer(getDefaultConfig());

      // Step 1: Planning
      const step1 = await server.processStep({
        step_number: 1,
        estimated_total: 3,
        purpose: "planning",
        context: "User wants to add a new feature",
        thought: "I should first understand the requirements",
        outcome: "Need to read the spec file",
        next_action: { tool: "Read", action: "Read spec.md" },
        rationale: "Understanding requirements before implementation",
      });

      expect(step1.isError).toBeUndefined();
      const data1 = JSON.parse(step1.content[0].text);
      expect(data1.status).toBe("flow_think_in_progress");
      expect(data1.step_number).toBe(1);

      // Step 2: Research
      const step2 = await server.processStep({
        step_number: 2,
        estimated_total: 3,
        purpose: "research",
        context: "Read the spec file",
        thought: "The feature requires modifying the auth module",
        outcome: "Identified files to change",
        next_action: "Implement the changes",
        rationale: "Ready to implement with clear understanding",
        confidence: 0.85,
      });

      const data2 = JSON.parse(step2.content[0].text);
      expect(data2.step_number).toBe(2);
      expect(data2.confidence).toBe(0.85);

      // Step 3: Final
      const step3 = await server.processStep({
        step_number: 3,
        estimated_total: 3,
        purpose: "implement",
        context: "Implemented the feature",
        thought: "All changes made and tests passing",
        outcome: "Feature complete",
        next_action: "Commit changes",
        rationale: "Implementation verified",
        is_final_step: true,
      });

      const data3 = JSON.parse(step3.content[0].text);
      expect(data3.status).toBe("flow_think_complete");
      expect(data3.completed).toBe(true);

      // Verify history
      const history = server.getHistory();
      expect(history.steps).toHaveLength(3);
      expect(history.completed).toBe(true);
    });

    test("handles revision workflow", async () => {
      const server = new FlowThinkServer(getDefaultConfig());

      // Initial step
      await server.processStep({
        step_number: 1,
        estimated_total: 2,
        purpose: "analysis",
        context: "Starting investigation",
        thought: "I think the bug is in module A",
        outcome: "Will check module A",
        next_action: "Read module A",
        rationale: "Initial hypothesis",
        hypothesis: "Bug is in module A",
        verification_status: "pending",
      });

      // Revision step
      const revision = await server.processStep({
        step_number: 2,
        estimated_total: 2,
        purpose: "analysis",
        context: "Checked module A, no bug found",
        thought: "My initial hypothesis was wrong, checking module B",
        outcome: "Bug is actually in module B",
        next_action: "Fix module B",
        rationale: "Correcting earlier assessment",
        revises_step: 1,
        revision_reason: "Module A was clean, found real bug in module B",
        hypothesis: "Bug is in module B",
        verification_status: "confirmed",
        is_final_step: true,
      });

      const data = JSON.parse(revision.content[0].text);
      expect(data.revised_step).toBe(1);
      expect(data.hypothesis.status).toBe("confirmed");
    });

    test("handles branching workflow", async () => {
      const server = new FlowThinkServer(getDefaultConfig());

      // Base step
      await server.processStep({
        step_number: 1,
        estimated_total: 3,
        purpose: "decision",
        context: "Deciding implementation approach",
        thought: "Could use approach A or B",
        outcome: "Will explore approach A first",
        next_action: "Try approach A",
        rationale: "A seems simpler",
      });

      // Branch to try alternative
      const branch = await server.processStep({
        step_number: 2,
        estimated_total: 3,
        purpose: "exploration",
        context: "Exploring alternative",
        thought: "Trying approach B for comparison",
        outcome: "Approach B results",
        next_action: "Compare results",
        rationale: "Need to evaluate both options",
        branch_from: 1,
        branch_id: "alt-approach",
        branch_name: "Alternative: Approach B",
      });

      const data = JSON.parse(branch.content[0].text);
      expect(data.branch.id).toBe("alt-approach");
      expect(data.branch.name).toBe("Alternative: Approach B");
      expect(data.branch.from).toBe(1);
    });

    test("tracks tools across steps", async () => {
      const server = new FlowThinkServer(getDefaultConfig());

      await server.processStep({
        step_number: 1,
        estimated_total: 2,
        purpose: "research",
        context: "Starting",
        thought: "Thinking",
        outcome: "Done",
        next_action: "Continue",
        rationale: "Why",
        tools_used: ["Glob", "Read"],
      });

      await server.processStep({
        step_number: 2,
        estimated_total: 2,
        purpose: "implement",
        context: "Implementing",
        thought: "Writing code",
        outcome: "Code written",
        next_action: { tool: "Bash", action: "Run tests" },
        rationale: "Verify changes",
        tools_used: ["Edit"],
        is_final_step: true,
      });

      const history = server.getHistory();
      const tools = history.metadata?.tools_used ?? [];

      expect(tools).toContain("Glob");
      expect(tools).toContain("Read");
      expect(tools).toContain("Edit");
      expect(tools).toContain("Bash");
    });

    test("handles error gracefully", async () => {
      const server = new FlowThinkServer(getDefaultConfig());

      const result = await server.processStep({
        step_number: 1,
        // Missing required fields
      });

      expect(result.isError).toBe(true);
      const data = JSON.parse(result.content[0].text);
      expect(data.error).toBeDefined();
      expect(data.missing_fields).toBeDefined();
      expect(data.missing_fields.length).toBeGreaterThan(0);
    });
  });

  describe("Configuration Integration", () => {
    test("respects maxHistorySize config", async () => {
      const server = new FlowThinkServer({
        ...getDefaultConfig(),
        maxHistorySize: 2,
      });

      for (let i = 1; i <= 5; i++) {
        await server.processStep({
          step_number: i,
          estimated_total: 5,
          purpose: "test",
          context: `Step ${i}`,
          thought: "Thinking",
          outcome: "Done",
          next_action: "Next",
          rationale: "Reason",
        });
      }

      const history = server.getHistory();
      expect(history.steps).toHaveLength(2);
      expect(history.steps[0].step_number).toBe(4);
      expect(history.steps[1].step_number).toBe(5);
    });

    test("respects outputFormat config", async () => {
      const jsonServer = new FlowThinkServer({
        ...getDefaultConfig(),
        outputFormat: "json",
      });

      const markdownServer = new FlowThinkServer({
        ...getDefaultConfig(),
        outputFormat: "markdown",
      });

      // Both should process steps the same way
      const step = {
        step_number: 1,
        estimated_total: 1,
        purpose: "test",
        context: "Test",
        thought: "Test",
        outcome: "Test",
        next_action: "Done",
        rationale: "Test",
        is_final_step: true,
      };

      const jsonResult = await jsonServer.processStep(step);
      const mdResult = await markdownServer.processStep({ ...step });

      // Response format should be the same (JSON)
      expect(() => JSON.parse(jsonResult.content[0].text)).not.toThrow();
      expect(() => JSON.parse(mdResult.content[0].text)).not.toThrow();
    });
  });
});
