/**
 * Flow Think MCP - Research Hooks
 *
 * Integration hooks for flow-research command.
 * Provides research-specific step templates, hypothesis tracking,
 * file reference tracking, and research output formatting.
 */

import type { FlowThinkStep, StructuredAction } from "../../types.js";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

/**
 * Input for creating a research step.
 * Omits 'purpose' since it's always 'research'.
 */
export interface ResearchStepInput {
  step_number: number;
  estimated_total: number;
  context: string;
  thought: string;
  outcome: string;
  next_action: string | StructuredAction;
  rationale: string;

  // Optional fields
  hypothesis?: string;
  verification_status?: "pending" | "confirmed" | "refuted";
  confidence?: number;
  uncertainty_notes?: string;
  files_referenced?: string[];
  patterns_discovered?: string[];
  session_id?: string;
  flow_id?: string;
  beads_task_id?: string;
  is_final_step?: boolean;
  tools_used?: string[];
  external_context?: Record<string, unknown>;
  dependencies?: number[];
  revises_step?: number;
  revision_reason?: string;
  branch_from?: number;
  branch_id?: string;
  branch_name?: string;
}

/**
 * A research hypothesis with tracking.
 */
export interface ResearchHypothesis {
  /** Unique identifier */
  id: string;
  /** The hypothesis text */
  text: string;
  /** Current status */
  status: "pending" | "confirmed" | "refuted";
  /** Step where hypothesis was introduced */
  step_introduced: number;
  /** Step where hypothesis was resolved (if any) */
  step_resolved?: number;
  /** Note explaining the resolution */
  resolution_note?: string;
  /** Evidence collected for this hypothesis */
  evidence?: HypothesisEvidence[];
}

/**
 * Evidence for or against a hypothesis.
 */
export interface HypothesisEvidence {
  /** Step number where evidence was found */
  step_number: number;
  /** Whether this evidence supports the hypothesis */
  supports: boolean;
  /** Description of the evidence */
  description: string;
}

/**
 * A file reference tracked during research.
 */
export interface FileReference {
  /** Absolute file path */
  path: string;
  /** First step where file was referenced */
  first_seen_step: number;
  /** Last step where file was referenced */
  last_seen_step: number;
  /** All references to this file */
  references: FileReferenceEntry[];
  /** File type category */
  type: "source" | "test" | "documentation" | "config" | "other";
}

/**
 * A single reference to a file.
 */
export interface FileReferenceEntry {
  /** Step number */
  step_number: number;
  /** Note about why file was referenced */
  note?: string;
}

/**
 * A research finding.
 */
export interface ResearchFinding {
  /** Unique identifier */
  id: string;
  /** Category of finding */
  category: string;
  /** Title of finding */
  title: string;
  /** Description of finding */
  description: string;
  /** Step number where finding was made */
  step_number: number;
  /** Confidence in finding (0-1) */
  confidence: number;
  /** Sources for this finding */
  sources?: string[];
}

/**
 * A research outcome answering a question.
 */
export interface ResearchOutcome {
  /** The question being answered */
  question: string;
  /** The answer */
  answer: string;
  /** Confidence in answer (0-1) */
  confidence: number;
  /** Step numbers that provided evidence */
  evidence_steps: number[];
  /** Recommendations based on this outcome */
  recommendations?: string[];
}

/**
 * Summary of research outcomes.
 */
export interface ResearchOutcomeSummary {
  /** Total questions answered */
  total_questions: number;
  /** Average confidence across all answers */
  average_confidence: number;
  /** Number of high confidence answers (>= 0.7) */
  high_confidence_answers: number;
  /** Questions with low confidence */
  low_confidence_areas: string[];
  /** All recommendations collected */
  all_recommendations: string[];
  /** Executive summary text */
  executive_summary: string;
}

// ─────────────────────────────────────────────────────────────
// Core Functions
// ─────────────────────────────────────────────────────────────

/**
 * Create a research step with purpose automatically set to 'research'.
 */
