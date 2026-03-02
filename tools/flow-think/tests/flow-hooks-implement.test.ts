/**
 * Flow Think MCP - Flow Implement Hooks Tests
 *
 * Tests for TDD-specific step templates and workflow helpers for flow-implement command.
 */

import { describe, test, expect } from "bun:test";
import {
  TDD_PHASES,
  TDD_PHASE_ORDER,
  type TDDPhase,
  type TDDCycleState,
  type TDDOutcome,
  type CoverageInfo,
  createTDDStep,
  createRedPhaseStep,
  createGreenPhaseStep,
  createRefactorPhaseStep,
  createCoverageVerificationStep,
  createTDDCycleState,
  advanceTDDCycle,
  getTDDCycleProgress,
  formatTDDOutcome,
  formatCoverageReport,
  validateTDDTransition,
  isTDDComplete,
} from "../src/flow/hooks/implement.js";

describe("TDD Phase Constants", () => {
  test("TDD_PHASES contains all four phases", () => {
    expect(TDD_PHASES.red).toBeDefined();
    expect(TDD_PHASES.green).toBeDefined();
    expect(TDD_PHASES.refactor).toBeDefined();
    expect(TDD_PHASES.verify).toBeDefined();
  });

  test("each phase has purpose and description", () => {
    for (const phase of Object.values(TDD_PHASES)) {
      expect(phase.purpose).toBe("implement");
      expect(phase.description).toBeDefined();
      expect(phase.description.length).toBeGreaterThan(0);
    }
  });

  test("TDD_PHASE_ORDER defines correct sequence", () => {
    expect(TDD_PHASE_ORDER).toEqual(["red", "green", "refactor", "verify"]);
  });
});

describe("createTDDStep", () => {
  test("creates step with implement purpose", () => {
    const step = createTDDStep({
      phase: "red",
      step_number: 1,
      estimated_total: 4,
      context: "Starting TDD cycle",
      thought: "Writing failing test",
      outcome: "Test created",
      next_action: "Run test to verify it fails",
      rationale: "TDD requires test-first approach",
    });

    expect(step.purpose).toBe("implement");
    expect(step.step_number).toBe(1);
  });

  test("includes TDD phase metadata", () => {
    const step = createTDDStep({
      phase: "green",
      step_number: 2,
      estimated_total: 4,
      context: "Test is failing",
      thought: "Implementing minimum code",
      outcome: "Implementation complete",
      next_action: "Run tests",
      rationale: "Make test pass",
    });

    expect(step.external_context?.tdd_phase).toBe("green");
  });

  test("accepts optional fields", () => {
    const step = createTDDStep({
      phase: "red",
      step_number: 1,
      estimated_total: 4,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: "Action",
      rationale: "Rationale",
      confidence: 0.8,
      files_referenced: ["src/module.ts", "tests/module.test.ts"],
      beads_task_id: "task-123",
    });

    expect(step.confidence).toBe(0.8);
    expect(step.files_referenced).toContain("src/module.ts");
    expect(step.beads_task_id).toBe("task-123");
  });
});

describe("createRedPhaseStep", () => {
  test("creates step for red phase", () => {
    const step = createRedPhaseStep({
      step_number: 1,
      estimated_total: 4,
      test_description: "should validate user input",
      test_file: "tests/validate.test.ts",
      context: "Implementing input validation",
    });

    expect(step.purpose).toBe("implement");
    expect(step.external_context?.tdd_phase).toBe("red");
    expect(step.thought).toContain("failing test");
    expect(step.files_referenced).toContain("tests/validate.test.ts");
  });

  test("uses default estimated_total of 4", () => {
    const step = createRedPhaseStep({
      step_number: 1,
      test_description: "test case",
      test_file: "test.ts",
      context: "Context",
    });

    expect(step.estimated_total).toBe(4);
  });

  test("includes test description in outcome", () => {
    const step = createRedPhaseStep({
      step_number: 1,
      test_description: "should handle edge cases",
      test_file: "test.ts",
      context: "Testing edge cases",
    });

    expect(step.outcome).toContain("should handle edge cases");
  });
});

describe("createGreenPhaseStep", () => {
  test("creates step for green phase", () => {
    const step = createGreenPhaseStep({
      step_number: 2,
      estimated_total: 4,
      implementation_approach: "Add validation function",
      target_file: "src/validate.ts",
      context: "Test is failing as expected",
    });

    expect(step.purpose).toBe("implement");
    expect(step.external_context?.tdd_phase).toBe("green");
    expect(step.thought).toContain("minimum code");
    expect(step.files_referenced).toContain("src/validate.ts");
  });

  test("includes implementation approach in outcome", () => {
    const step = createGreenPhaseStep({
      step_number: 2,
      implementation_approach: "Use regex for validation",
      target_file: "src/validate.ts",
      context: "Context",
    });

    expect(step.outcome).toContain("Use regex for validation");
  });
});

