/**
 * Flow Think MCP - Types Unit Tests
 *
 * Tests for type utilities and constants defined in types.ts.
 */

import { describe, test, expect } from "bun:test";
import {
  CONFIDENCE_THRESHOLDS,
  getConfidenceLevel,
  validateRevisionTarget,
  validateBranchRequest,
  generateBranchId,
  validateDependencies,
  generateSessionId,
  type ConfidenceLevel,
  type ConfidenceWarning,
  type RevisionInfo,
  type RevisionValidationResult,
  type Branch,
  type BranchStatus,
  type SessionEntry,
  type DependencyValidationResult,
} from "../src/types.js";

describe("CONFIDENCE_THRESHOLDS", () => {
  test("defines expected thresholds", () => {
    expect(CONFIDENCE_THRESHOLDS.low).toBe(0.3);
    expect(CONFIDENCE_THRESHOLDS.medium).toBe(0.5);
    expect(CONFIDENCE_THRESHOLDS.high).toBe(0.8);
    expect(CONFIDENCE_THRESHOLDS.very_high).toBe(0.95);
  });

  test("thresholds are in ascending order", () => {
    expect(CONFIDENCE_THRESHOLDS.low).toBeLessThan(CONFIDENCE_THRESHOLDS.medium);
    expect(CONFIDENCE_THRESHOLDS.medium).toBeLessThan(CONFIDENCE_THRESHOLDS.high);
    expect(CONFIDENCE_THRESHOLDS.high).toBeLessThan(CONFIDENCE_THRESHOLDS.very_high);
  });
});

describe("getConfidenceLevel", () => {
  test("returns 'low' for confidence below 0.3", () => {
    expect(getConfidenceLevel(0)).toBe("low");
    expect(getConfidenceLevel(0.1)).toBe("low");
    expect(getConfidenceLevel(0.29)).toBe("low");
  });

  test("returns 'low' for confidence at 0.3 threshold", () => {
    // 0.3 is the boundary for "low" - values < 0.5 are still "low"
    expect(getConfidenceLevel(0.3)).toBe("low");
    expect(getConfidenceLevel(0.49)).toBe("low");
  });

  test("returns 'medium' for confidence >= 0.5 and < 0.8", () => {
    expect(getConfidenceLevel(0.5)).toBe("medium");
    expect(getConfidenceLevel(0.6)).toBe("medium");
    expect(getConfidenceLevel(0.79)).toBe("medium");
  });

  test("returns 'high' for confidence >= 0.8 and < 0.95", () => {
    expect(getConfidenceLevel(0.8)).toBe("high");
    expect(getConfidenceLevel(0.9)).toBe("high");
    expect(getConfidenceLevel(0.94)).toBe("high");
  });

  test("returns 'very_high' for confidence >= 0.95", () => {
    expect(getConfidenceLevel(0.95)).toBe("very_high");
    expect(getConfidenceLevel(0.99)).toBe("very_high");
    expect(getConfidenceLevel(1.0)).toBe("very_high");
  });

  test("handles edge cases", () => {
    expect(getConfidenceLevel(-0.1)).toBe("low"); // Negative becomes low
    expect(getConfidenceLevel(1.5)).toBe("very_high"); // Above 1 becomes very_high
  });
});

describe("ConfidenceWarning type", () => {
  test("can create valid warning object", () => {
    const warning: ConfidenceWarning = {
      level: "warning",
      message: "Low confidence detected",
      suggestion: "Consider gathering more information",
      confidence: 0.25,
      threshold: 0.5,
    };

    expect(warning.level).toBe("warning");
    expect(warning.message).toBe("Low confidence detected");
    expect(warning.suggestion).toBe("Consider gathering more information");
    expect(warning.confidence).toBe(0.25);
    expect(warning.threshold).toBe(0.5);
  });

  test("suggestion is optional", () => {
    const warning: ConfidenceWarning = {
      level: "info",
      message: "Confidence noted",
      confidence: 0.6,
      threshold: 0.5,
    };

    expect(warning.suggestion).toBeUndefined();
  });

  test("supports all warning levels", () => {
    const levels: ConfidenceWarning["level"][] = ["info", "warning", "critical"];

    for (const level of levels) {
      const warning: ConfidenceWarning = {
        level,
        message: `${level} level warning`,
        confidence: 0.2,
        threshold: 0.5,
      };
      expect(warning.level).toBe(level);
    }
  });
});

describe("RevisionInfo type", () => {
  test("can create valid revision info object", () => {
    const info: RevisionInfo = {
      original_step: 3,
      revised_by: 7,
      reason: "Found a bug in the original analysis",
      timestamp: new Date().toISOString(),
    };

    expect(info.original_step).toBe(3);
    expect(info.revised_by).toBe(7);
    expect(info.reason).toBe("Found a bug in the original analysis");
    expect(info.timestamp).toBeDefined();
  });
});

