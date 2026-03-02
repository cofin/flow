/**
 * Flow Think MCP - Pattern Capture Integration
 *
 * Captures patterns discovered during reasoning and syncs to learnings.md.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { FlowThinkStep } from "../types.js";

/**
 * Pattern categories matching patterns.md sections.
 */
export type PatternCategory =
  | "code-conventions"
  | "architecture"
  | "gotchas"
  | "testing"
  | "context";

/**
 * All valid pattern category values.
 */
export const PATTERN_CATEGORIES: PatternCategory[] = [
  "code-conventions",
  "architecture",
  "gotchas",
  "testing",
  "context",
];

/**
 * A captured pattern with metadata.
 */
export interface CapturedPattern {
  /** The pattern text */
  text: string;
  /** Category for patterns.md sections */
  category: PatternCategory;
  /** Step number where pattern was discovered */
  source_step: number;
  /** When the pattern was captured */
  timestamp: string;
  /** Flow ID (track) this pattern came from */
  flow_id?: string;
  /** Files related to this pattern */
  files_related?: string[];
}

/**
 * Result of a pattern capture operation.
 */
export interface CaptureResult {
  /** Whether the capture succeeded */
  success: boolean;
  /** Number of patterns captured */
  captured_count: number;
  /** Whether learnings.md was updated */
  learnings_updated: boolean;
  /** Number of patterns elevated to patterns.md */
  elevated_count: number;
  /** Reason if capture was skipped or failed */
  reason?: string;
}

/**
 * Result of a pattern elevation operation.
 */
export interface ElevationResult {
  /** Whether the elevation succeeded */
  success: boolean;
  /** Reason if elevation failed */
  reason?: string;
}

/**
 * Statistics for pattern capture.
 */
export interface CaptureStats {
  /** Total patterns captured */
  total_captured: number;
  /** Patterns by category */
  by_category: Record<PatternCategory, number>;
  /** Patterns elevated to patterns.md */
  total_elevated: number;
  /** Last capture timestamp */
  last_capture_at?: string;
}

/**
 * Options for PatternCapture.
 */
export interface PatternCaptureOptions {
  /** Working directory (defaults to cwd) */
  workingDirectory?: string;
  /** Whether pattern capture is enabled */
  enabled?: boolean;
  /** Auto-elevate patterns on final step */
  autoElevate?: boolean;
}

/**
 * Keywords for categorizing patterns.
 * Order matters for overlapping keywords - more specific patterns checked first.
 */
const CATEGORY_KEYWORDS: Record<PatternCategory, string[]> = {
  "code-conventions": [
    "convention",
    "naming",
    "style",
    "import order",
    "camelcase",
    "snake_case",
    "format",
    "indent",
  ],
  architecture: [
    "service layer",
    "repository pattern",
    "layer handles",
    "module boundaries",
    "boundary",
    "domain model",
    "interface",
    "dependency injection",
  ],
  gotchas: [
    "watch out",
    "gotcha",
    "bug",
    "race condition",
    "edge case",
    "careful",
    "beware",
    "critical",
    "warning",
  ],
  testing: [
    "test",
    "mock",
    "fixture",
    "coverage",
    "unit test",
    "integration test",
    "assert",
    "expect",
  ],
  context: [
    "lives in",
    "located in",
    "located at",
    "file:",
    "path:",
    "directory",
    "is in",
  ],
};

/**
 * Categorize a pattern based on its text.
 *
 * @param text - The pattern text to categorize
 * @returns The inferred category
 */
export function categorizePattern(text: string): PatternCategory {
  const lower = text.toLowerCase();

  // Check each category's keywords (in priority order)
  // Check gotchas first since they may contain architecture keywords
  for (const keyword of CATEGORY_KEYWORDS["gotchas"]) {
    if (lower.includes(keyword)) {
      return "gotchas";
    }
  }

  // Check code conventions
  for (const keyword of CATEGORY_KEYWORDS["code-conventions"]) {
    if (lower.includes(keyword)) {
      return "code-conventions";
    }
  }

  // Check architecture
  for (const keyword of CATEGORY_KEYWORDS["architecture"]) {
    if (lower.includes(keyword)) {
      return "architecture";
    }
  }

  // Check testing
  for (const keyword of CATEGORY_KEYWORDS["testing"]) {
    if (lower.includes(keyword)) {
      return "testing";
    }
  }

  // Check context
  for (const keyword of CATEGORY_KEYWORDS["context"]) {
    if (lower.includes(keyword)) {
      return "context";
    }
  }

  // Default to context
  return "context";
}

