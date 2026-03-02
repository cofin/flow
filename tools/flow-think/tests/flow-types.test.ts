/**
 * Flow Think MCP - Flow-Specific Types Unit Tests
 *
 * Tests for Flow-specific purpose types and context structures.
 */

import { describe, test, expect } from "bun:test";
import {
  // Flow Purpose Types
  FLOW_PURPOSE_TYPES,
  FLOW_PURPOSE_TO_COMMAND,
  isFlowPurpose,
  getFlowCommand,
  getFlowPurposeDescription,
  type FlowPurpose,
  // Flow Context Types
  type FlowContext,
  type FlowPhase,
  type FlowTask,
  type FlowTrack,
  // Flow Phase Status
  FLOW_PHASE_STATUSES,
  type FlowPhaseStatus,
  // Flow Task Status
  FLOW_TASK_STATUSES,
  type FlowTaskStatus,
  // Utility functions
  createFlowContext,
  createFlowPhase,
  createFlowTask,
  isFlowPhaseComplete,
  getFlowPhaseProgress,
} from "../src/flow/types.js";

// ─────────────────────────────────────────────────────────────
// Flow Purpose Types Tests
// ─────────────────────────────────────────────────────────────

describe("FLOW_PURPOSE_TYPES", () => {
  test("defines all required purpose types", () => {
    expect(FLOW_PURPOSE_TYPES.planning).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.research).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.implement).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.debug).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.analysis).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.reflection).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.decision).toBeDefined();
    expect(FLOW_PURPOSE_TYPES.validation).toBeDefined();
  });

  test("each purpose type has a description", () => {
    for (const [key, value] of Object.entries(FLOW_PURPOSE_TYPES)) {
      expect(typeof value).toBe("string");
      expect(value.length).toBeGreaterThan(0);
    }
  });

  test("planning purpose describes PRD and plan creation", () => {
    expect(FLOW_PURPOSE_TYPES.planning.toLowerCase()).toContain("prd");
  });

  test("research purpose describes investigation", () => {
    expect(FLOW_PURPOSE_TYPES.research.toLowerCase()).toMatch(/research|investigat/);
  });

  test("implement purpose describes TDD workflow", () => {
    expect(FLOW_PURPOSE_TYPES.implement.toLowerCase()).toContain("tdd");
  });

  test("reflection purpose describes pattern extraction", () => {
    expect(FLOW_PURPOSE_TYPES.reflection.toLowerCase()).toMatch(/pattern|learning/);
  });

  test("validation purpose describes verification", () => {
    expect(FLOW_PURPOSE_TYPES.validation.toLowerCase()).toMatch(/validat|verif/);
  });
});

describe("FLOW_PURPOSE_TO_COMMAND", () => {
  test("maps planning to flow-prd and flow-plan commands", () => {
    const commands = FLOW_PURPOSE_TO_COMMAND.planning;
    expect(commands).toContain("flow-prd");
  });

  test("maps research to flow-research command", () => {
    const commands = FLOW_PURPOSE_TO_COMMAND.research;
    expect(commands).toContain("flow-research");
  });

  test("maps implement to flow-implement command", () => {
    const commands = FLOW_PURPOSE_TO_COMMAND.implement;
    expect(commands).toContain("flow-implement");
  });

  test("maps validation to flow-validate command", () => {
    const commands = FLOW_PURPOSE_TO_COMMAND.validation;
    expect(commands).toContain("flow-validate");
  });

  test("all purposes have at least one command mapping", () => {
    for (const purpose of Object.keys(FLOW_PURPOSE_TYPES)) {
      const commands = FLOW_PURPOSE_TO_COMMAND[purpose as FlowPurpose];
      expect(Array.isArray(commands)).toBe(true);
      expect(commands.length).toBeGreaterThan(0);
    }
  });
});

