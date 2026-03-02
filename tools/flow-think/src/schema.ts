/**
 * Flow Think MCP - Tool Schema Definition
 *
 * Defines the MCP tool schema for the flow_think structured reasoning tool.
 */

import type { Tool } from "@modelcontextprotocol/sdk/types.js";

/**
 * Tool description shown to LLMs.
 * Explains when and how to use the flow_think tool.
 */
const TOOL_DESCRIPTION = `Record a structured reasoning step for complex problem-solving.

Use this tool to break down multi-step problems into trackable reasoning steps.
Each step captures your current thinking, expected outcome, and planned next action.

WHEN TO USE:
- Multi-step analysis, debugging, or planning tasks
- Tasks requiring systematic exploration of options
- Problems where you need to track progress or revise earlier thinking
- Complex workflows requiring hypothesis testing

WORKFLOW:
1. Start with step_number=1, estimate your total steps
2. Describe your thought process, expected outcome, and next action
3. Continue calling for each reasoning step, adjusting estimated_total as needed
4. Set is_final_step=true when reasoning is complete

PURPOSE TYPES:
- planning: Breaking down tasks, outlining approach
- research: Gathering information, investigating
- implement: Writing code, making changes (TDD)
- debug: Troubleshooting errors, root cause analysis
- analysis: Examining code/architecture
- validation: Verifying hypothesis or implementation
- decision: Choosing between options
- exploration: Trying different approaches
- reflection: Reviewing progress, extracting patterns

Returns JSON summary with step count, completion status, and next action.`;

/**
 * The flow_think tool schema for MCP.
 */
export const FLOW_THINK_TOOL: Tool = {
  name: "flow_think",
  description: TOOL_DESCRIPTION,
  inputSchema: {
    type: "object",
    properties: {
      // ─────────────────────────────────────────────────────────────
      // Required fields
      // ─────────────────────────────────────────────────────────────
      step_number: {
        type: "integer",
        description: "Sequential step number starting from 1. Increment for each new reasoning step.",
        minimum: 1,
      },
      estimated_total: {
        type: "integer",
        description:
          "Current estimate of total steps needed. Adjust as you learn more about the problem.",
        minimum: 1,
      },
      purpose: {
        type: "string",
        description:
          "Category of this reasoning step. Standard: planning, research, implement, debug, analysis, validation, decision, exploration, reflection. Custom strings allowed.",
      },
      context: {
        type: "string",
        description:
          "What is already known or has been completed. Include relevant findings from previous steps.",
      },
      thought: {
        type: "string",
        description: "Your current reasoning process. Describe what you are thinking and why.",
      },
      outcome: {
        type: "string",
        description:
          "The expected or actual result from this step. What did you learn or accomplish?",
      },
      next_action: {
        oneOf: [
          {
            type: "string",
            description: "Simple description of your next action",
          },
          {
            type: "object",
            description: "Structured action with tool details",
            properties: {
              tool: { type: "string", description: "Name of tool to use" },
              action: { type: "string", description: "Specific action to perform" },
              parameters: { type: "object", description: "Parameters to pass to the tool" },
              expectedOutput: { type: "string", description: "What you expect this action to return" },
            },
            required: ["action"],
          },
        ],
        description: "What you will do next. Can be a simple string or structured object.",
      },
      rationale: {
        type: "string",
        description: "Why you chose this next action. Explain your reasoning for the approach.",
      },

      // ─────────────────────────────────────────────────────────────
      // Completion
      // ─────────────────────────────────────────────────────────────
      is_final_step: {
        type: "boolean",
        description:
          "Set to true to explicitly mark this as the final reasoning step. The chain will be marked complete.",
      },

      // ─────────────────────────────────────────────────────────────
      // Confidence tracking (Chapter 2)
      // ─────────────────────────────────────────────────────────────
      confidence: {
        type: "number",
        description:
          "Your confidence in this step (0-1 scale). Lower values trigger warnings: 0.3=low, 0.5=moderate, 0.8+=high.",
        minimum: 0,
        maximum: 1,
      },
      uncertainty_notes: {
        type: "string",
        description:
          "Describe specific uncertainties or doubts. What assumptions are you making?",
      },

      // ─────────────────────────────────────────────────────────────
      // Revision support (Chapter 2)
      // ─────────────────────────────────────────────────────────────
      revises_step: {
        type: "integer",
        description:
          "Step number you are revising or correcting. The original will be marked as revised.",
        minimum: 1,
      },
      revision_reason: {
        type: "string",
        description: "Why you are revising the earlier step. What was wrong or incomplete?",
      },

      // ─────────────────────────────────────────────────────────────
      // Branching support (Chapter 2)
      // ─────────────────────────────────────────────────────────────
      branch_from: {
        type: "integer",
        description:
          "Step number to branch from for exploring an alternative approach. Creates a new path.",
        minimum: 1,
      },
      branch_id: {
        type: "string",
        description: "Unique identifier for this branch. Auto-generated if not provided.",
      },
      branch_name: {
        type: "string",
        description: 'Human-readable name for this branch (e.g., "Alternative A: Use caching")',
      },

      // ─────────────────────────────────────────────────────────────
      // Hypothesis verification (Chapter 2)
      // ─────────────────────────────────────────────────────────────
      hypothesis: {
        type: "string",
        description: "Current hypothesis being tested. State your theory clearly.",
      },
      verification_status: {
        type: "string",
        enum: ["pending", "confirmed", "refuted"],
        description: "Status of hypothesis verification.",
      },

      // ─────────────────────────────────────────────────────────────
      // Tool integration
      // ─────────────────────────────────────────────────────────────
      tools_used: {
        type: "array",
        items: { type: "string" },
        description: "List of tools you used during this step for tracking purposes.",
      },
      external_context: {
        type: "object",
        description: "External data or tool outputs relevant to this step.",
      },
      dependencies: {
        type: "array",
        items: { type: "integer" },
        description: "Step numbers this step depends on. Validated against existing steps.",
      },

      // ─────────────────────────────────────────────────────────────
      // Session support
      // ─────────────────────────────────────────────────────────────
      session_id: {
        type: "string",
        description:
          "Session identifier for grouping related reasoning chains. Sessions expire after timeout.",
      },

      // ─────────────────────────────────────────────────────────────
      // Flow-specific (Chapter 3)
      // ─────────────────────────────────────────────────────────────
      flow_id: {
        type: "string",
        description: "Current Flow context (flow_id from .agent/specs/).",
      },
      beads_task_id: {
        type: "string",
        description: "Linked Beads task ID for sync.",
      },
      files_referenced: {
        type: "array",
        items: { type: "string" },
        description: "Files examined during this step (absolute paths).",
      },
      patterns_discovered: {
        type: "array",
        items: { type: "string" },
        description: "Patterns discovered for learnings capture.",
      },
    },
    required: [
      "step_number",
      "estimated_total",
      "purpose",
      "context",
      "thought",
      "outcome",
      "next_action",
      "rationale",
    ],
  },
};
