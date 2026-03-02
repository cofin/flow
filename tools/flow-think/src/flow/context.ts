/**
 * Flow Think MCP - Flow Context Loading
 *
 * Functionality to load Flow context from .agent/ directory.
 * Provides access to specs, plans, patterns, workflow, and metadata.
 */

import { existsSync, readFileSync } from "fs";
import { join } from "path";

/**
 * Flow status markers used in flows.md and plan.md.
 */
export type FlowStatus = "pending" | "in_progress" | "completed" | "blocked" | "skipped";

/**
 * Flow specification loaded from spec.md or prd.md.
 */
export interface FlowSpec {
  /** Flow identifier */
  flow_id: string;
  /** Full content of the spec file */
  content: string;
  /** Path to the spec file */
  file_path: string;
}

/**
 * Flow plan loaded from plan.md.
 */
export interface FlowPlan {
  /** Flow identifier */
  flow_id: string;
  /** Full content of the plan file */
  content: string;
  /** Path to the plan file */
  file_path: string;
}

/**
 * Metadata from metadata.json in a flow's spec directory.
 */
export interface FlowMetadata {
  /** PRD/Flow identifier */
  prd_id: string;
  /** Type of flow (saga, flow, etc.) */
  type: string;
  /** Current status */
  status: string;
  /** Beads epic ID for tracking */
  beads_epic_id?: string;
  /** Creation timestamp */
  created_at: string;
  /** Last update timestamp */
  updated_at: string;
  /** Description of the flow */
  description: string;
  /** Chapters if this is a saga/PRD */
  chapters?: Array<{
    id: string;
    name: string;
    status: string;
    beads_id: string;
    dependencies: string[];
  }>;
}

/**
 * Complete Flow context loaded from .agent/ directory.
 */
export interface FlowContext {
  /** Flow identifier */
  flow_id: string;
  /** Project root directory */
  project_root: string;
  /** Loaded specification (spec.md or prd.md) */
  spec: FlowSpec | null;
  /** Loaded plan (plan.md) */
  plan: FlowPlan | null;
  /** Patterns content from patterns.md */
  patterns: string | null;
  /** Workflow content from workflow.md */
  workflow: string | null;
  /** Metadata from metadata.json */
  metadata: FlowMetadata | null;
}

/**
 * Detected flow from flows.md registry.
 */
export interface DetectedFlow {
  /** Flow identifier */
  flow_id: string;
  /** Flow name/title */
  name: string;
  /** Current status */
  status: FlowStatus;
  /** Path to flow directory */
  path: string;
  /** Associated Beads ID */
  beads_id?: string;
}

/**
 * Cache for loaded content.
 */
const flowsRegistryCache: Map<string, string | null> = new Map();
const specCache: Map<string, FlowSpec | null> = new Map();
const planCache: Map<string, FlowPlan | null> = new Map();
const metadataCache: Map<string, FlowMetadata | null> = new Map();
let patternsCache: Map<string, string | null> = new Map();
let workflowCache: Map<string, string | null> = new Map();

/**
 * Clear all cached Flow context data.
 * Useful for testing or when .agent/ directory changes.
 */
export function clearFlowContextCache(): void {
  flowsRegistryCache.clear();
  specCache.clear();
  planCache.clear();
  metadataCache.clear();
  patternsCache.clear();
  workflowCache.clear();
}

/**
 * Flow context loader service.
 *
 * Provides methods to load Flow context from .agent/ directory,
 * including specs, plans, patterns, workflow, and metadata.
 */
export class FlowContextLoader {
  private projectRoot: string;

  /**
   * Create a new FlowContextLoader.
   *
   * @param directory - Project root directory (defaults to cwd)
   */
  constructor(directory?: string) {
    this.projectRoot = directory ?? process.cwd();
  }

  /**
   * Get the project root directory.
   */
  getProjectRoot(): string {
    return this.projectRoot;
  }

  /**
   * Get the .agent directory path.
   */
  private getAgentPath(): string {
    return join(this.projectRoot, ".agent");
  }

  /**
   * Get the specs directory path.
   */
  private getSpecsPath(): string {
    return join(this.getAgentPath(), "specs");
  }

  /**
   * Check if .agent directory exists.
   */
  async hasAgentDirectory(): Promise<boolean> {
    return existsSync(this.getAgentPath());
  }