describe("createRefactorPhaseStep", () => {
  test("creates step for refactor phase", () => {
    const step = createRefactorPhaseStep({
      step_number: 3,
      estimated_total: 4,
      refactor_goals: ["Extract common logic", "Improve naming"],
      affected_files: ["src/validate.ts", "src/utils.ts"],
      context: "Tests are passing",
    });

    expect(step.purpose).toBe("implement");
    expect(step.external_context?.tdd_phase).toBe("refactor");
    expect(step.thought).toContain("while tests pass");
    expect(step.files_referenced).toContain("src/validate.ts");
    expect(step.files_referenced).toContain("src/utils.ts");
  });

  test("lists refactor goals in outcome", () => {
    const step = createRefactorPhaseStep({
      step_number: 3,
      refactor_goals: ["DRY principle", "Better error handling"],
      affected_files: ["src/module.ts"],
      context: "Context",
    });

    expect(step.outcome).toContain("DRY principle");
    expect(step.outcome).toContain("Better error handling");
  });

  test("handles empty refactor goals", () => {
    const step = createRefactorPhaseStep({
      step_number: 3,
      refactor_goals: [],
      affected_files: ["src/module.ts"],
      context: "Context",
    });

    expect(step.outcome).toContain("No refactoring needed");
  });
});

describe("createCoverageVerificationStep", () => {
  test("creates step for coverage verification", () => {
    const coverage: CoverageInfo = {
      total: 85,
      statements: 87,
      branches: 80,
      functions: 90,
      lines: 85,
    };

    const step = createCoverageVerificationStep({
      step_number: 4,
      estimated_total: 4,
      coverage,
      target_coverage: 80,
      context: "Refactoring complete",
    });

    expect(step.purpose).toBe("implement");
    expect(step.external_context?.tdd_phase).toBe("verify");
    expect(step.external_context?.coverage).toEqual(coverage);
    expect(step.outcome).toContain("85%");
  });

  test("indicates success when coverage meets target", () => {
    const step = createCoverageVerificationStep({
      step_number: 4,
      coverage: { total: 85 },
      target_coverage: 80,
      context: "Context",
    });

    expect(step.thought).toContain("meets target");
    expect(step.confidence).toBeGreaterThanOrEqual(0.8);
  });

  test("indicates failure when coverage below target", () => {
    const step = createCoverageVerificationStep({
      step_number: 4,
      coverage: { total: 65 },
      target_coverage: 80,
      context: "Context",
    });

    expect(step.thought).toContain("below target");
    expect(step.confidence).toBeLessThan(0.8);
  });

  test("uses default target coverage of 80%", () => {
    const step = createCoverageVerificationStep({
      step_number: 4,
      coverage: { total: 75 },
      context: "Context",
    });

    expect(step.thought).toContain("below target");
  });

  test("marks as final step when coverage passes", () => {
    const step = createCoverageVerificationStep({
      step_number: 4,
      coverage: { total: 90 },
      target_coverage: 80,
      context: "Context",
    });

    expect(step.is_final_step).toBe(true);
  });

  test("does not mark as final when coverage fails", () => {
    const step = createCoverageVerificationStep({
      step_number: 4,
      coverage: { total: 60 },
      target_coverage: 80,
      context: "Context",
    });

    expect(step.is_final_step).toBeFalsy();
  });
});

