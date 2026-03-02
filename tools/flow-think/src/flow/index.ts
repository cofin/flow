/**
 * Flow Think MCP - Flow Integration Module
 *
 * Re-exports all Flow-related functionality.
 */

export {
  PatternCapture,
  type PatternCategory,
  type CapturedPattern,
  type CaptureResult,
  type ElevationResult,
  type CaptureStats,
  type PatternCaptureOptions,
  PATTERN_CATEGORIES,
  formatPatternForLearnings,
  formatPatternForElevation,
  categorizePattern,
} from "./patterns.js";