/**
 * Format a pattern for learnings.md.
 *
 * @param pattern - The pattern to format
 * @returns Formatted markdown string
 */
export function formatPatternForLearnings(pattern: CapturedPattern): string {
  const lines: string[] = [];

  lines.push(`- **[${pattern.category}]** ${pattern.text}`);
  lines.push(`  - *Step ${pattern.source_step} at ${pattern.timestamp}*`);

  if (pattern.files_related && pattern.files_related.length > 0) {
    lines.push(`  - Files: ${pattern.files_related.join(", ")}`);
  }

  return lines.join("\n");
}

/**
 * Format a pattern for patterns.md elevation.
 *
 * @param pattern - The pattern to format
 * @returns Formatted markdown string
 */
export function formatPatternForElevation(pattern: CapturedPattern): string {
  const source = pattern.flow_id ? ` *(from ${pattern.flow_id})*` : "";
  return `- ${pattern.text}${source}`;
}

/**
 * Map category to patterns.md section header.
 */
const CATEGORY_TO_HEADER: Record<PatternCategory, string> = {
  "code-conventions": "## Code Conventions",
  architecture: "## Architecture",
  gotchas: "## Gotchas",
  testing: "## Testing",
  context: "## Context",
};

/**
 * Pattern capture service.
 *
 * Captures patterns discovered during reasoning and syncs to learnings.md.
 */
export class PatternCapture {
  private workingDirectory: string;
  private enabled: boolean;
  private autoElevate: boolean;

  // Statistics
  private stats: CaptureStats = {
    total_captured: 0,
    by_category: {
      "code-conventions": 0,
      architecture: 0,
      gotchas: 0,
      testing: 0,
      context: 0,
    },
    total_elevated: 0,
  };

  constructor(options: PatternCaptureOptions = {}) {
    this.workingDirectory = options.workingDirectory ?? process.cwd();
    this.enabled = options.enabled ?? true;
    this.autoElevate = options.autoElevate ?? false;
  }

  /**
   * Extract patterns from a step.
   *
   * @param step - The step to extract patterns from
   * @returns Array of captured patterns
   */
  extractPatterns(step: FlowThinkStep): CapturedPattern[] {
    if (!step.patterns_discovered || step.patterns_discovered.length === 0) {
      return [];
    }

    const timestamp = step.timestamp ?? new Date().toISOString();

    return step.patterns_discovered.map((text) => ({
      text,
      category: categorizePattern(text),
      source_step: step.step_number,
      timestamp,
      flow_id: step.flow_id,
      files_related: step.files_referenced,
    }));
  }

  /**
   * Capture patterns from a step and write to learnings.md.
   *
   * @param step - The step to capture patterns from
   * @returns Result of the capture operation
   */
  async captureFromStep(step: FlowThinkStep): Promise<CaptureResult> {
    // Check if disabled
    if (!this.enabled) {
      return {
        success: true,
        captured_count: 0,
        learnings_updated: false,
        elevated_count: 0,
        reason: "Pattern capture disabled",
      };
    }

    // Extract patterns
    const patterns = this.extractPatterns(step);

    if (patterns.length === 0) {
      return {
        success: true,
        captured_count: 0,
        learnings_updated: false,
        elevated_count: 0,
        reason: "No patterns to capture",
      };
    }

    // Update stats
    for (const pattern of patterns) {
      this.stats.total_captured++;
      this.stats.by_category[pattern.category]++;
    }
    this.stats.last_capture_at = new Date().toISOString();

    // Try to write to learnings.md
    let learningsUpdated = false;
    let reason: string | undefined;

    if (!step.flow_id) {
      reason = "No flow_id provided - patterns captured but not written to learnings.md";
    } else {
      try {
        learningsUpdated = await this.appendToLearnings(step.flow_id, patterns);
      } catch (error) {
        reason = `Failed to update learnings.md: ${error instanceof Error ? error.message : String(error)}`;
      }
    }

    // Auto-elevate on final step if enabled
    let elevatedCount = 0;
    if (this.autoElevate && step.is_final_step) {
      for (const pattern of patterns) {
        try {
          const result = await this.elevatePattern(pattern);
          if (result.success) {
            elevatedCount++;
            this.stats.total_elevated++;
          }
        } catch {
          // Continue with other patterns
        }
      }
    }

    return {
      success: true,
      captured_count: patterns.length,
      learnings_updated: learningsUpdated,
      elevated_count: elevatedCount,
      reason,
    };
  }

