/**
 * Flow Think MCP - Pattern Capture Tests
 *
 * Tests for pattern capture and learnings integration.
 */

import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import * as fs from "node:fs";
import * as path from "node:path";
import {
  PatternCapture,
  type PatternCategory,
  type CapturedPattern,
  PATTERN_CATEGORIES,
  formatPatternForLearnings,
  formatPatternForElevation,
  categorizePattern,
  type PatternCaptureOptions,
} from "../src/flow/patterns.js";
import type { FlowThinkStep } from "../src/types.js";

// Test helper to create a temporary directory
function createTempDir(): string {
  const tempDir = `/tmp/flow-think-test-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  fs.mkdirSync(tempDir, { recursive: true });
  return tempDir;
}

// Test helper to clean up temp directory
function cleanupTempDir(dir: string): void {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {
    // Ignore cleanup errors
  }
}

describe("Pattern Categories", () => {
  test("has expected category values", () => {
    expect(PATTERN_CATEGORIES).toContain("code-conventions");
    expect(PATTERN_CATEGORIES).toContain("architecture");
    expect(PATTERN_CATEGORIES).toContain("gotchas");
    expect(PATTERN_CATEGORIES).toContain("testing");
    expect(PATTERN_CATEGORIES).toContain("context");
    expect(PATTERN_CATEGORIES.length).toBe(5);
  });
});

describe("categorizePattern", () => {
  test("categorizes code style patterns", () => {
    expect(categorizePattern("Use camelCase for variables")).toBe("code-conventions");
    expect(categorizePattern("Import order: built-in, external, internal")).toBe("code-conventions");
    expect(categorizePattern("naming convention for handlers")).toBe("code-conventions");
  });

  test("categorizes architecture patterns", () => {
    expect(categorizePattern("Service layer handles business logic")).toBe("architecture");
    expect(categorizePattern("Use repository pattern for data access")).toBe("architecture");
    expect(categorizePattern("Module boundaries follow domain model")).toBe("architecture");
  });

  test("categorizes gotchas", () => {
    expect(categorizePattern("Watch out for race condition in auth")).toBe("gotchas");
    expect(categorizePattern("Gotcha: cache must be invalidated after update")).toBe("gotchas");
    expect(categorizePattern("Bug: the API returns null not undefined")).toBe("gotchas");
  });

  test("categorizes testing patterns", () => {
    expect(categorizePattern("Mock the database in unit tests")).toBe("testing");
    expect(categorizePattern("Use fixtures for integration tests")).toBe("testing");
    expect(categorizePattern("Test coverage should be above 80%")).toBe("testing");
  });

  test("categorizes context patterns", () => {
    expect(categorizePattern("Auth module lives in src/auth/")).toBe("context");
    expect(categorizePattern("File: config.ts contains all settings")).toBe("context");
    expect(categorizePattern("The user service is in services/user.ts")).toBe("context");
  });

  test("defaults to context for unknown patterns", () => {
    expect(categorizePattern("Some random observation")).toBe("context");
  });
});

describe("formatPatternForLearnings", () => {
  test("formats pattern with all fields", () => {
    const pattern: CapturedPattern = {
      text: "Use async/await for database calls",
      category: "code-conventions",
      source_step: 3,
      timestamp: "2026-01-31T10:00:00Z",
      flow_id: "test-flow_20260131",
      files_related: ["src/db.ts", "src/repo.ts"],
    };

    const formatted = formatPatternForLearnings(pattern);

    expect(formatted).toContain("Use async/await for database calls");
    expect(formatted).toContain("code-conventions");
    expect(formatted).toContain("Step 3");
    expect(formatted).toContain("src/db.ts");
  });

  test("formats pattern without optional fields", () => {
    const pattern: CapturedPattern = {
      text: "Simple pattern observation",
      category: "context",
      source_step: 1,
      timestamp: "2026-01-31T10:00:00Z",
    };

    const formatted = formatPatternForLearnings(pattern);

    expect(formatted).toContain("Simple pattern observation");
    expect(formatted).toContain("context");
    expect(formatted).not.toContain("Files:");
  });
});

describe("formatPatternForElevation", () => {
  test("formats pattern for patterns.md elevation", () => {
    const pattern: CapturedPattern = {
      text: "Always validate input at API boundaries",
      category: "architecture",
      source_step: 5,
      timestamp: "2026-01-31T10:00:00Z",
      flow_id: "auth-feature_20260131",
    };

    const formatted = formatPatternForElevation(pattern);

    expect(formatted).toContain("Always validate input at API boundaries");
    expect(formatted).toContain("auth-feature_20260131");
  });
});

describe("PatternCapture", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = createTempDir();
    // Create .agent/specs/test-flow/ structure
    fs.mkdirSync(path.join(tempDir, ".agent", "specs", "test-flow_20260131"), { recursive: true });
    // Create empty learnings.md
    fs.writeFileSync(
      path.join(tempDir, ".agent", "specs", "test-flow_20260131", "learnings.md"),
      "# Track Learnings\n\n---\n\n"
    );
    // Create patterns.md
    fs.writeFileSync(
      path.join(tempDir, ".agent", "patterns.md"),
      "# Project Patterns\n\n## Code Conventions\n\n## Architecture\n\n## Gotchas\n\n## Testing\n\n## Context\n\n"
    );
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
  });

  test("extracts patterns from step", () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 2,
      estimated_total: 5,
      purpose: "analysis",
      context: "Reviewing codebase",
      thought: "Found interesting patterns",
      outcome: "Documented patterns",
      next_action: "Continue",
      rationale: "For future reference",
      flow_id: "test-flow_20260131",
      patterns_discovered: [
        "Use repository pattern for data access",
        "Watch out for race conditions in auth module",
      ],
      timestamp: "2026-01-31T10:00:00Z",
    };

    const patterns = capture.extractPatterns(step);

    expect(patterns.length).toBe(2);
    expect(patterns[0].text).toBe("Use repository pattern for data access");
    expect(patterns[0].category).toBe("architecture");
    expect(patterns[1].text).toBe("Watch out for race conditions in auth module");
    expect(patterns[1].category).toBe("gotchas");
  });

  test("returns empty array when no patterns", () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 3,
      purpose: "planning",
      context: "Starting",
      thought: "Planning",
      outcome: "Plan ready",
      next_action: "Implement",
      rationale: "Need a plan",
    };

    const patterns = capture.extractPatterns(step);

    expect(patterns.length).toBe(0);
  });

  test("appends patterns to learnings.md", async () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 3,
      estimated_total: 5,
      purpose: "reflection",
      context: "Reviewing work",
      thought: "Found patterns",
      outcome: "Documented",
      next_action: "Continue",
      rationale: "For knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Service layer handles validation"],
      timestamp: "2026-01-31T10:00:00Z",
      files_referenced: ["src/services/user.ts"],
    };

    const result = await capture.captureFromStep(step);

    expect(result.success).toBe(true);
    expect(result.captured_count).toBe(1);
    expect(result.learnings_updated).toBe(true);

    // Check learnings.md was updated
    const learningsPath = path.join(
      tempDir,
      ".agent",
      "specs",
      "test-flow_20260131",
      "learnings.md"
    );
    const content = fs.readFileSync(learningsPath, "utf-8");
    expect(content).toContain("Service layer handles validation");
  });

  test("handles missing flow_id gracefully", async () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found pattern",
      outcome: "Documented",
      next_action: "Done",
      rationale: "Knowledge capture",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    const result = await capture.captureFromStep(step);

    expect(result.success).toBe(true);
    expect(result.captured_count).toBe(1);
    expect(result.learnings_updated).toBe(false);
    expect(result.reason).toContain("No flow_id");
  });

  test("elevates patterns to patterns.md when requested", async () => {
    const capture = new PatternCapture({
      workingDirectory: tempDir,
      autoElevate: true,
    });

    const step: FlowThinkStep = {
      step_number: 5,
      estimated_total: 5,
      purpose: "reflection",
      context: "Final review",
      thought: "Important pattern found",
      outcome: "Should be elevated",
      next_action: "Complete",
      rationale: "Project-wide learning",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Critical: Always sanitize user input"],
      timestamp: "2026-01-31T10:00:00Z",
      is_final_step: true,
    };

    const result = await capture.captureFromStep(step);

    expect(result.success).toBe(true);
    expect(result.elevated_count).toBeGreaterThan(0);

    // Check patterns.md was updated
    const patternsPath = path.join(tempDir, ".agent", "patterns.md");
    const content = fs.readFileSync(patternsPath, "utf-8");
    expect(content).toContain("Always sanitize user input");
  });

  test("does not elevate when autoElevate is false", async () => {
    const capture = new PatternCapture({
      workingDirectory: tempDir,
      autoElevate: false,
    });

    const step: FlowThinkStep = {
      step_number: 5,
      estimated_total: 5,
      purpose: "reflection",
      context: "Final review",
      thought: "Pattern found",
      outcome: "Documented",
      next_action: "Complete",
      rationale: "Learning",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
      is_final_step: true,
    };

    const result = await capture.captureFromStep(step);

    expect(result.success).toBe(true);
    expect(result.elevated_count).toBe(0);
  });

  test("handles missing learnings.md gracefully", async () => {
    // Remove learnings.md
    fs.unlinkSync(path.join(tempDir, ".agent", "specs", "test-flow_20260131", "learnings.md"));

    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found pattern",
      outcome: "Documented",
      next_action: "Done",
      rationale: "Knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    const result = await capture.captureFromStep(step);

    // Should create the file
    expect(result.success).toBe(true);
    expect(result.learnings_updated).toBe(true);

    const learningsPath = path.join(
      tempDir,
      ".agent",
      "specs",
      "test-flow_20260131",
      "learnings.md"
    );
    expect(fs.existsSync(learningsPath)).toBe(true);
  });

  test("handles missing .agent directory gracefully", async () => {
    // Remove .agent directory
    fs.rmSync(path.join(tempDir, ".agent"), { recursive: true, force: true });

    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found pattern",
      outcome: "Documented",
      next_action: "Done",
      rationale: "Knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    const result = await capture.captureFromStep(step);

    // Should fail gracefully - cannot create spec directory without .agent
    expect(result.success).toBe(true);
    expect(result.learnings_updated).toBe(false);
  });

  test("gets capture statistics", async () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found patterns",
      outcome: "Documented",
      next_action: "Continue",
      rationale: "Knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Pattern 1", "Pattern 2"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    await capture.captureFromStep(step);

    const stats = capture.getStats();

    expect(stats.total_captured).toBe(2);
    expect(stats.by_category["context"]).toBeGreaterThanOrEqual(0);
  });

  test("resets statistics", async () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found pattern",
      outcome: "Documented",
      next_action: "Done",
      rationale: "Knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    await capture.captureFromStep(step);
    capture.resetStats();

    const stats = capture.getStats();
    expect(stats.total_captured).toBe(0);
  });

  test("elevates specific pattern to patterns.md", async () => {
    const capture = new PatternCapture({ workingDirectory: tempDir });

    const pattern: CapturedPattern = {
      text: "Use dependency injection for testability",
      category: "architecture",
      source_step: 3,
      timestamp: "2026-01-31T10:00:00Z",
      flow_id: "test-flow_20260131",
    };

    const result = await capture.elevatePattern(pattern);

    expect(result.success).toBe(true);

    const patternsPath = path.join(tempDir, ".agent", "patterns.md");
    const content = fs.readFileSync(patternsPath, "utf-8");
    expect(content).toContain("Use dependency injection for testability");
    expect(content).toContain("## Architecture");
  });
});

describe("PatternCapture disabled mode", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = createTempDir();
  });

  afterEach(() => {
    cleanupTempDir(tempDir);
  });

  test("does nothing when disabled", async () => {
    const capture = new PatternCapture({
      workingDirectory: tempDir,
      enabled: false,
    });

    const step: FlowThinkStep = {
      step_number: 1,
      estimated_total: 2,
      purpose: "analysis",
      context: "Analyzing",
      thought: "Found pattern",
      outcome: "Documented",
      next_action: "Done",
      rationale: "Knowledge capture",
      flow_id: "test-flow_20260131",
      patterns_discovered: ["Some pattern"],
      timestamp: "2026-01-31T10:00:00Z",
    };

    const result = await capture.captureFromStep(step);

    expect(result.success).toBe(true);
    expect(result.captured_count).toBe(0);
    expect(result.reason).toContain("disabled");
  });
});