  /**
   * Load the flows.md registry file.
   *
   * @returns Content of flows.md or null if not found
   */
  async loadFlowsRegistry(): Promise<string | null> {
    const cacheKey = this.projectRoot;
    if (flowsRegistryCache.has(cacheKey)) {
      return flowsRegistryCache.get(cacheKey)!;
    }

    const flowsPath = join(this.getAgentPath(), "flows.md");
    if (!existsSync(flowsPath)) {
      flowsRegistryCache.set(cacheKey, null);
      return null;
    }

    try {
      const content = readFileSync(flowsPath, "utf-8");
      flowsRegistryCache.set(cacheKey, content);
      return content;
    } catch {
      flowsRegistryCache.set(cacheKey, null);
      return null;
    }
  }

  /**
   * Parse flow status marker to FlowStatus type.
   *
   * @param marker - Status marker from markdown (e.g., "[ ]", "[~]")
   * @returns Corresponding FlowStatus
   */
  parseFlowStatus(marker: string): FlowStatus {
    switch (marker) {
      case "[ ]":
        return "pending";
      case "[~]":
        return "in_progress";
      case "[x]":
        return "completed";
      case "[!]":
        return "blocked";
      case "[-]":
        return "skipped";
      default:
        return "pending";
    }
  }

  /**
   * Detect active flows from the flows.md registry.
   *
   * @returns Array of detected flows
   */
  async detectCurrentFlow(): Promise<DetectedFlow[]> {
    const registry = await this.loadFlowsRegistry();
    if (!registry) {
      return [];
    }

    const flows: DetectedFlow[] = [];

    // Parse flow entries from flows.md
    // Format: ### [status] Flow: Name
    // *Link: [./specs/flow_id/](./specs/flow_id/)*
    // *Beads: beads_id*
    const flowPattern = /###\s+(\[[ x~!-]\])\s+(?:Flow|PRD):\s+(.+)\n\*Link:\s+\[\.\/specs\/([^/]+)\//g;
    const beadsPattern = /\*Beads:\s+(\S+)\*/;

    let match;
    while ((match = flowPattern.exec(registry)) !== null) {
      const [_fullMatch, statusMarker, name, flowId] = match;
      const status = this.parseFlowStatus(statusMarker);

      // Look for Beads ID after the match
      const afterMatch = registry.slice(match.index, match.index + 500);
      const beadsMatch = beadsPattern.exec(afterMatch);

      flows.push({
        flow_id: flowId,
        name: name.trim(),
        status,
        path: join(this.getSpecsPath(), flowId),
        beads_id: beadsMatch ? beadsMatch[1] : undefined,
      });
    }

    return flows;
  }

  /**
   * Load the spec/prd.md for a flow.
   *
   * Tries both spec.md and prd.md (Flow uses prd.md for sagas).
   *
   * @param flowId - Flow identifier
   * @returns FlowSpec or null if not found
   */
  async loadSpec(flowId: string): Promise<FlowSpec | null> {
    const cacheKey = `${this.projectRoot}:${flowId}`;
    if (specCache.has(cacheKey)) {
      return specCache.get(cacheKey)!;
    }

    const flowDir = join(this.getSpecsPath(), flowId);
    if (!existsSync(flowDir)) {
      specCache.set(cacheKey, null);
      return null;
    }

    // Try spec.md first, then prd.md
    const specFiles = ["spec.md", "prd.md"];
    for (const filename of specFiles) {
      const specPath = join(flowDir, filename);
      if (existsSync(specPath)) {
        try {
          const content = readFileSync(specPath, "utf-8");
          const spec: FlowSpec = {
            flow_id: flowId,
            content,
            file_path: specPath,
          };
          specCache.set(cacheKey, spec);
          return spec;
        } catch {
          // Continue to next file
        }
      }
    }

    specCache.set(cacheKey, null);
    return null;
  }

  /**
   * Load the plan.md for a flow.
   *
   * @param flowId - Flow identifier
   * @returns FlowPlan or null if not found
   */
  async loadPlan(flowId: string): Promise<FlowPlan | null> {
    const cacheKey = `${this.projectRoot}:${flowId}`;
    if (planCache.has(cacheKey)) {
      return planCache.get(cacheKey)!;
    }

    const planPath = join(this.getSpecsPath(), flowId, "plan.md");
    if (!existsSync(planPath)) {
      planCache.set(cacheKey, null);
      return null;
    }

    try {
      const content = readFileSync(planPath, "utf-8");
      const plan: FlowPlan = {
        flow_id: flowId,
        content,
        file_path: planPath,
      };
      planCache.set(cacheKey, plan);
      return plan;
    } catch {
      planCache.set(cacheKey, null);
      return null;
    }
  }

