/**
 * Flow Think MCP - PRD Integration Hooks Tests
 *
 * Tests for PRD-specific step templates and integration hooks.
 */

import { describe, test, expect } from "bun:test";
import {
  createPlanningStep,
  createChapterDecompositionStep,
  trackChapterProgress,
  generatePrdContext,
  PRD_PURPOSE,
  type PrdContext,
  type ChapterInfo,
  type ChapterProgress,
} from "../src/flow/hooks/prd.js";

describe("PRD_PURPOSE constant", () => {
  test("is set to 'planning'", () => {
    expect(PRD_PURPOSE).toBe("planning");
  });
});

describe("PrdContext type", () => {
  test("can create valid PRD context object", () => {
    const context: PrdContext = {
      prdTitle: "User Authentication System",
      prdPath: ".agent/specs/user-auth_20260131/spec.md",
      flowId: "user-auth_20260131",
      summary: "Implement secure user authentication with OAuth2",
    };

    expect(context.prdTitle).toBe("User Authentication System");
    expect(context.prdPath).toBe(".agent/specs/user-auth_20260131/spec.md");
    expect(context.flowId).toBe("user-auth_20260131");
    expect(context.summary).toBe("Implement secure user authentication with OAuth2");
  });

  test("allows optional beadsEpicId", () => {
    const context: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/to/spec.md",
      flowId: "feature_20260131",
      beadsEpicId: "epic-123",
    };

    expect(context.beadsEpicId).toBe("epic-123");
  });
});

describe("ChapterInfo type", () => {
  test("can create valid chapter info", () => {
    const chapter: ChapterInfo = {
      id: 1,
      title: "Project Setup",
      description: "Initialize project structure and dependencies",
      tasks: ["Create directory structure", "Initialize package.json", "Add TypeScript config"],
    };

    expect(chapter.id).toBe(1);
    expect(chapter.title).toBe("Project Setup");
    expect(chapter.tasks).toHaveLength(3);
  });

  test("supports optional estimatedTasks", () => {
    const chapter: ChapterInfo = {
      id: 1,
      title: "Implementation",
      description: "Core implementation",
      estimatedTasks: 5,
    };

    expect(chapter.estimatedTasks).toBe(5);
    expect(chapter.tasks).toBeUndefined();
  });
});

describe("generatePrdContext", () => {
  test("generates context string from PrdContext", () => {
    const prdContext: PrdContext = {
      prdTitle: "User Auth",
      prdPath: ".agent/specs/auth/spec.md",
      flowId: "auth_20260131",
      summary: "Implement authentication",
    };

    const result = generatePrdContext(prdContext);

    expect(result).toContain("PRD: User Auth");
    expect(result).toContain("Flow ID: auth_20260131");
    expect(result).toContain("Implement authentication");
  });

  test("includes Beads epic ID when present", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
      beadsEpicId: "epic-456",
    };

    const result = generatePrdContext(prdContext);

    expect(result).toContain("Beads Epic: epic-456");
  });

  test("omits Beads line when no epic ID", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const result = generatePrdContext(prdContext);

    expect(result).not.toContain("Beads");
  });
});

describe("createPlanningStep", () => {
  test("creates initial planning step with correct structure", () => {
    const prdContext: PrdContext = {
      prdTitle: "User Authentication",
      prdPath: ".agent/specs/auth/spec.md",
      flowId: "auth_20260131",
      summary: "Implement OAuth2 authentication",
    };

    const step = createPlanningStep(prdContext);

    expect(step.step_number).toBe(1);
    expect(step.purpose).toBe("planning");
    expect(step.context).toContain("PRD: User Authentication");
    expect(step.flow_id).toBe("auth_20260131");
  });

  test("sets estimated_total based on summary length heuristic", () => {
    const shortPrd: PrdContext = {
      prdTitle: "Small Feature",
      prdPath: "/path/spec.md",
      flowId: "small_20260131",
      summary: "Simple task",
    };

    const longPrd: PrdContext = {
      prdTitle: "Large Feature",
      prdPath: "/path/spec.md",
      flowId: "large_20260131",
      summary: "This is a comprehensive feature that requires multiple phases including research, design, implementation, testing, and documentation across several modules.",
    };

    const shortStep = createPlanningStep(shortPrd);
    const longStep = createPlanningStep(longPrd);

    expect(shortStep.estimated_total).toBeGreaterThanOrEqual(3);
    expect(longStep.estimated_total).toBeGreaterThan(shortStep.estimated_total);
  });

  test("includes thought about chapter decomposition", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
      summary: "Description",
    };

    const step = createPlanningStep(prdContext);

    expect(step.thought).toContain("chapter");
    expect(step.thought.toLowerCase()).toContain("breakdown");
  });

  test("next_action points to chapter decomposition", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const step = createPlanningStep(prdContext);

    expect(step.next_action).toContain("chapter");
  });

  test("includes beads_task_id when epic is provided", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
      beadsEpicId: "epic-789",
    };

    const step = createPlanningStep(prdContext);

    expect(step.beads_task_id).toBe("epic-789");
  });

  test("allows custom step_number override", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const step = createPlanningStep(prdContext, { stepNumber: 5 });

    expect(step.step_number).toBe(5);
  });
});

