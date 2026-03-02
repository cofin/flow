/**
 * Flow Think MCP - Research Hooks Unit Tests
 *
 * Tests for flow-research command integration hooks.
 */

import { describe, test, expect } from "bun:test";
import {
  createResearchStep,
  ResearchStepTemplates,
  ResearchHypothesisTracker,
  ResearchFileTracker,
  formatResearchFindings,
  summarizeResearchOutcomes,
  type ResearchStepInput,
  type ResearchHypothesis,
  type ResearchFinding,
  type ResearchOutcome,
} from "../src/flow/hooks/research.js";

describe("createResearchStep", () => {
  test("creates step with purpose set to 'research'", () => {
    const input: ResearchStepInput = {
      step_number: 1,
      estimated_total: 5,
      context: "Investigating authentication options",
      thought: "Need to compare OAuth providers",
      outcome: "Found 3 viable options",
      next_action: "Evaluate each option",
      rationale: "Must choose best fit for our needs",
    };

    const step = createResearchStep(input);

    expect(step.purpose).toBe("research");
    expect(step.step_number).toBe(1);
    expect(step.estimated_total).toBe(5);
    expect(step.context).toBe("Investigating authentication options");
  });

  test("allows hypothesis tracking", () => {
    const input: ResearchStepInput = {
      step_number: 2,
      estimated_total: 5,
      context: "Testing hypothesis",
      thought: "Checking if OAuth2 is the best choice",
      outcome: "Initial evidence supports hypothesis",
      next_action: "Gather more evidence",
      rationale: "Need stronger confirmation",
      hypothesis: "OAuth2 with PKCE is the most secure option",
      verification_status: "pending",
    };

    const step = createResearchStep(input);

    expect(step.hypothesis).toBe("OAuth2 with PKCE is the most secure option");
    expect(step.verification_status).toBe("pending");
  });

  test("allows file reference tracking", () => {
    const input: ResearchStepInput = {
      step_number: 1,
      estimated_total: 3,
      context: "Reviewing existing code",
      thought: "Need to understand current implementation",
      outcome: "Found authentication module",
      next_action: "Analyze module structure",
      rationale: "Understanding existing code before changes",
      files_referenced: ["/src/auth/oauth.ts", "/src/auth/session.ts"],
    };

    const step = createResearchStep(input);

    expect(step.files_referenced).toEqual(["/src/auth/oauth.ts", "/src/auth/session.ts"]);
  });

  test("supports patterns_discovered for research insights", () => {
    const input: ResearchStepInput = {
      step_number: 3,
      estimated_total: 5,
      context: "Analyzing codebase patterns",
      thought: "Found consistent patterns in auth module",
      outcome: "Identified repository pattern usage",
      next_action: "Document pattern for team",
      rationale: "Knowledge sharing",
      patterns_discovered: ["Repository pattern for data access", "Factory pattern for auth providers"],
    };

    const step = createResearchStep(input);

    expect(step.patterns_discovered).toHaveLength(2);
    expect(step.patterns_discovered).toContain("Repository pattern for data access");
  });

  test("preserves all FlowThinkStep fields", () => {
    const input: ResearchStepInput = {
      step_number: 1,
      estimated_total: 2,
      context: "Test",
      thought: "Testing",
      outcome: "Tested",
      next_action: "Next",
      rationale: "Reason",
      session_id: "session-123",
      flow_id: "auth-research_20260131",
      beads_task_id: "task-456",
      confidence: 0.75,
    };

    const step = createResearchStep(input);

    expect(step.session_id).toBe("session-123");
    expect(step.flow_id).toBe("auth-research_20260131");
    expect(step.beads_task_id).toBe("task-456");
    expect(step.confidence).toBe(0.75);
  });
});

describe("ResearchStepTemplates", () => {
  test("creates initial exploration step", () => {
    const step = ResearchStepTemplates.initialExploration({
      topic: "OAuth2 providers",
      questions: ["Which providers support PKCE?", "What are the pricing models?"],
    });

    expect(step.purpose).toBe("research");
    expect(step.context).toContain("OAuth2 providers");
    expect(step.thought).toContain("questions");
  });

  test("creates evidence gathering step", () => {
    const step = ResearchStepTemplates.gatherEvidence({
      hypothesis: "OAuth2 is the best choice",
      sources: ["Official docs", "Case studies"],
      step_number: 2,
      estimated_total: 5,
    });

    expect(step.purpose).toBe("research");
    expect(step.hypothesis).toBe("OAuth2 is the best choice");
    expect(step.verification_status).toBe("pending");
  });

  test("creates comparison analysis step", () => {
    const step = ResearchStepTemplates.compareOptions({
      options: ["Auth0", "Okta", "Firebase Auth"],
      criteria: ["pricing", "features", "ease of use"],
      step_number: 3,
      estimated_total: 5,
    });

    expect(step.purpose).toBe("research");
    expect(step.context).toContain("Auth0");
    expect(step.context).toContain("criteria");
  });

  test("creates conclusion step", () => {
    const step = ResearchStepTemplates.concludeResearch({
      summary: "OAuth2 with Auth0 is recommended",
      confidence: 0.85,
      recommendations: ["Use Auth0 for enterprise features", "Implement PKCE flow"],
      step_number: 5,
      estimated_total: 5,
    });

    expect(step.purpose).toBe("research");
    expect(step.is_final_step).toBe(true);
    expect(step.confidence).toBe(0.85);
    expect(step.outcome).toContain("Auth0");
  });
});