export function createResearchStep(input: ResearchStepInput): FlowThinkStep {
  return {
    ...input,
    purpose: "research",
  };
}

// ─────────────────────────────────────────────────────────────
// Research Step Templates
// ─────────────────────────────────────────────────────────────

/**
 * Templates for common research step patterns.
 */
export const ResearchStepTemplates = {
  /**
   * Create an initial exploration step.
   */
  initialExploration(params: {
    topic: string;
    questions: string[];
    step_number?: number;
    estimated_total?: number;
  }): FlowThinkStep {
    const questionsText = params.questions.map((q, i) => `${i + 1}. ${q}`).join("\n");
    return createResearchStep({
      step_number: params.step_number ?? 1,
      estimated_total: params.estimated_total ?? 5,
      context: `Beginning research on: ${params.topic}`,
      thought: `Need to investigate the following questions:\n${questionsText}`,
      outcome: "Research plan established",
      next_action: "Start gathering information",
      rationale: "Systematic exploration of the topic will yield best results",
    });
  },

  /**
   * Create an evidence gathering step.
   */
  gatherEvidence(params: {
    hypothesis: string;
    sources: string[];
    step_number: number;
    estimated_total: number;
  }): FlowThinkStep {
    const sourcesText = params.sources.join(", ");
    return createResearchStep({
      step_number: params.step_number,
      estimated_total: params.estimated_total,
      context: `Testing hypothesis: ${params.hypothesis}`,
      thought: `Gathering evidence from: ${sourcesText}`,
      outcome: "Evidence gathered for analysis",
      next_action: "Analyze the evidence",
      rationale: "Multiple sources provide stronger evidence",
      hypothesis: params.hypothesis,
      verification_status: "pending",
    });
  },

  /**
   * Create a comparison analysis step.
   */
  compareOptions(params: {
    options: string[];
    criteria: string[];
    step_number: number;
    estimated_total: number;
  }): FlowThinkStep {
    const optionsText = params.options.join(", ");
    const criteriaText = params.criteria.join(", ");
    return createResearchStep({
      step_number: params.step_number,
      estimated_total: params.estimated_total,
      context: `Comparing options: ${optionsText} using criteria: ${criteriaText}`,
      thought: "Systematic comparison will reveal the best option",
      outcome: "Comparison complete",
      next_action: "Summarize findings",
      rationale: "Structured comparison ensures fair evaluation",
    });
  },

  /**
   * Create a conclusion step.
   */
  concludeResearch(params: {
    summary: string;
    confidence: number;
    recommendations: string[];
    step_number: number;
    estimated_total: number;
  }): FlowThinkStep {
    const recsText = params.recommendations.map((r, i) => `${i + 1}. ${r}`).join("\n");
    return createResearchStep({
      step_number: params.step_number,
      estimated_total: params.estimated_total,
      context: "Research complete, drawing conclusions",
      thought: "Synthesizing all findings into actionable recommendations",
      outcome: `${params.summary}\n\nRecommendations:\n${recsText}`,
      next_action: "Document findings",
      rationale: "Clear conclusions enable informed decisions",
      confidence: params.confidence,
      is_final_step: true,
    });
  },
};

// ─────────────────────────────────────────────────────────────
// Hypothesis Tracker
// ─────────────────────────────────────────────────────────────

/**
 * Tracks hypotheses across research steps.
 */
export class ResearchHypothesisTracker {
  private hypotheses: Map<string, ResearchHypothesis> = new Map();

  /**
   * Add a new hypothesis.
   */
  addHypothesis(hypothesis: ResearchHypothesis): void {
    this.hypotheses.set(hypothesis.id, {
      ...hypothesis,
      evidence: hypothesis.evidence ?? [],
    });
  }

  /**
   * Get a hypothesis by ID.
   */
  get(id: string): ResearchHypothesis | undefined {
    return this.hypotheses.get(id);
  }