describe("createChapterDecompositionStep", () => {
  test("creates step for breaking PRD into chapters", () => {
    const prdContext: PrdContext = {
      prdTitle: "User Auth",
      prdPath: "/path/spec.md",
      flowId: "auth_20260131",
      summary: "Authentication system",
    };

    const chapters: ChapterInfo[] = [
      { id: 1, title: "Setup", description: "Project setup" },
      { id: 2, title: "Core Auth", description: "Authentication logic" },
      { id: 3, title: "Testing", description: "Test suite" },
    ];

    const step = createChapterDecompositionStep(prdContext, chapters, 2);

    expect(step.step_number).toBe(2);
    expect(step.purpose).toBe("planning");
    expect(step.thought).toContain("chapter");
  });

  test("lists chapters in context", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const chapters: ChapterInfo[] = [
      { id: 1, title: "Phase 1: Setup", description: "Initialize" },
      { id: 2, title: "Phase 2: Implement", description: "Build core" },
    ];

    const step = createChapterDecompositionStep(prdContext, chapters, 2);

    expect(step.context).toContain("Phase 1: Setup");
    expect(step.context).toContain("Phase 2: Implement");
  });

  test("includes chapter count in outcome", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const chapters: ChapterInfo[] = [
      { id: 1, title: "Ch1", description: "Desc" },
      { id: 2, title: "Ch2", description: "Desc" },
      { id: 3, title: "Ch3", description: "Desc" },
      { id: 4, title: "Ch4", description: "Desc" },
    ];

    const step = createChapterDecompositionStep(prdContext, chapters, 2);

    expect(step.outcome).toContain("4");
    expect(step.outcome.toLowerCase()).toContain("chapter");
  });

  test("sets flow_id from context", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "my-feature_20260131",
    };

    const step = createChapterDecompositionStep(prdContext, [], 2);

    expect(step.flow_id).toBe("my-feature_20260131");
  });
});

describe("ChapterProgress type", () => {
  test("can create valid progress object", () => {
    const progress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Setup",
      status: "in_progress",
      tasksCompleted: 3,
      tasksTotal: 5,
      startedAt: new Date().toISOString(),
    };

    expect(progress.chapterId).toBe(1);
    expect(progress.status).toBe("in_progress");
    expect(progress.tasksCompleted).toBe(3);
    expect(progress.tasksTotal).toBe(5);
  });

  test("supports all status values", () => {
    const statuses: ChapterProgress["status"][] = ["pending", "in_progress", "completed", "blocked"];

    for (const status of statuses) {
      const progress: ChapterProgress = {
        chapterId: 1,
        chapterTitle: "Test",
        status,
        tasksCompleted: 0,
        tasksTotal: 1,
      };
      expect(progress.status).toBe(status);
    }
  });

  test("supports optional completedAt", () => {
    const progress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Done",
      status: "completed",
      tasksCompleted: 5,
      tasksTotal: 5,
      startedAt: "2026-01-31T10:00:00Z",
      completedAt: "2026-01-31T12:00:00Z",
    };

    expect(progress.completedAt).toBe("2026-01-31T12:00:00Z");
  });
});

describe("trackChapterProgress", () => {
  test("creates progress tracking step", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const progress: ChapterProgress = {
      chapterId: 2,
      chapterTitle: "Implementation",
      status: "in_progress",
      tasksCompleted: 3,
      tasksTotal: 8,
    };

    const step = trackChapterProgress(prdContext, progress, 5);

    expect(step.step_number).toBe(5);
    expect(step.purpose).toBe("planning");
    expect(step.context).toContain("Chapter 2");
    expect(step.context).toContain("Implementation");
  });

  test("includes progress percentage in outcome", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const progress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Setup",
      status: "in_progress",
      tasksCompleted: 2,
      tasksTotal: 4,
    };

    const step = trackChapterProgress(prdContext, progress, 3);

    // 2/4 = 50%
    expect(step.outcome).toContain("50%");
  });

  test("marks completion when all tasks done", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const progress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Setup",
      status: "completed",
      tasksCompleted: 5,
      tasksTotal: 5,
    };

    const step = trackChapterProgress(prdContext, progress, 10);

    expect(step.outcome.toLowerCase()).toContain("complete");
  });

  test("indicates blocked status in thought", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    const progress: ChapterProgress = {
      chapterId: 2,
      chapterTitle: "Implementation",
      status: "blocked",
      tasksCompleted: 1,
      tasksTotal: 5,
      blockedReason: "Waiting for API access",
    };

    const step = trackChapterProgress(prdContext, progress, 7);

    expect(step.thought.toLowerCase()).toContain("blocked");
    expect(step.thought).toContain("Waiting for API access");
  });

  test("sets flow_id from context", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "tracked-feature_20260131",
    };

    const progress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Ch1",
      status: "pending",
      tasksCompleted: 0,
      tasksTotal: 3,
    };

    const step = trackChapterProgress(prdContext, progress, 2);

    expect(step.flow_id).toBe("tracked-feature_20260131");
  });

  test("calculates correct percentage for edge cases", () => {
    const prdContext: PrdContext = {
      prdTitle: "Feature",
      prdPath: "/path/spec.md",
      flowId: "feature_20260131",
    };

    // 0% case
    const zeroProgress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Start",
      status: "pending",
      tasksCompleted: 0,
      tasksTotal: 10,
    };
    const zeroStep = trackChapterProgress(prdContext, zeroProgress, 1);
    expect(zeroStep.outcome).toContain("0%");

    // 100% case
    const fullProgress: ChapterProgress = {
      chapterId: 1,
      chapterTitle: "Done",
      status: "completed",
      tasksCompleted: 10,
      tasksTotal: 10,
    };
    const fullStep = trackChapterProgress(prdContext, fullProgress, 2);
    expect(fullStep.outcome).toContain("100%");
  });
});