describe("isFlowPurpose", () => {
  test("returns true for valid Flow purposes", () => {
    expect(isFlowPurpose("planning")).toBe(true);
    expect(isFlowPurpose("research")).toBe(true);
    expect(isFlowPurpose("implement")).toBe(true);
    expect(isFlowPurpose("debug")).toBe(true);
    expect(isFlowPurpose("analysis")).toBe(true);
    expect(isFlowPurpose("reflection")).toBe(true);
    expect(isFlowPurpose("decision")).toBe(true);
    expect(isFlowPurpose("validation")).toBe(true);
  });

  test("returns false for invalid purposes", () => {
    expect(isFlowPurpose("invalid")).toBe(false);
    expect(isFlowPurpose("")).toBe(false);
    expect(isFlowPurpose("PLANNING")).toBe(false); // case-sensitive
    expect(isFlowPurpose("exploration")).toBe(false); // generic, not Flow-specific
  });

  test("returns false for non-string values", () => {
    expect(isFlowPurpose(null as unknown as string)).toBe(false);
    expect(isFlowPurpose(undefined as unknown as string)).toBe(false);
    expect(isFlowPurpose(123 as unknown as string)).toBe(false);
  });
});

describe("getFlowCommand", () => {
  test("returns commands for valid purposes", () => {
    const commands = getFlowCommand("planning");
    expect(commands).toContain("flow-prd");
  });

  test("returns undefined for invalid purposes", () => {
    expect(getFlowCommand("invalid")).toBeUndefined();
  });

  test("returns array of commands", () => {
    const commands = getFlowCommand("implement");
    expect(Array.isArray(commands)).toBe(true);
  });
});

describe("getFlowPurposeDescription", () => {
  test("returns description for valid purposes", () => {
    const desc = getFlowPurposeDescription("planning");
    expect(desc).toBe(FLOW_PURPOSE_TYPES.planning);
  });

  test("returns undefined for invalid purposes", () => {
    expect(getFlowPurposeDescription("invalid")).toBeUndefined();
  });
});

// ─────────────────────────────────────────────────────────────
// Flow Phase Status Tests
// ─────────────────────────────────────────────────────────────

describe("FLOW_PHASE_STATUSES", () => {
  test("includes all expected statuses", () => {
    expect(FLOW_PHASE_STATUSES).toContain("pending");
    expect(FLOW_PHASE_STATUSES).toContain("in_progress");
    expect(FLOW_PHASE_STATUSES).toContain("completed");
    expect(FLOW_PHASE_STATUSES).toContain("blocked");
    expect(FLOW_PHASE_STATUSES).toContain("skipped");
  });
});

// ─────────────────────────────────────────────────────────────
// Flow Task Status Tests
// ─────────────────────────────────────────────────────────────

describe("FLOW_TASK_STATUSES", () => {
  test("includes all expected statuses matching markdown markers", () => {
    expect(FLOW_TASK_STATUSES).toContain("pending");     // [ ]
    expect(FLOW_TASK_STATUSES).toContain("in_progress"); // [~]
    expect(FLOW_TASK_STATUSES).toContain("completed");   // [x]
    expect(FLOW_TASK_STATUSES).toContain("blocked");     // [!]
    expect(FLOW_TASK_STATUSES).toContain("skipped");     // [-]
  });
});

// ─────────────────────────────────────────────────────────────
// FlowContext Type Tests
// ─────────────────────────────────────────────────────────────

describe("FlowContext type", () => {
  test("can create valid FlowContext object", () => {
    const context: FlowContext = {
      track_id: "user-auth_20260131",
      current_phase: 1,
      current_task: "1.1",
      spec_path: ".agent/specs/user-auth_20260131",
      beads_epic_id: "epic-123",
    };

    expect(context.track_id).toBe("user-auth_20260131");
    expect(context.current_phase).toBe(1);
    expect(context.current_task).toBe("1.1");
    expect(context.spec_path).toBe(".agent/specs/user-auth_20260131");
    expect(context.beads_epic_id).toBe("epic-123");
  });

  test("beads_epic_id is optional", () => {
    const context: FlowContext = {
      track_id: "feature_20260131",
      current_phase: 2,
      current_task: "2.3",
      spec_path: ".agent/specs/feature_20260131",
    };

    expect(context.beads_epic_id).toBeUndefined();
  });
});

describe("createFlowContext", () => {
  test("creates context with required fields", () => {
    const context = createFlowContext({
      track_id: "test_20260131",
      current_phase: 1,
      current_task: "1.1",
      spec_path: ".agent/specs/test_20260131",
    });

    expect(context.track_id).toBe("test_20260131");
    expect(context.current_phase).toBe(1);
    expect(context.current_task).toBe("1.1");
    expect(context.spec_path).toBe(".agent/specs/test_20260131");
  });

  test("creates context with optional beads_epic_id", () => {
    const context = createFlowContext({
      track_id: "test_20260131",
      current_phase: 1,
      current_task: "1.1",
      spec_path: ".agent/specs/test_20260131",
      beads_epic_id: "epic-456",
    });

    expect(context.beads_epic_id).toBe("epic-456");
  });
});

