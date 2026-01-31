/**
 * Flow Think MCP - Configuration Loading
 *
 * Loads configuration from environment variables with sensible defaults.
 */

import type { FlowThinkConfig, OutputFormat } from "./types.js";

/**
 * Default configuration values.
 */
const DEFAULTS = {
  outputFormat: "console" as OutputFormat,
  maxHistorySize: 100,
  sessionTimeout: 60, // minutes
  maxBranchDepth: 5,
  beadsSync: true,
  lowConfidenceThreshold: 0.5,
} as const;

/**
 * Valid output format values.
 */
const VALID_OUTPUT_FORMATS: OutputFormat[] = ["console", "json", "markdown"];

/**
 * Parse a boolean from environment variable.
 */
function parseEnvBool(value: string | undefined, defaultValue: boolean): boolean {
  if (value === undefined) return defaultValue;
  const lower = value.toLowerCase();
  return lower === "true" || lower === "1" || lower === "yes";
}

/**
 * Parse an integer from environment variable.
 */
function parseEnvInt(
  value: string | undefined,
  defaultValue: number,
  min?: number,
  max?: number
): number {
  if (value === undefined) return defaultValue;
  const parsed = parseInt(value, 10);
  if (isNaN(parsed)) return defaultValue;
  if (min !== undefined && parsed < min) return min;
  if (max !== undefined && parsed > max) return max;
  return parsed;
}

/**
 * Parse output format from environment variable.
 */
function parseOutputFormat(value: string | undefined): OutputFormat {
  if (value === undefined) return DEFAULTS.outputFormat;
  const lower = value.toLowerCase() as OutputFormat;
  if (VALID_OUTPUT_FORMATS.includes(lower)) {
    return lower;
  }
  console.error(
    `⚠️ Invalid FLOW_MCP_OUTPUT_FORMAT: "${value}". Using default: ${DEFAULTS.outputFormat}`
  );
  return DEFAULTS.outputFormat;
}

/**
 * Load configuration from environment variables.
 *
 * Environment variables:
 * - FLOW_MCP_OUTPUT_FORMAT: console | json | markdown (default: console)
 * - FLOW_MCP_MAX_HISTORY: number (default: 100)
 * - FLOW_MCP_SESSION_TIMEOUT: minutes (default: 60)
 * - FLOW_MCP_MAX_BRANCH_DEPTH: number (default: 5)
 * - FLOW_MCP_BEADS_SYNC: true | false (default: true)
 * - FLOW_MCP_LOW_CONFIDENCE: 0-1 (default: 0.5)
 */
export function loadConfig(): FlowThinkConfig {
  const env = process.env;

  const config: FlowThinkConfig = {
    outputFormat: parseOutputFormat(env.FLOW_MCP_OUTPUT_FORMAT),
    maxHistorySize: parseEnvInt(env.FLOW_MCP_MAX_HISTORY, DEFAULTS.maxHistorySize, 1, 10000),
    sessionTimeout: parseEnvInt(env.FLOW_MCP_SESSION_TIMEOUT, DEFAULTS.sessionTimeout, 1, 1440),
    maxBranchDepth: parseEnvInt(env.FLOW_MCP_MAX_BRANCH_DEPTH, DEFAULTS.maxBranchDepth, 1, 20),
    beadsSync: parseEnvBool(env.FLOW_MCP_BEADS_SYNC, DEFAULTS.beadsSync),
    lowConfidenceThreshold: parseEnvInt(
      env.FLOW_MCP_LOW_CONFIDENCE ? String(parseFloat(env.FLOW_MCP_LOW_CONFIDENCE) * 100) : undefined,
      DEFAULTS.lowConfidenceThreshold * 100,
      0,
      100
    ) / 100,
  };

  return config;
}

/**
 * Log configuration to stderr (for debugging).
 */
export function logConfig(config: FlowThinkConfig): void {
  console.error("📋 Configuration:");
  console.error(`   - Output Format: ${config.outputFormat}`);
  console.error(`   - Max History: ${config.maxHistorySize} steps`);
  console.error(`   - Session Timeout: ${config.sessionTimeout} min`);
  console.error(`   - Max Branch Depth: ${config.maxBranchDepth}`);
  console.error(`   - Beads Sync: ${config.beadsSync ? "Enabled" : "Disabled"}`);
  console.error(`   - Low Confidence Threshold: ${config.lowConfidenceThreshold}`);
}

/**
 * Get default configuration (for testing).
 */
export function getDefaultConfig(): FlowThinkConfig {
  return { ...DEFAULTS };
}
