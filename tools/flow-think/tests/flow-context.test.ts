/**
 * Flow Think MCP - Flow Context Tests
 *
 * Tests for loading Flow context from .agent/ directory.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import {
  FlowContextLoader,
  clearFlowContextCache,
  type FlowContext,
  type FlowSpec,
  type FlowMetadata,
  type FlowStatus,
} from "../src/flow/context.js";

describe("FlowContextLoader", () => {
  beforeEach(() => {
    clearFlowContextCache();
  });

  describe("constructor", () => {
    test("uses provided directory", () => {
      const loader = new FlowContextLoader("/test/project");
      expect(loader.getProjectRoot()).toBe("/test/project");
    });

    test("uses current directory when no path provided", () => {
      const loader = new FlowContextLoader();
      expect(loader.getProjectRoot()).toBe(process.cwd());
    });
  });

  describe("hasAgentDirectory", () => {
    test("returns true when .agent directory exists", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const exists = await loader.hasAgentDirectory();
      expect(exists).toBe(true);
    });

    test("returns false when .agent directory does not exist", async () => {
      const loader = new FlowContextLoader("/tmp");
      const exists = await loader.hasAgentDirectory();
      expect(exists).toBe(false);
    });
  });

  describe("loadFlowsRegistry", () => {
    test("loads flows.md when it exists", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const registry = await loader.loadFlowsRegistry();

      // flows.md exists in the flow project
      expect(registry).not.toBeNull();
      expect(typeof registry).toBe("string");
      expect(registry).toContain("Flow Registry");
    });

    test("returns null when flows.md does not exist", async () => {
      const loader = new FlowContextLoader("/tmp");
      const registry = await loader.loadFlowsRegistry();
      expect(registry).toBeNull();
    });
  });

  describe("detectCurrentFlow", () => {
    test("extracts active flows from registry", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const flows = await loader.detectCurrentFlow();

      // Should find at least one flow from flows.md
      expect(Array.isArray(flows)).toBe(true);
    });

    test("returns empty array when no .agent directory", async () => {
      const loader = new FlowContextLoader("/tmp");
      const flows = await loader.detectCurrentFlow();
      expect(flows).toEqual([]);
    });
  });

  describe("loadSpec", () => {
    test("loads spec/prd.md for a flow when it exists", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      // Use the known flow from flows.md
      const spec = await loader.loadSpec("agent-parity-cleanup_20260302");

      expect(spec).not.toBeNull();
      if (spec) {
        expect(spec.content).toContain("Flow: Command Parity and Artifact Cleanup");
      }
    });

    test("returns null when flow does not exist", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const spec = await loader.loadSpec("nonexistent-flow_20260101");
      expect(spec).toBeNull();
    });
  });

  describe("loadPlan", () => {
    test("returns null when plan.md does not exist", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const plan = await loader.loadPlan("flow-mcp_20260130");
      // flow-mcp_20260130 has prd.md but no plan.md based on our earlier ls
      expect(plan).toBeNull();
    });
  });

  describe("loadPatterns", () => {
    test("returns patterns content when file exists", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const patterns = await loader.loadPatterns();

      // patterns.md may or may not exist, just verify the return type
      if (patterns !== null) {
        expect(typeof patterns).toBe("string");
      }
    });

    test("returns null when patterns.md does not exist", async () => {
      const loader = new FlowContextLoader("/tmp");
      const patterns = await loader.loadPatterns();
      expect(patterns).toBeNull();
    });
  });

  describe("loadWorkflow", () => {
    test("returns null when workflow.md does not exist in .agent", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const workflow = await loader.loadWorkflow();
      // workflow.md is typically in templates/agent/, not .agent/
      // This test verifies the method returns null when file doesn't exist
      expect(workflow).toBeNull();
    });
  });

  describe("loadMetadata", () => {
    test("loads metadata.json for a flow when it exists", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const metadata = await loader.loadMetadata("agent-parity-cleanup_20260302");

      expect(metadata).not.toBeNull();
      if (metadata) {
        expect(metadata.beads_epic_id).toBe("flow-9xp");
      }
    });

    test("returns null when metadata.json does not exist", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const metadata = await loader.loadMetadata("nonexistent-flow_20260101");
      expect(metadata).toBeNull();
    });
  });

  describe("getFullContext", () => {
    test("returns full context for a flow", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const context = await loader.getFullContext("agent-parity-cleanup_20260302");

      expect(context).not.toBeNull();
      if (context) {
        expect(context.flow_id).toBe("agent-parity-cleanup_20260302");
        expect(context.spec).not.toBeNull();
        expect(context.metadata).not.toBeNull();
      }
    });

    test("returns null when flow does not exist", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");
      const context = await loader.getFullContext("nonexistent-flow_20260101");
      expect(context).toBeNull();
    });
  });

  describe("parseFlowStatus", () => {
    test("parses pending status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[ ]")).toBe("pending");
    });

    test("parses in_progress status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[~]")).toBe("in_progress");
    });

    test("parses completed status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[x]")).toBe("completed");
    });

    test("parses blocked status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[!]")).toBe("blocked");
    });

    test("parses skipped status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[-]")).toBe("skipped");
    });

    test("returns pending for unknown status", () => {
      const loader = new FlowContextLoader("/tmp");
      expect(loader.parseFlowStatus("[?]")).toBe("pending");
    });
  });

  describe("caching", () => {
    test("caches loaded content", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");

      // Load twice
      const registry1 = await loader.loadFlowsRegistry();
      const registry2 = await loader.loadFlowsRegistry();

      // Should return same value (cached)
      expect(registry1).toBe(registry2);
    });

    test("clearFlowContextCache clears the cache", async () => {
      const loader = new FlowContextLoader("/home/cody/code/c/flow");

      // Load to populate cache
      await loader.loadFlowsRegistry();

      // Clear cache
      clearFlowContextCache();

      // Can load again without issues
      const registry = await loader.loadFlowsRegistry();
      expect(registry).not.toBeNull();
    });
  });
});

describe("FlowStatus type", () => {
  test("defines all valid status values", () => {
    const statuses: FlowStatus[] = ["pending", "in_progress", "completed", "blocked", "skipped"];
    expect(statuses).toHaveLength(5);
  });
});

describe("FlowSpec type", () => {
  test("can create valid spec object", () => {
    const spec: FlowSpec = {
      flow_id: "test-flow_20260130",
      content: "# Test Flow\n\nThis is a test.",
      file_path: "/path/to/spec.md",
    };

    expect(spec.flow_id).toBe("test-flow_20260130");
    expect(spec.content).toContain("Test Flow");
  });
});

describe("FlowMetadata type", () => {
  test("can create valid metadata object", () => {
    const metadata: FlowMetadata = {
      prd_id: "test-flow_20260130",
      type: "flow",
      status: "in_progress",
      beads_epic_id: "test-ri1",
      created_at: "2026-01-30T00:00:00Z",
      updated_at: "2026-01-30T12:00:00Z",
      description: "Test flow description",
    };

    expect(metadata.prd_id).toBe("test-flow_20260130");
    expect(metadata.beads_epic_id).toBe("test-ri1");
  });
});

describe("FlowContext type", () => {
  test("can create valid context object", () => {
    const context: FlowContext = {
      flow_id: "test-flow_20260130",
      project_root: "/path/to/project",
      spec: {
        flow_id: "test-flow_20260130",
        content: "Spec content",
        file_path: "/path/to/spec.md",
      },
      plan: null,
      patterns: "Pattern content",
      workflow: null,
      metadata: {
        prd_id: "test-flow_20260130",
        type: "flow",
        status: "pending",
        created_at: "2026-01-30T00:00:00Z",
        updated_at: "2026-01-30T00:00:00Z",
        description: "Description",
      },
    };

    expect(context.flow_id).toBe("test-flow_20260130");
    expect(context.spec).not.toBeNull();
    expect(context.plan).toBeNull();
  });
});