  /**
   * Append patterns to learnings.md for a flow.
   *
   * @param flowId - The flow ID
   * @param patterns - Patterns to append
   * @returns Whether the file was updated
   */
  private async appendToLearnings(
    flowId: string,
    patterns: CapturedPattern[]
  ): Promise<boolean> {
    const specDir = path.join(this.workingDirectory, ".agent", "specs", flowId);
    const learningsPath = path.join(specDir, "learnings.md");

    // Check if .agent directory exists
    const agentDir = path.join(this.workingDirectory, ".agent");
    if (!fs.existsSync(agentDir)) {
      console.error("No .agent directory found - cannot write learnings");
      return false;
    }

    // Create spec directory if needed
    if (!fs.existsSync(specDir)) {
      fs.mkdirSync(specDir, { recursive: true });
    }

    // Read existing content or create new
    let content: string;
    if (fs.existsSync(learningsPath)) {
      content = fs.readFileSync(learningsPath, "utf-8");
    } else {
      content = "# Track Learnings\n\n---\n\n";
    }

    // Format patterns
    const timestamp = new Date().toISOString().split("T")[0];
    const header = `\n## [${timestamp}] - Patterns from Step ${patterns[0].source_step}\n\n`;
    const formatted = patterns.map(formatPatternForLearnings).join("\n\n");

    // Append to file
    const newContent = content + header + formatted + "\n";
    fs.writeFileSync(learningsPath, newContent, "utf-8");

    console.error(`Captured ${patterns.length} pattern(s) to ${learningsPath}`);
    return true;
  }

  /**
   * Elevate a pattern to patterns.md.
   *
   * @param pattern - The pattern to elevate
   * @returns Result of the elevation
   */
  async elevatePattern(pattern: CapturedPattern): Promise<ElevationResult> {
    const patternsPath = path.join(this.workingDirectory, ".agent", "patterns.md");

    // Check if patterns.md exists
    if (!fs.existsSync(patternsPath)) {
      return {
        success: false,
        reason: "patterns.md not found",
      };
    }

    // Read existing content
    let content = fs.readFileSync(patternsPath, "utf-8");

    // Find the section for this category
    const header = CATEGORY_TO_HEADER[pattern.category];
    const formatted = formatPatternForElevation(pattern);

    // Find the section and append
    const headerIndex = content.indexOf(header);
    if (headerIndex === -1) {
      return {
        success: false,
        reason: `Section ${header} not found in patterns.md`,
      };
    }

    // Find the next section or end of file
    const nextSectionMatch = content.slice(headerIndex + header.length).match(/\n## /);
    const insertPosition = nextSectionMatch
      ? headerIndex + header.length + (nextSectionMatch.index ?? 0)
      : content.length;

    // Insert the pattern
    const before = content.slice(0, insertPosition);
    const after = content.slice(insertPosition);

    // Add newline if needed
    const needsNewline = !before.endsWith("\n\n");
    const newContent = before + (needsNewline ? "\n" : "") + formatted + "\n" + after;

    fs.writeFileSync(patternsPath, newContent, "utf-8");

    console.error(`Elevated pattern to ${patternsPath}: ${pattern.text.slice(0, 50)}...`);
    return { success: true };
  }

  /**
   * Get capture statistics.
   */
  getStats(): CaptureStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics.
   */
  resetStats(): void {
    this.stats = {
      total_captured: 0,
      by_category: {
        "code-conventions": 0,
        architecture: 0,
        gotchas: 0,
        testing: 0,
        context: 0,
      },
      total_elevated: 0,
    };
  }
}
