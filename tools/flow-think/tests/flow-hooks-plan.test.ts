/**
 * Flow Think MCP - Plan Hooks Unit Tests
 *
 * Tests for flow-plan command integration hooks.
 * These hooks provide plan-specific step templates for the planning workflow.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import {
  createPlanStep,
  createTaskBreakdownStep,
  createPhaseOrganizationStep,
  createDependencyTrackingStep,
  updateTaskStatus,
  PLAN_PURPOSE,
  PLAN_STEP_TEMPLATES,
  type PlanStepInput,
  type TaskBreakdownInput,
  type PhaseOrganizationInput,
  type DependencyTrackingInput,
  type TaskStatusUpdate,
  type TaskStatus,
} from "../src/flow/hooks/plan.js";

describe("PLAN_PURPOSE constant", () => {
  test("equals 'planning'", () => {
    expect(PLAN_PURPOSE).toBe("planning");
  });
});

describe("PLAN_STEP_TEMPLATES", () => {
  test("has task_breakdown template", () => {
    expect(PLAN_STEP_TEMPLATES.task_breakdown).toBeDefined();
    expect(PLAN_STEP_TEMPLATES.task_breakdown.purpose).toBe("planning");
    expect(PLAN_STEP_TEMPLATES.task_breakdown.description).toContain("task");
  });

  test("has phase_organization template", () => {
    expect(PLAN_STEP_TEMPLATES.phase_organization).toBeDefined();
    expect(PLAN_STEP_TEMPLATES.phase_organization.purpose).toBe("planning");
    expect(PLAN_STEP_TEMPLATES.phase_organization.description).toContain(
      "phase"
    );
  });

  test("has dependency_tracking template", () => {
    expect(PLAN_STEP_TEMPLATES.dependency_tracking).toBeDefined();
    expect(PLAN_STEP_TEMPLATES.dependency_tracking.purpose).toBe("planning");
    expect(PLAN_STEP_TEMPLATES.dependency_tracking.description).toContain(
      "depend"
    );
  });

  test("all templates have required fields", () => {
    for (const [name, template] of Object.entries(PLAN_STEP_TEMPLATES)) {
      expect(template.purpose).toBe("planning");
      expect(template.description).toBeTruthy();
      expect(template.contextHints).toBeDefined();
      expect(Array.isArray(template.contextHints)).toBe(true);
    }
  });
});

describe("createPlanStep", () => {
  test("creates step with planning purpose", () => {
    const input: PlanStepInput = {
      step_number: 1,
      estimated_total: 5,
      context: "Analyzing PRD for user authentication feature",
      thought: "Need to break down the requirements into implementable tasks",
      outcome: "Identified 3 main areas: login, registration, password reset",
      next_action: "Create task breakdown for each area",
      rationale:
        "Breaking into areas first helps organize the work into phases",
    };

    const step = createPlanStep(input);

    expect(step.purpose).toBe("planning");
    expect(step.step_number).toBe(1);
    expect(step.estimated_total).toBe(5);
    expect(step.context).toBe(input.context);
    expect(step.thought).toBe(input.thought);
    expect(step.outcome).toBe(input.outcome);
    expect(step.next_action).toBe(input.next_action);
    expect(step.rationale).toBe(input.rationale);
  });

  test("accepts optional flow_id", () => {
    const step = createPlanStep({
      step_number: 1,
      estimated_total: 3,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: "Next",
      rationale: "Rationale",
      flow_id: "user-auth_20260131",
    });

    expect(step.flow_id).toBe("user-auth_20260131");
  });

  test("accepts optional beads_task_id", () => {
    const step = createPlanStep({
      step_number: 1,
      estimated_total: 3,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: "Next",
      rationale: "Rationale",
      beads_task_id: "BD-123",
    });

    expect(step.beads_task_id).toBe("BD-123");
  });

  test("accepts optional confidence", () => {
    const step = createPlanStep({
      step_number: 1,
      estimated_total: 3,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: "Next",
      rationale: "Rationale",
      confidence: 0.85,
    });

    expect(step.confidence).toBe(0.85);
  });

  test("accepts optional files_referenced", () => {
    const files = ["/path/to/spec.md", "/path/to/plan.md"];
    const step = createPlanStep({
      step_number: 1,
      estimated_total: 3,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: "Next",
      rationale: "Rationale",
      files_referenced: files,
    });

    expect(step.files_referenced).toEqual(files);
  });

  test("accepts structured next_action", () => {
    const step = createPlanStep({
      step_number: 1,
      estimated_total: 3,
      context: "Context",
      thought: "Thought",
      outcome: "Outcome",
      next_action: {
        tool: "Read",
        action: "Read the PRD file",
        expectedOutput: "PRD contents",
      },
      rationale: "Rationale",
    });

    expect(typeof step.next_action).toBe("object");
    expect((step.next_action as { action: string }).action).toBe(
      "Read the PRD file"
    );
  });
});

describe("createTaskBreakdownStep", () => {
  test("creates task breakdown step", () => {
    const input: TaskBreakdownInput = {
      step_number: 2,
      estimated_total: 5,
      prd_summary: "User authentication system with OAuth support",
      identified_tasks: [
        "Set up OAuth provider configuration",
        "Implement login flow",
        "Implement registration flow",
        "Add session management",
      ],
      next_action: "Organize tasks into phases",
      rationale: "Breaking down into atomic tasks helps estimate effort",
    };

    const step = createTaskBreakdownStep(input);

    expect(step.purpose).toBe("planning");
    expect(step.step_number).toBe(2);
    expect(step.context).toContain("User authentication system");
    expect(step.thought).toContain("break down");
    expect(step.outcome).toContain("4 tasks identified");
    expect(step.outcome).toContain("Set up OAuth");
    expect(step.outcome).toContain("Implement login");
    expect(step.next_action).toBe(input.next_action);
    expect(step.rationale).toBe(input.rationale);
  });

  test("handles empty task list", () => {
    const input: TaskBreakdownInput = {
      step_number: 1,
      estimated_total: 3,
      prd_summary: "Simple feature",
      identified_tasks: [],
      next_action: "Re-analyze requirements",
      rationale: "No clear tasks identified yet",
    };

    const step = createTaskBreakdownStep(input);

    expect(step.outcome).toContain("0 tasks identified");
  });

  test("accepts optional priority ordering", () => {
    const input: TaskBreakdownInput = {
      step_number: 2,
      estimated_total: 5,
      prd_summary: "Feature X",
      identified_tasks: ["Task A", "Task B", "Task C"],
      priority_order: ["Task C", "Task A", "Task B"],
      next_action: "Next",
      rationale: "Rationale",
    };

    const step = createTaskBreakdownStep(input);

    expect(step.outcome).toContain("Priority order");
    expect(step.outcome).toContain("Task C");
  });

  test("accepts optional flow_id and beads_task_id", () => {
    const input: TaskBreakdownInput = {
      step_number: 1,
      estimated_total: 3,
      prd_summary: "Feature",
      identified_tasks: ["Task"],
      next_action: "Next",
      rationale: "Rationale",
      flow_id: "feature_20260131",
      beads_task_id: "BD-456",
    };

    const step = createTaskBreakdownStep(input);

    expect(step.flow_id).toBe("feature_20260131");
    expect(step.beads_task_id).toBe("BD-456");
  });
});

describe("createPhaseOrganizationStep", () => {
  test("creates phase organization step", () => {
    const input: PhaseOrganizationInput = {
      step_number: 3,
      estimated_total: 5,
      phases: [
        {
          name: "Phase 1: Setup",
          tasks: ["Install dependencies", "Configure database"],
        },
        {
          name: "Phase 2: Core Implementation",
          tasks: ["Implement auth flow", "Add user model"],
        },
        {
          name: "Phase 3: Integration",
          tasks: ["Connect frontend", "Write tests"],
        },
      ],
      next_action: "Create plan.md document",
      rationale:
        "Phases group related tasks for incremental delivery and testing",
    };

    const step = createPhaseOrganizationStep(input);

    expect(step.purpose).toBe("planning");
    expect(step.step_number).toBe(3);
    expect(step.context).toContain("organizing tasks");
    expect(step.thought).toContain("phase");
    expect(step.outcome).toContain("3 phases defined");
    expect(step.outcome).toContain("Phase 1: Setup");
    expect(step.outcome).toContain("2 tasks");
    expect(step.next_action).toBe(input.next_action);
    expect(step.rationale).toBe(input.rationale);
  });

  test("handles single phase", () => {
    const input: PhaseOrganizationInput = {
      step_number: 2,
      estimated_total: 3,
      phases: [
        {
          name: "Phase 1: All Tasks",
          tasks: ["Task A", "Task B"],
        },
      ],
      next_action: "Continue planning",
      rationale: "Simple enough for single phase",
    };

    const step = createPhaseOrganizationStep(input);

    expect(step.outcome).toContain("1 phase defined");
  });

  test("accepts optional phase descriptions", () => {
    const input: PhaseOrganizationInput = {
      step_number: 2,
      estimated_total: 4,
      phases: [
        {
          name: "Phase 1: Foundation",
          tasks: ["Task A"],
          description: "Set up the core infrastructure",
        },
      ],
      next_action: "Next",
      rationale: "Rationale",
    };

    const step = createPhaseOrganizationStep(input);

    expect(step.outcome).toContain("Set up the core infrastructure");
  });

  test("accepts optional parallel execution flag", () => {
    const input: PhaseOrganizationInput = {
      step_number: 2,
      estimated_total: 4,
      phases: [
        {
          name: "Phase 1",
          tasks: ["Task A", "Task B"],
          parallel: true,
        },
      ],
      next_action: "Next",
      rationale: "Rationale",
    };

    const step = createPhaseOrganizationStep(input);

    expect(step.outcome).toContain("parallel");
  });
});

describe("createDependencyTrackingStep", () => {
  test("creates dependency tracking step", () => {
    const input: DependencyTrackingInput = {
      step_number: 4,
      estimated_total: 5,
      dependencies: [
        { task: "Task B", depends_on: ["Task A"] },
        { task: "Task C", depends_on: ["Task A", "Task B"] },
      ],
      next_action: "Update plan.md with dependency annotations",
      rationale: "Dependencies ensure correct execution order",
    };

    const step = createDependencyTrackingStep(input);

    expect(step.purpose).toBe("planning");
    expect(step.step_number).toBe(4);
    expect(step.context).toContain("dependenc");
    expect(step.thought).toContain("track");
    expect(step.outcome).toContain("Task B");
    expect(step.outcome).toContain("depends on");
    expect(step.outcome).toContain("Task A");
    expect(step.next_action).toBe(input.next_action);
    expect(step.rationale).toBe(input.rationale);
  });

  test("handles no dependencies", () => {
    const input: DependencyTrackingInput = {
      step_number: 3,
      estimated_total: 4,
      dependencies: [],
      next_action: "Proceed with implementation",
      rationale: "All tasks are independent",
    };

    const step = createDependencyTrackingStep(input);

    expect(step.outcome).toContain("No task dependencies");
  });

  test("accepts optional blocked_by information", () => {
    const input: DependencyTrackingInput = {
      step_number: 4,
      estimated_total: 5,
      dependencies: [{ task: "Task B", depends_on: ["Task A"] }],
      blocked_by: [{ task: "Task C", reason: "Waiting for API design" }],
      next_action: "Resolve blockers",
      rationale: "Need to address blockers before proceeding",
    };

    const step = createDependencyTrackingStep(input);

    expect(step.outcome).toContain("Blocked");
    expect(step.outcome).toContain("Task C");
    expect(step.outcome).toContain("Waiting for API design");
  });

  test("accepts optional critical_path", () => {
    const input: DependencyTrackingInput = {
      step_number: 4,
      estimated_total: 5,
      dependencies: [{ task: "Task B", depends_on: ["Task A"] }],
      critical_path: ["Task A", "Task B", "Task C"],
      next_action: "Focus on critical path",
      rationale: "Critical path determines minimum completion time",
    };

    const step = createDependencyTrackingStep(input);

    expect(step.outcome).toContain("Critical path");
    expect(step.outcome).toContain("Task A");
  });
});

describe("updateTaskStatus", () => {
  test("updates task to pending status", () => {
    const update: TaskStatusUpdate = {
      task_id: "task-1",
      task_name: "Implement login",
      status: "pending",
    };

    const result = updateTaskStatus(update);

    expect(result.task_id).toBe("task-1");
    expect(result.task_name).toBe("Implement login");
    expect(result.status).toBe("pending");
    expect(result.marker).toBe("[ ]");
    expect(result.timestamp).toBeDefined();
  });

  test("updates task to in_progress status", () => {
    const result = updateTaskStatus({
      task_id: "task-2",
      task_name: "Add tests",
      status: "in_progress",
    });

    expect(result.status).toBe("in_progress");
    expect(result.marker).toBe("[~]");
  });

  test("updates task to completed status", () => {
    const result = updateTaskStatus({
      task_id: "task-3",
      task_name: "Deploy",
      status: "completed",
    });

    expect(result.status).toBe("completed");
    expect(result.marker).toBe("[x]");
  });

  test("updates task to blocked status", () => {
    const result = updateTaskStatus({
      task_id: "task-4",
      task_name: "Integration",
      status: "blocked",
      reason: "Waiting for API keys",
    });

    expect(result.status).toBe("blocked");
    expect(result.marker).toBe("[!]");
    expect(result.reason).toBe("Waiting for API keys");
  });

  test("updates task to skipped status", () => {
    const result = updateTaskStatus({
      task_id: "task-5",
      task_name: "Optional feature",
      status: "skipped",
      reason: "Out of scope for MVP",
    });

    expect(result.status).toBe("skipped");
    expect(result.marker).toBe("[-]");
    expect(result.reason).toBe("Out of scope for MVP");
  });

  test("accepts optional commit_sha for completed tasks", () => {
    const result = updateTaskStatus({
      task_id: "task-6",
      task_name: "Feature X",
      status: "completed",
      commit_sha: "abc123def",
    });

    expect(result.commit_sha).toBe("abc123def");
  });

  test("accepts optional beads_id", () => {
    const result = updateTaskStatus({
      task_id: "task-7",
      task_name: "Task Y",
      status: "pending",
      beads_id: "BD-789",
    });

    expect(result.beads_id).toBe("BD-789");
  });

  test("validates status is a known type", () => {
    const validStatuses: TaskStatus[] = [
      "pending",
      "in_progress",
      "completed",
      "blocked",
      "skipped",
    ];

    for (const status of validStatuses) {
      const result = updateTaskStatus({
        task_id: "test",
        task_name: "Test",
        status,
      });
      expect(result.status).toBe(status);
    }
  });
});

describe("integration scenarios", () => {
  test("complete planning workflow", () => {
    // Step 1: Initial plan step
    const step1 = createPlanStep({
      step_number: 1,
      estimated_total: 4,
      context: "Starting to plan user authentication feature",
      thought: "Need to analyze the PRD and break down into tasks",
      outcome: "Identified high-level areas: auth, user management, security",
      next_action: "Break down into specific tasks",
      rationale: "Understanding scope helps create accurate task list",
      flow_id: "user-auth_20260131",
    });

    expect(step1.purpose).toBe("planning");
    expect(step1.flow_id).toBe("user-auth_20260131");

    // Step 2: Task breakdown
    const step2 = createTaskBreakdownStep({
      step_number: 2,
      estimated_total: 4,
      prd_summary: "OAuth-based authentication with JWT tokens",
      identified_tasks: [
        "Configure OAuth providers",
        "Implement JWT token service",
        "Create login endpoint",
        "Create registration endpoint",
        "Add token refresh mechanism",
      ],
      priority_order: [
        "Configure OAuth providers",
        "Implement JWT token service",
        "Create login endpoint",
        "Create registration endpoint",
        "Add token refresh mechanism",
      ],
      next_action: "Organize into phases",
      rationale: "Core auth must be built before endpoints",
      flow_id: "user-auth_20260131",
    });

    expect(step2.purpose).toBe("planning");
    expect(step2.outcome).toContain("5 tasks identified");

    // Step 3: Phase organization
    const step3 = createPhaseOrganizationStep({
      step_number: 3,
      estimated_total: 4,
      phases: [
        {
          name: "Phase 1: Foundation",
          tasks: ["Configure OAuth providers", "Implement JWT token service"],
          description: "Set up core authentication infrastructure",
        },
        {
          name: "Phase 2: Endpoints",
          tasks: [
            "Create login endpoint",
            "Create registration endpoint",
            "Add token refresh mechanism",
          ],
          parallel: false,
        },
      ],
      next_action: "Document dependencies",
      rationale: "Foundation must be complete before implementing endpoints",
      flow_id: "user-auth_20260131",
    });

    expect(step3.purpose).toBe("planning");
    expect(step3.outcome).toContain("2 phases defined");

    // Step 4: Dependency tracking
    const step4 = createDependencyTrackingStep({
      step_number: 4,
      estimated_total: 4,
      dependencies: [
        { task: "Create login endpoint", depends_on: ["Implement JWT token service"] },
        { task: "Create registration endpoint", depends_on: ["Implement JWT token service"] },
        { task: "Add token refresh mechanism", depends_on: ["Create login endpoint"] },
      ],
      critical_path: [
        "Configure OAuth providers",
        "Implement JWT token service",
        "Create login endpoint",
        "Add token refresh mechanism",
      ],
      next_action: "Finalize plan.md and begin implementation",
      rationale: "All dependencies mapped, ready for TDD implementation",
      flow_id: "user-auth_20260131",
    });

    expect(step4.purpose).toBe("planning");
    expect(step4.outcome).toContain("Critical path");

    // Task status updates during implementation
    const taskUpdate = updateTaskStatus({
      task_id: "task-oauth",
      task_name: "Configure OAuth providers",
      status: "completed",
      commit_sha: "abc123",
      beads_id: "BD-101",
    });

    expect(taskUpdate.status).toBe("completed");
    expect(taskUpdate.marker).toBe("[x]");
    expect(taskUpdate.commit_sha).toBe("abc123");
  });
});