  /**
   * Load the project-level patterns.md.
   *
   * @returns Patterns content or null if not found
   */
  async loadPatterns(): Promise<string | null> {
    const cacheKey = this.projectRoot;
    if (patternsCache.has(cacheKey)) {
      return patternsCache.get(cacheKey)!;
    }

    const patternsPath = join(this.getAgentPath(), "patterns.md");
    if (!existsSync(patternsPath)) {
      patternsCache.set(cacheKey, null);
      return null;
    }

    try {
      const content = readFileSync(patternsPath, "utf-8");
      patternsCache.set(cacheKey, content);
      return content;
    } catch {
      patternsCache.set(cacheKey, null);
      return null;
    }
  }

  /**
   * Load the project-level workflow.md.
   *
   * @returns Workflow content or null if not found
   */
  async loadWorkflow(): Promise<string | null> {
    const cacheKey = this.projectRoot;
    if (workflowCache.has(cacheKey)) {
      return workflowCache.get(cacheKey)!;
    }

    const workflowPath = join(this.getAgentPath(), "workflow.md");
    if (!existsSync(workflowPath)) {
      workflowCache.set(cacheKey, null);
      return null;
    }

    try {
      const content = readFileSync(workflowPath, "utf-8");
      workflowCache.set(cacheKey, content);
      return content;
    } catch {
      workflowCache.set(cacheKey, null);
      return null;
    }
  }

  /**
   * Load metadata.json for a flow.
   *
   * @param flowId - Flow identifier
   * @returns FlowMetadata or null if not found
   */
  async loadMetadata(flowId: string): Promise<FlowMetadata | null> {
    const cacheKey = `${this.projectRoot}:${flowId}`;
    if (metadataCache.has(cacheKey)) {
      return metadataCache.get(cacheKey)!;
    }

    const metadataPath = join(this.getSpecsPath(), flowId, "metadata.json");
    if (!existsSync(metadataPath)) {
      metadataCache.set(cacheKey, null);
      return null;
    }

    try {
      const content = readFileSync(metadataPath, "utf-8");
      const metadata = JSON.parse(content) as FlowMetadata;
      metadataCache.set(cacheKey, metadata);
      return metadata;
    } catch {
      metadataCache.set(cacheKey, null);
      return null;
    }
  }

  /**
   * Get complete Flow context for a flow.
   *
   * Loads spec, plan, patterns, workflow, and metadata.
   *
   * @param flowId - Flow identifier
   * @returns FlowContext or null if flow doesn't exist
   */
  async getFullContext(flowId: string): Promise<FlowContext | null> {
    // Check if flow directory exists
    const flowDir = join(this.getSpecsPath(), flowId);
    if (!existsSync(flowDir)) {
      return null;
    }

    // Load all components in parallel
    const [spec, plan, patterns, workflow, metadata] = await Promise.all([
      this.loadSpec(flowId),
      this.loadPlan(flowId),
      this.loadPatterns(),
      this.loadWorkflow(),
      this.loadMetadata(flowId),
    ]);

    // If neither spec nor metadata exists, the flow doesn't really exist
    if (!spec && !metadata) {
      return null;
    }

    return {
      flow_id: flowId,
      project_root: this.projectRoot,
      spec,
      plan,
      patterns,
      workflow,
      metadata,
    };
  }

  /**
   * Get summary of Flow context for logging.
   *
   * @param flowId - Flow identifier
   * @returns Summary string
   */
  async getContextSummary(flowId: string): Promise<string> {
    const context = await this.getFullContext(flowId);
    if (!context) {
      return `Flow '${flowId}' not found`;
    }

    const lines: string[] = [];
    lines.push(`Flow: ${flowId}`);

    if (context.metadata) {
      lines.push(`  Type: ${context.metadata.type}`);
      lines.push(`  Status: ${context.metadata.status}`);
      if (context.metadata.beads_epic_id) {
        lines.push(`  Beads: ${context.metadata.beads_epic_id}`);
      }
    }

    if (context.spec) {
      lines.push(`  Spec: ${context.spec.file_path}`);
    }

    if (context.plan) {
      lines.push(`  Plan: ${context.plan.file_path}`);
    }

    if (context.patterns) {
      lines.push(`  Patterns: loaded`);
    }

    if (context.workflow) {
      lines.push(`  Workflow: loaded`);
    }

    return lines.join("\n");
  }
}