  /**
   * Get all hypotheses.
   */
  getAll(): ResearchHypothesis[] {
    return Array.from(this.hypotheses.values());
  }

  /**
   * Update hypothesis status.
   */
  updateStatus(
    id: string,
    status: "pending" | "confirmed" | "refuted",
    step_resolved?: number,
    resolution_note?: string
  ): void {
    const hypothesis = this.hypotheses.get(id);
    if (hypothesis) {
      hypothesis.status = status;
      if (step_resolved !== undefined) {
        hypothesis.step_resolved = step_resolved;
      }
      if (resolution_note !== undefined) {
        hypothesis.resolution_note = resolution_note;
      }
    }
  }

  /**
   * Add evidence for a hypothesis.
   */
  addEvidence(id: string, evidence: HypothesisEvidence): void {
    const hypothesis = this.hypotheses.get(id);
    if (hypothesis) {
      if (!hypothesis.evidence) {
        hypothesis.evidence = [];
      }
      hypothesis.evidence.push(evidence);
    }
  }

  /**
   * Get summary of all hypotheses.
   */
  getSummary(): { total: number; confirmed: number; refuted: number; pending: number } {
    let confirmed = 0;
    let refuted = 0;
    let pending = 0;

    for (const hypothesis of this.hypotheses.values()) {
      switch (hypothesis.status) {
        case "confirmed":
          confirmed++;
          break;
        case "refuted":
          refuted++;
          break;
        case "pending":
          pending++;
          break;
      }
    }

    return {
      total: this.hypotheses.size,
      confirmed,
      refuted,
      pending,
    };
  }
}

// ─────────────────────────────────────────────────────────────
// File Tracker
// ─────────────────────────────────────────────────────────────

/**
 * Tracks files referenced during research.
 */
export class ResearchFileTracker {
  private files: Map<string, FileReference> = new Map();

  /**
   * Determine file type from path.
   */
  private getFileType(path: string): FileReference["type"] {
    if (path.includes("/tests/") || path.includes(".test.") || path.includes(".spec.")) {
      return "test";
    }
    if (path.includes("/docs/") || path.endsWith(".md")) {
      return "documentation";
    }
    if (
      path.includes("config") ||
      path.endsWith(".json") ||
      path.endsWith(".yaml") ||
      path.endsWith(".yml") ||
      path.endsWith(".toml")
    ) {
      return "config";
    }
    if (
      path.endsWith(".ts") ||
      path.endsWith(".js") ||
      path.endsWith(".py") ||
      path.endsWith(".rs") ||
      path.endsWith(".go")
    ) {
      return "source";
    }
    return "other";
  }

  /**
   * Add a file reference.
   */
  addReference(path: string, step_number: number, note?: string): void {
    const existing = this.files.get(path);
    if (existing) {
      existing.last_seen_step = step_number;
      existing.references.push({ step_number, note });
    } else {
      this.files.set(path, {
        path,
        first_seen_step: step_number,
        last_seen_step: step_number,
        references: [{ step_number, note }],
        type: this.getFileType(path),
      });
    }
  }

  /**
   * Get a file reference by path.
   */
  get(path: string): FileReference | undefined {
    return this.files.get(path);
  }

  /**
   * Get all file references.
   */
  getAll(): FileReference[] {
    return Array.from(this.files.values());
  }

  /**
   * Get files grouped by type.
   */
  getByType(): Record<string, string[]> {
    const result: Record<string, string[]> = {
      source: [],
      test: [],
      documentation: [],
      config: [],
      other: [],
    };

    for (const file of this.files.values()) {
      result[file.type].push(file.path);
    }

    return result;
  }

  /**
   * Get summary of tracked files.
   */
  getSummary(): {
    total_files: number;
    source_files: number;
    test_files: number;
    documentation_files: number;
    config_files: number;
    other_files: number;
  } {
    const byType = this.getByType();
    return {
      total_files: this.files.size,
      source_files: byType.source.length,
      test_files: byType.test.length,
      documentation_files: byType.documentation.length,
      config_files: byType.config.length,
      other_files: byType.other.length,
    };
  }
}