describe("ResearchHypothesisTracker", () => {
  test("tracks hypotheses across steps", () => {
    const tracker = new ResearchHypothesisTracker();

    tracker.addHypothesis({
      id: "h1",
      text: "OAuth2 is the best choice",
      status: "pending",
      step_introduced: 1,
    });

    const hypotheses = tracker.getAll();
    expect(hypotheses).toHaveLength(1);
    expect(hypotheses[0].text).toBe("OAuth2 is the best choice");
  });

  test("updates hypothesis status", () => {
    const tracker = new ResearchHypothesisTracker();

    tracker.addHypothesis({
      id: "h1",
      text: "OAuth2 is the best choice",
      status: "pending",
      step_introduced: 1,
    });

    tracker.updateStatus("h1", "confirmed", 3, "Evidence from benchmarks");

    const hypothesis = tracker.get("h1");
    expect(hypothesis?.status).toBe("confirmed");
    expect(hypothesis?.step_resolved).toBe(3);
    expect(hypothesis?.resolution_note).toBe("Evidence from benchmarks");
  });

  test("tracks hypothesis evidence", () => {
    const tracker = new ResearchHypothesisTracker();

    tracker.addHypothesis({
      id: "h1",
      text: "OAuth2 is secure",
      status: "pending",
      step_introduced: 1,
    });

    tracker.addEvidence("h1", {
      step_number: 2,
      supports: true,
      description: "PKCE prevents CSRF attacks",
    });

    tracker.addEvidence("h1", {
      step_number: 3,
      supports: false,
      description: "Legacy systems may not support it",
    });

    const hypothesis = tracker.get("h1");
    expect(hypothesis?.evidence).toHaveLength(2);
    expect(hypothesis?.evidence?.[0].supports).toBe(true);
    expect(hypothesis?.evidence?.[1].supports).toBe(false);
  });

  test("generates hypothesis summary", () => {
    const tracker = new ResearchHypothesisTracker();

    tracker.addHypothesis({
      id: "h1",
      text: "OAuth2 is the best choice",
      status: "confirmed",
      step_introduced: 1,
    });

    tracker.addHypothesis({
      id: "h2",
      text: "SAML is obsolete",
      status: "refuted",
      step_introduced: 2,
    });

    const summary = tracker.getSummary();

    expect(summary.total).toBe(2);
    expect(summary.confirmed).toBe(1);
    expect(summary.refuted).toBe(1);
    expect(summary.pending).toBe(0);
  });
});

describe("ResearchFileTracker", () => {
  test("tracks files referenced during research", () => {
    const tracker = new ResearchFileTracker();

    tracker.addReference("/src/auth/oauth.ts", 1, "Contains OAuth implementation");
    tracker.addReference("/src/auth/session.ts", 1, "Session management");
    tracker.addReference("/src/auth/oauth.ts", 2, "Revisited for token refresh");

    const files = tracker.getAll();
    expect(files).toHaveLength(2); // Unique files

    const oauthFile = tracker.get("/src/auth/oauth.ts");
    expect(oauthFile?.references).toHaveLength(2);
    expect(oauthFile?.first_seen_step).toBe(1);
    expect(oauthFile?.last_seen_step).toBe(2);
  });

  test("categorizes files by type", () => {
    const tracker = new ResearchFileTracker();

    tracker.addReference("/src/auth/oauth.ts", 1);
    tracker.addReference("/tests/auth.test.ts", 2);
    tracker.addReference("/docs/auth.md", 3);

    const byType = tracker.getByType();

    expect(byType.source).toContain("/src/auth/oauth.ts");
    expect(byType.test).toContain("/tests/auth.test.ts");
    expect(byType.documentation).toContain("/docs/auth.md");
  });

  test("generates file summary", () => {
    const tracker = new ResearchFileTracker();

    tracker.addReference("/src/auth/oauth.ts", 1);
    tracker.addReference("/src/auth/session.ts", 1);
    tracker.addReference("/tests/auth.test.ts", 2);

    const summary = tracker.getSummary();

    expect(summary.total_files).toBe(3);
    expect(summary.source_files).toBe(2);
    expect(summary.test_files).toBe(1);
  });
});