// ─────────────────────────────────────────────────────────────
// FlowPhase Type Tests
// ─────────────────────────────────────────────────────────────

describe("FlowPhase type", () => {
  test("can create valid FlowPhase object", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Foundation",
      status: "in_progress",
      tasks: [],
      execution_mode: "sequential",
    };

    expect(phase.number).toBe(1);
    expect(phase.name).toBe("Foundation");
    expect(phase.status).toBe("in_progress");
    expect(phase.tasks).toEqual([]);
    expect(phase.execution_mode).toBe("sequential");
  });

  test("supports parallel execution mode", () => {
    const phase: FlowPhase = {
      number: 2,
      name: "Implementation",
      status: "pending",
      tasks: [],
      execution_mode: "parallel",
    };

    expect(phase.execution_mode).toBe("parallel");
  });

  test("checkpoint_tag is optional", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "completed",
      tasks: [],
      execution_mode: "sequential",
      checkpoint_tag: "checkpoint/feature/phase-1",
    };

    expect(phase.checkpoint_tag).toBe("checkpoint/feature/phase-1");
  });
});

describe("createFlowPhase", () => {
  test("creates phase with defaults", () => {
    const phase = createFlowPhase({
      number: 1,
      name: "Foundation",
    });

    expect(phase.number).toBe(1);
    expect(phase.name).toBe("Foundation");
    expect(phase.status).toBe("pending");
    expect(phase.tasks).toEqual([]);
    expect(phase.execution_mode).toBe("sequential");
  });

  test("allows overriding defaults", () => {
    const phase = createFlowPhase({
      number: 2,
      name: "Parallel Phase",
      status: "in_progress",
      execution_mode: "parallel",
    });

    expect(phase.status).toBe("in_progress");
    expect(phase.execution_mode).toBe("parallel");
  });
});

// ─────────────────────────────────────────────────────────────
// FlowTask Type Tests
// ─────────────────────────────────────────────────────────────

describe("FlowTask type", () => {
  test("can create valid FlowTask object", () => {
    const task: FlowTask = {
      id: "1.1",
      description: "Create user model",
      status: "pending",
      phase: 1,
    };

    expect(task.id).toBe("1.1");
    expect(task.description).toBe("Create user model");
    expect(task.status).toBe("pending");
    expect(task.phase).toBe(1);
  });

  test("supports optional fields", () => {
    const task: FlowTask = {
      id: "2.3",
      description: "Implement authentication",
      status: "completed",
      phase: 2,
      commit_sha: "abc123",
      files: ["src/auth.ts", "src/auth.test.ts"],
      dependencies: ["2.1", "2.2"],
      beads_task_id: "task-789",
    };

    expect(task.commit_sha).toBe("abc123");
    expect(task.files).toEqual(["src/auth.ts", "src/auth.test.ts"]);
    expect(task.dependencies).toEqual(["2.1", "2.2"]);
    expect(task.beads_task_id).toBe("task-789");
  });

  test("supports blocked status with reason", () => {
    const task: FlowTask = {
      id: "3.1",
      description: "Deploy to production",
      status: "blocked",
      phase: 3,
      blocked_reason: "Waiting for security review",
    };

    expect(task.status).toBe("blocked");
    expect(task.blocked_reason).toBe("Waiting for security review");
  });

  test("supports skipped status with reason", () => {
    const task: FlowTask = {
      id: "3.2",
      description: "Optional feature",
      status: "skipped",
      phase: 3,
      skip_reason: "Not needed for MVP",
    };

    expect(task.status).toBe("skipped");
    expect(task.skip_reason).toBe("Not needed for MVP");
  });
});