describe("TDD Cycle State Management", () => {
  describe("createTDDCycleState", () => {
    test("creates initial state", () => {
      const state = createTDDCycleState("task-123");

      expect(state.task_id).toBe("task-123");
      expect(state.current_phase).toBe("red");
      expect(state.cycle_number).toBe(1);
      expect(state.phases_completed).toEqual([]);
      expect(state.started_at).toBeDefined();
    });

    test("accepts optional cycle number", () => {
      const state = createTDDCycleState("task-123", 3);

      expect(state.cycle_number).toBe(3);
    });
  });

  describe("advanceTDDCycle", () => {
    test("advances from red to green", () => {
      const state = createTDDCycleState("task-123");
      const newState = advanceTDDCycle(state);

      expect(newState.current_phase).toBe("green");
      expect(newState.phases_completed).toContain("red");
    });

    test("advances from green to refactor", () => {
      const state: TDDCycleState = {
        ...createTDDCycleState("task-123"),
        current_phase: "green",
        phases_completed: ["red"],
      };
      const newState = advanceTDDCycle(state);

      expect(newState.current_phase).toBe("refactor");
      expect(newState.phases_completed).toContain("green");
    });

    test("advances from refactor to verify", () => {
      const state: TDDCycleState = {
        ...createTDDCycleState("task-123"),
        current_phase: "refactor",
        phases_completed: ["red", "green"],
      };
      const newState = advanceTDDCycle(state);

      expect(newState.current_phase).toBe("verify");
      expect(newState.phases_completed).toContain("refactor");
    });

    test("completes cycle after verify", () => {
      const state: TDDCycleState = {
        ...createTDDCycleState("task-123"),
        current_phase: "verify",
        phases_completed: ["red", "green", "refactor"],
      };
      const newState = advanceTDDCycle(state);

      expect(newState.phases_completed).toContain("verify");
      expect(newState.completed_at).toBeDefined();
    });
  });

  describe("getTDDCycleProgress", () => {
    test("returns progress for each phase", () => {
      expect(getTDDCycleProgress(createTDDCycleState("t"))).toBe(0);

      const afterRed: TDDCycleState = {
        ...createTDDCycleState("t"),
        current_phase: "green",
        phases_completed: ["red"],
      };
      expect(getTDDCycleProgress(afterRed)).toBe(25);

      const afterGreen: TDDCycleState = {
        ...createTDDCycleState("t"),
        current_phase: "refactor",
        phases_completed: ["red", "green"],
      };
      expect(getTDDCycleProgress(afterGreen)).toBe(50);

      const afterRefactor: TDDCycleState = {
        ...createTDDCycleState("t"),
        current_phase: "verify",
        phases_completed: ["red", "green", "refactor"],
      };
      expect(getTDDCycleProgress(afterRefactor)).toBe(75);

      const complete: TDDCycleState = {
        ...createTDDCycleState("t"),
        current_phase: "verify",
        phases_completed: ["red", "green", "refactor", "verify"],
        completed_at: new Date().toISOString(),
      };
      expect(getTDDCycleProgress(complete)).toBe(100);
    });
  });

  describe("validateTDDTransition", () => {
    test("allows valid transitions", () => {
      expect(validateTDDTransition("red", "green")).toEqual({ valid: true });
      expect(validateTDDTransition("green", "refactor")).toEqual({ valid: true });
      expect(validateTDDTransition("refactor", "verify")).toEqual({ valid: true });
    });

    test("rejects invalid transitions", () => {
      const result = validateTDDTransition("red", "refactor");
      expect(result.valid).toBe(false);
      expect(result.error).toContain("Invalid transition");
    });

    test("allows going back to red from any phase", () => {
      expect(validateTDDTransition("green", "red")).toEqual({ valid: true });
      expect(validateTDDTransition("refactor", "red")).toEqual({ valid: true });
      expect(validateTDDTransition("verify", "red")).toEqual({ valid: true });
    });
  });

  describe("isTDDComplete", () => {
    test("returns false for incomplete cycle", () => {
      expect(isTDDComplete(createTDDCycleState("t"))).toBe(false);
    });

    test("returns true when all phases completed", () => {
      const complete: TDDCycleState = {
        ...createTDDCycleState("t"),
        phases_completed: ["red", "green", "refactor", "verify"],
        completed_at: new Date().toISOString(),
      };
      expect(isTDDComplete(complete)).toBe(true);
    });
  });
});

describe("Output Formatting", () => {
  describe("formatTDDOutcome", () => {
    test("formats successful outcome", () => {
      const outcome: TDDOutcome = {
        task_id: "task-123",
        task_name: "Add user validation",
        success: true,
        cycles_completed: 1,
        final_coverage: 92,
        tests_added: 5,
        files_modified: ["src/validate.ts", "tests/validate.test.ts"],
        duration_ms: 45000,
        learnings: ["Input validation should use early returns"],
      };

      const formatted = formatTDDOutcome(outcome);

      expect(formatted).toContain("task-123");
      expect(formatted).toContain("Add user validation");
      expect(formatted).toContain("SUCCESS");
      expect(formatted).toContain("92%");
      expect(formatted).toContain("5 tests");
    });

    test("formats failed outcome", () => {
      const outcome: TDDOutcome = {
        task_id: "task-456",
        task_name: "Complex feature",
        success: false,
        cycles_completed: 2,
        final_coverage: 65,
        tests_added: 3,
        files_modified: ["src/feature.ts"],
        failure_reason: "Coverage target not met",
      };

      const formatted = formatTDDOutcome(outcome);

      expect(formatted).toContain("FAILED");
      expect(formatted).toContain("Coverage target not met");
    });

    test("includes markdown formatting", () => {
      const outcome: TDDOutcome = {
        task_id: "t",
        task_name: "Task",
        success: true,
        cycles_completed: 1,
        final_coverage: 90,
        tests_added: 2,
        files_modified: [],
      };

      const formatted = formatTDDOutcome(outcome);

      expect(formatted).toContain("##");
      expect(formatted).toContain("**");
    });
  });

  describe("formatCoverageReport", () => {
    test("formats full coverage info", () => {
      const coverage: CoverageInfo = {
        total: 85,
        statements: 87,
        branches: 80,
        functions: 90,
        lines: 85,
      };

      const report = formatCoverageReport(coverage, 80);

      expect(report).toContain("85%");
      expect(report).toContain("**Statements:** 87%");
      expect(report).toContain("**Branches:** 80%");
      expect(report).toContain("**Functions:** 90%");
      expect(report).toContain("**Lines:** 85%");
      expect(report).toContain("PASS");
    });

    test("formats minimal coverage info", () => {
      const coverage: CoverageInfo = {
        total: 75,
      };

      const report = formatCoverageReport(coverage, 80);

      expect(report).toContain("75%");
      expect(report).toContain("FAIL");
    });

    test("indicates pass/fail based on target", () => {
      const passing = formatCoverageReport({ total: 85 }, 80);
      const failing = formatCoverageReport({ total: 75 }, 80);

      expect(passing).toContain("PASS");
      expect(failing).toContain("FAIL");
    });
  });
});