describe("formatResearchFindings", () => {
  test("formats findings as markdown", () => {
    const findings: ResearchFinding[] = [
      {
        id: "f1",
        category: "security",
        title: "OAuth2 PKCE Support",
        description: "All major providers support PKCE flow",
        step_number: 2,
        confidence: 0.9,
        sources: ["Auth0 docs", "Okta docs"],
      },
      {
        id: "f2",
        category: "performance",
        title: "Token Refresh Latency",
        description: "Average latency is 50ms",
        step_number: 3,
        confidence: 0.75,
      },
    ];

    const markdown = formatResearchFindings(findings, "markdown");

    expect(markdown).toContain("## Research Findings");
    expect(markdown).toContain("### security");
    expect(markdown).toContain("OAuth2 PKCE Support");
    expect(markdown).toContain("**Confidence:** 90%");
    expect(markdown).toContain("**Sources:**");
  });

  test("formats findings as JSON", () => {
    const findings: ResearchFinding[] = [
      {
        id: "f1",
        category: "security",
        title: "OAuth2 PKCE Support",
        description: "All major providers support PKCE flow",
        step_number: 2,
        confidence: 0.9,
      },
    ];

    const json = formatResearchFindings(findings, "json");
    const parsed = JSON.parse(json);

    expect(parsed.findings).toHaveLength(1);
    expect(parsed.findings[0].title).toBe("OAuth2 PKCE Support");
  });

  test("formats findings as plain text", () => {
    const findings: ResearchFinding[] = [
      {
        id: "f1",
        category: "security",
        title: "OAuth2 PKCE Support",
        description: "All major providers support PKCE flow",
        step_number: 2,
        confidence: 0.9,
      },
    ];

    const text = formatResearchFindings(findings, "text");

    expect(text).toContain("[security]");
    expect(text).toContain("OAuth2 PKCE Support");
  });

  test("groups findings by category", () => {
    const findings: ResearchFinding[] = [
      { id: "f1", category: "security", title: "Finding 1", description: "Desc 1", step_number: 1, confidence: 0.8 },
      { id: "f2", category: "security", title: "Finding 2", description: "Desc 2", step_number: 2, confidence: 0.7 },
      { id: "f3", category: "performance", title: "Finding 3", description: "Desc 3", step_number: 3, confidence: 0.9 },
    ];

    const markdown = formatResearchFindings(findings, "markdown");

    // Security section should have both findings
    const securitySection = markdown.split("### performance")[0];
    expect(securitySection).toContain("Finding 1");
    expect(securitySection).toContain("Finding 2");
  });
});

describe("summarizeResearchOutcomes", () => {
  test("summarizes research outcomes", () => {
    const outcomes: ResearchOutcome[] = [
      {
        question: "Which OAuth provider is best?",
        answer: "Auth0 for enterprise, Firebase for smaller projects",
        confidence: 0.85,
        evidence_steps: [1, 2, 3],
      },
      {
        question: "Is OAuth2 secure enough?",
        answer: "Yes, with PKCE flow",
        confidence: 0.95,
        evidence_steps: [2, 4],
      },
    ];

    const summary = summarizeResearchOutcomes(outcomes);

    expect(summary.total_questions).toBe(2);
    expect(summary.average_confidence).toBeCloseTo(0.9, 2);
    expect(summary.high_confidence_answers).toBe(2);
  });

  test("generates executive summary", () => {
    const outcomes: ResearchOutcome[] = [
      {
        question: "Which OAuth provider?",
        answer: "Auth0 recommended",
        confidence: 0.85,
        evidence_steps: [1, 2],
      },
    ];

    const summary = summarizeResearchOutcomes(outcomes);

    expect(summary.executive_summary).toContain("Auth0 recommended");
    expect(summary.executive_summary).toContain("85%");
  });

  test("identifies low confidence areas", () => {
    const outcomes: ResearchOutcome[] = [
      {
        question: "Which provider?",
        answer: "Auth0",
        confidence: 0.9,
        evidence_steps: [1],
      },
      {
        question: "What about costs?",
        answer: "Unclear pricing",
        confidence: 0.4,
        evidence_steps: [2],
      },
    ];

    const summary = summarizeResearchOutcomes(outcomes);

    expect(summary.low_confidence_areas).toHaveLength(1);
    expect(summary.low_confidence_areas[0]).toBe("What about costs?");
  });

  test("generates recommendations list", () => {
    const outcomes: ResearchOutcome[] = [
      {
        question: "Which provider?",
        answer: "Auth0 for production",
        confidence: 0.9,
        evidence_steps: [1, 2, 3],
        recommendations: ["Start with Auth0 free tier", "Plan for upgrade at 1000 users"],
      },
    ];

    const summary = summarizeResearchOutcomes(outcomes);

    expect(summary.all_recommendations).toHaveLength(2);
    expect(summary.all_recommendations).toContain("Start with Auth0 free tier");
  });
});