describe("createFlowTask", () => {
  test("creates task with required fields", () => {
    const task = createFlowTask({
      id: "1.1",
      description: "Test task",
      phase: 1,
    });

    expect(task.id).toBe("1.1");
    expect(task.description).toBe("Test task");
    expect(task.status).toBe("pending");
    expect(task.phase).toBe(1);
  });

  test("allows overriding status", () => {
    const task = createFlowTask({
      id: "1.2",
      description: "In progress task",
      phase: 1,
      status: "in_progress",
    });

    expect(task.status).toBe("in_progress");
  });
});

// ─────────────────────────────────────────────────────────────
// FlowTrack Type Tests
// ─────────────────────────────────────────────────────────────

describe("FlowTrack type", () => {
  test("can create valid FlowTrack object", () => {
    const track: FlowTrack = {
      id: "user-auth_20260131",
      name: "User Authentication",
      status: "in_progress",
      created_at: "2026-01-31T10:00:00Z",
      phases: [],
    };

    expect(track.id).toBe("user-auth_20260131");
    expect(track.name).toBe("User Authentication");
    expect(track.status).toBe("in_progress");
    expect(track.phases).toEqual([]);
  });

  test("supports optional fields", () => {
    const track: FlowTrack = {
      id: "feature_20260131",
      name: "Feature",
      status: "completed",
      created_at: "2026-01-31T10:00:00Z",
      completed_at: "2026-01-31T18:00:00Z",
      phases: [],
      beads_epic_id: "epic-999",
      spec_path: ".agent/specs/feature_20260131",
    };

    expect(track.completed_at).toBe("2026-01-31T18:00:00Z");
    expect(track.beads_epic_id).toBe("epic-999");
    expect(track.spec_path).toBe(".agent/specs/feature_20260131");
  });
});

// ─────────────────────────────────────────────────────────────
// Utility Function Tests
// ─────────────────────────────────────────────────────────────

describe("isFlowPhaseComplete", () => {
  test("returns true when all tasks are completed", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "completed",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "completed", phase: 1 },
      ],
    };

    expect(isFlowPhaseComplete(phase)).toBe(true);
  });

  test("returns true when tasks are completed or skipped", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "completed",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "skipped", phase: 1 },
      ],
    };

    expect(isFlowPhaseComplete(phase)).toBe(true);
  });

  test("returns false when any task is pending", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "in_progress",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "pending", phase: 1 },
      ],
    };

    expect(isFlowPhaseComplete(phase)).toBe(false);
  });

  test("returns false when any task is in_progress", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "in_progress",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "in_progress", phase: 1 },
      ],
    };

    expect(isFlowPhaseComplete(phase)).toBe(false);
  });

  test("returns false when any task is blocked", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "blocked",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "blocked", phase: 1 },
      ],
    };

    expect(isFlowPhaseComplete(phase)).toBe(false);
  });

  test("returns true for empty tasks array", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Empty",
      status: "pending",
      execution_mode: "sequential",
      tasks: [],
    };

    expect(isFlowPhaseComplete(phase)).toBe(true);
  });
});

describe("getFlowPhaseProgress", () => {
  test("returns 100 for completed phase", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "completed",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "completed", phase: 1 },
      ],
    };

    expect(getFlowPhaseProgress(phase)).toBe(100);
  });

  test("returns 0 for pending phase", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "pending",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "pending", phase: 1 },
        { id: "1.2", description: "Task 2", status: "pending", phase: 1 },
      ],
    };

    expect(getFlowPhaseProgress(phase)).toBe(0);
  });

  test("returns correct percentage for partial progress", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "in_progress",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "pending", phase: 1 },
      ],
    };

    expect(getFlowPhaseProgress(phase)).toBe(50);
  });

  test("counts skipped as completed for progress", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Test",
      status: "in_progress",
      execution_mode: "sequential",
      tasks: [
        { id: "1.1", description: "Task 1", status: "completed", phase: 1 },
        { id: "1.2", description: "Task 2", status: "skipped", phase: 1 },
        { id: "1.3", description: "Task 3", status: "pending", phase: 1 },
      ],
    };

    // 2 out of 3 tasks are done (completed or skipped)
    expect(getFlowPhaseProgress(phase)).toBeCloseTo(66.67, 0);
  });

  test("returns 100 for empty tasks array", () => {
    const phase: FlowPhase = {
      number: 1,
      name: "Empty",
      status: "pending",
      execution_mode: "sequential",
      tasks: [],
    };

    expect(getFlowPhaseProgress(phase)).toBe(100);
  });
});