// ─────────────────────────────────────────────────────────────
// Formatting Functions
// ─────────────────────────────────────────────────────────────

/**
 * Format research findings.
 */
export function formatResearchFindings(
  findings: ResearchFinding[],
  format: "markdown" | "json" | "text"
): string {
  switch (format) {
    case "json":
      return JSON.stringify({ findings }, null, 2);

    case "markdown":
      return formatFindingsMarkdown(findings);

    case "text":
      return formatFindingsText(findings);

    default:
      return formatFindingsMarkdown(findings);
  }
}

/**
 * Format findings as markdown.
 */
function formatFindingsMarkdown(findings: ResearchFinding[]): string {
  const lines: string[] = ["## Research Findings", ""];

  // Group by category
  const byCategory = new Map<string, ResearchFinding[]>();
  for (const finding of findings) {
    const existing = byCategory.get(finding.category) ?? [];
    existing.push(finding);
    byCategory.set(finding.category, existing);
  }

  // Output each category
  for (const [category, categoryFindings] of byCategory) {
    lines.push(`### ${category}`, "");

    for (const finding of categoryFindings) {
      lines.push(`#### ${finding.title}`);
      lines.push("");
      lines.push(finding.description);
      lines.push("");
      lines.push(`- **Confidence:** ${Math.round(finding.confidence * 100)}%`);
      lines.push(`- **Step:** ${finding.step_number}`);
      if (finding.sources && finding.sources.length > 0) {
        lines.push(`- **Sources:** ${finding.sources.join(", ")}`);
      }
      lines.push("");
    }
  }

  return lines.join("\n");
}

/**
 * Format findings as plain text.
 */
function formatFindingsText(findings: ResearchFinding[]): string {
  const lines: string[] = [];

  for (const finding of findings) {
    lines.push(`[${finding.category}] ${finding.title}`);
    lines.push(`  ${finding.description}`);
    lines.push(`  Confidence: ${Math.round(finding.confidence * 100)}%`);
    if (finding.sources && finding.sources.length > 0) {
      lines.push(`  Sources: ${finding.sources.join(", ")}`);
    }
    lines.push("");
  }

  return lines.join("\n");
}

// ─────────────────────────────────────────────────────────────
// Summary Functions
// ─────────────────────────────────────────────────────────────

/**
 * Summarize research outcomes.
 */
export function summarizeResearchOutcomes(outcomes: ResearchOutcome[]): ResearchOutcomeSummary {
  const total_questions = outcomes.length;

  // Calculate average confidence
  const totalConfidence = outcomes.reduce((sum, o) => sum + o.confidence, 0);
  const average_confidence = total_questions > 0 ? totalConfidence / total_questions : 0;

  // Count high confidence answers
  const high_confidence_answers = outcomes.filter((o) => o.confidence >= 0.7).length;

  // Find low confidence areas
  const low_confidence_areas = outcomes
    .filter((o) => o.confidence < 0.5)
    .map((o) => o.question);

  // Collect all recommendations
  const all_recommendations: string[] = [];
  for (const outcome of outcomes) {
    if (outcome.recommendations) {
      all_recommendations.push(...outcome.recommendations);
    }
  }

  // Generate executive summary
  const executive_summary = generateExecutiveSummary(outcomes);

  return {
    total_questions,
    average_confidence,
    high_confidence_answers,
    low_confidence_areas,
    all_recommendations,
    executive_summary,
  };
}

/**
 * Generate executive summary from outcomes.
 */
function generateExecutiveSummary(outcomes: ResearchOutcome[]): string {
  const lines: string[] = [];

  for (const outcome of outcomes) {
    const confidencePercent = Math.round(outcome.confidence * 100);
    lines.push(`Q: ${outcome.question}`);
    lines.push(`A: ${outcome.answer} (${confidencePercent}% confidence)`);
    lines.push("");
  }

  return lines.join("\n").trim();
}