describe("validateRevisionTarget", () => {
  test("returns valid for existing step", () => {
    const existingSteps = new Set([1, 2, 3, 5]);
    const result = validateRevisionTarget(3, existingSteps);

    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  test("returns error for non-existent step", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateRevisionTarget(5, existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("step does not exist");
    expect(result.error).toContain("5");
  });

  test("returns error for step number less than 1", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateRevisionTarget(0, existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("must be >= 1");
  });

  test("returns error for negative step number", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateRevisionTarget(-1, existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("must be >= 1");
  });

  test("works with empty step set", () => {
    const existingSteps = new Set<number>();
    const result = validateRevisionTarget(1, existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("does not exist");
  });
});

describe("Branch type", () => {
  test("can create valid branch object", () => {
    const branch: Branch = {
      id: "branch-123",
      name: "Alternative approach A",
      from_step: 3,
      steps: [4, 5, 6],
      status: "active",
      depth: 1,
      created_at: new Date().toISOString(),
    };

    expect(branch.id).toBe("branch-123");
    expect(branch.from_step).toBe(3);
    expect(branch.steps).toHaveLength(3);
    expect(branch.depth).toBe(1);
  });

  test("supports all branch statuses", () => {
    const statuses: BranchStatus[] = ["active", "merged", "abandoned"];

    for (const status of statuses) {
      const branch: Branch = {
        id: "test",
        from_step: 1,
        steps: [],
        status,
        depth: 0,
        created_at: new Date().toISOString(),
      };
      expect(branch.status).toBe(status);
    }
  });

  test("supports nested branches with parent_branch", () => {
    const nestedBranch: Branch = {
      id: "nested-branch",
      from_step: 5,
      steps: [6, 7],
      status: "active",
      depth: 2,
      parent_branch: "parent-branch",
      created_at: new Date().toISOString(),
    };

    expect(nestedBranch.parent_branch).toBe("parent-branch");
    expect(nestedBranch.depth).toBe(2);
  });
});

describe("validateBranchRequest", () => {
  test("returns valid for existing step within depth limit", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateBranchRequest(2, existingSteps, 0, 5);

    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  test("returns error for non-existent step", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateBranchRequest(10, existingSteps, 0, 5);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("does not exist");
  });

  test("returns error for step number less than 1", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateBranchRequest(0, existingSteps, 0, 5);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("must be >= 1");
  });

  test("returns error when max depth exceeded", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateBranchRequest(2, existingSteps, 5, 5);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("Maximum branch depth");
    expect(result.error).toContain("5");
  });

  test("allows branching at depth just under max", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateBranchRequest(2, existingSteps, 4, 5);

    expect(result.valid).toBe(true);
  });
});

describe("generateBranchId", () => {
  test("generates unique IDs", () => {
    const ids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      ids.add(generateBranchId());
    }
    expect(ids.size).toBe(100);
  });

  test("uses default prefix", () => {
    const id = generateBranchId();
    expect(id).toMatch(/^branch-/);
  });

  test("uses custom prefix", () => {
    const id = generateBranchId("alt");
    expect(id).toMatch(/^alt-/);
  });

  test("includes timestamp-like component", () => {
    const id = generateBranchId();
    // Format: prefix-timestamp-random
    const parts = id.split("-");
    expect(parts.length).toBeGreaterThanOrEqual(3);
  });
});

describe("validateDependencies", () => {
  test("returns valid for existing dependencies", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateDependencies(4, [1, 2], existingSteps);

    expect(result.valid).toBe(true);
    expect(result.error).toBeUndefined();
  });

  test("returns error for non-existent dependency", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateDependencies(4, [1, 10], existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("do not exist");
    expect(result.invalid_steps).toContain(10);
  });

  test("returns error for self-dependency", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateDependencies(2, [2], existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("cannot depend on itself");
  });

  test("returns error for invalid dependency number", () => {
    const existingSteps = new Set([1, 2, 3]);
    const result = validateDependencies(4, [0], existingSteps);

    expect(result.valid).toBe(false);
    expect(result.error).toContain("must be >= 1");
  });
});

describe("generateSessionId", () => {
  test("generates unique IDs", () => {
    const ids = new Set<string>();
    for (let i = 0; i < 100; i++) {
      ids.add(generateSessionId());
    }
    expect(ids.size).toBe(100);
  });

  test("uses session prefix", () => {
    const id = generateSessionId();
    expect(id).toMatch(/^session-/);
  });

  test("includes timestamp-like component", () => {
    const id = generateSessionId();
    // Format: session-timestamp-random
    const parts = id.split("-");
    expect(parts.length).toBeGreaterThanOrEqual(3);
  });
});
