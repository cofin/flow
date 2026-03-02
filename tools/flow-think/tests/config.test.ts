/**
 * Flow Think MCP - Config Unit Tests
 *
 * Tests for configuration loading from environment variables.
 */

import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import { loadConfig, getDefaultConfig } from "../src/config.js";

describe("loadConfig", () => {
  const originalEnv = { ...process.env };

  afterEach(() => {
    // Restore original environment
    for (const key of Object.keys(process.env)) {
      if (key.startsWith("FLOW_MCP_")) {
        delete process.env[key];
      }
    }
    Object.assign(process.env, originalEnv);
  });

  test("returns defaults when no env vars set", () => {
    delete process.env.FLOW_MCP_OUTPUT_FORMAT;
    delete process.env.FLOW_MCP_MAX_HISTORY;

    const config = loadConfig();

    expect(config.outputFormat).toBe("console");
    expect(config.maxHistorySize).toBe(100);
    expect(config.sessionTimeout).toBe(60);
    expect(config.maxBranchDepth).toBe(5);
    expect(config.beadsSync).toBe(true);
    expect(config.lowConfidenceThreshold).toBe(0.5);
  });

  describe("FLOW_MCP_OUTPUT_FORMAT", () => {
    test("parses console format", () => {
      process.env.FLOW_MCP_OUTPUT_FORMAT = "console";
      expect(loadConfig().outputFormat).toBe("console");
    });

    test("parses json format", () => {
      process.env.FLOW_MCP_OUTPUT_FORMAT = "json";
      expect(loadConfig().outputFormat).toBe("json");
    });

    test("parses markdown format", () => {
      process.env.FLOW_MCP_OUTPUT_FORMAT = "markdown";
      expect(loadConfig().outputFormat).toBe("markdown");
    });

    test("parses case-insensitively", () => {
      process.env.FLOW_MCP_OUTPUT_FORMAT = "JSON";
      expect(loadConfig().outputFormat).toBe("json");
    });

    test("falls back to default for invalid format", () => {
      process.env.FLOW_MCP_OUTPUT_FORMAT = "invalid";
      expect(loadConfig().outputFormat).toBe("console");
    });
  });

  describe("FLOW_MCP_MAX_HISTORY", () => {
    test("parses valid integer", () => {
      process.env.FLOW_MCP_MAX_HISTORY = "50";
      expect(loadConfig().maxHistorySize).toBe(50);
    });

    test("clamps to minimum of 1", () => {
      process.env.FLOW_MCP_MAX_HISTORY = "0";
      expect(loadConfig().maxHistorySize).toBe(1);
    });

    test("clamps to maximum of 10000", () => {
      process.env.FLOW_MCP_MAX_HISTORY = "99999";
      expect(loadConfig().maxHistorySize).toBe(10000);
    });

    test("falls back to default for non-numeric", () => {
      process.env.FLOW_MCP_MAX_HISTORY = "abc";
      expect(loadConfig().maxHistorySize).toBe(100);
    });
  });

  describe("FLOW_MCP_SESSION_TIMEOUT", () => {
    test("parses valid timeout in minutes", () => {
      process.env.FLOW_MCP_SESSION_TIMEOUT = "120";
      expect(loadConfig().sessionTimeout).toBe(120);
    });

    test("clamps to minimum of 1", () => {
      process.env.FLOW_MCP_SESSION_TIMEOUT = "-5";
      expect(loadConfig().sessionTimeout).toBe(1);
    });

    test("clamps to maximum of 1440 (24 hours)", () => {
      process.env.FLOW_MCP_SESSION_TIMEOUT = "9999";
      expect(loadConfig().sessionTimeout).toBe(1440);
    });
  });

  describe("FLOW_MCP_MAX_BRANCH_DEPTH", () => {
    test("parses valid depth", () => {
      process.env.FLOW_MCP_MAX_BRANCH_DEPTH = "10";
      expect(loadConfig().maxBranchDepth).toBe(10);
    });

    test("clamps to minimum of 1", () => {
      process.env.FLOW_MCP_MAX_BRANCH_DEPTH = "0";
      expect(loadConfig().maxBranchDepth).toBe(1);
    });

    test("clamps to maximum of 20", () => {
      process.env.FLOW_MCP_MAX_BRANCH_DEPTH = "100";
      expect(loadConfig().maxBranchDepth).toBe(20);
    });
  });

  describe("FLOW_MCP_BEADS_SYNC", () => {
    test("parses true", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "true";
      expect(loadConfig().beadsSync).toBe(true);
    });

    test("parses false", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "false";
      expect(loadConfig().beadsSync).toBe(false);
    });

    test("parses 1 as true", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "1";
      expect(loadConfig().beadsSync).toBe(true);
    });

    test("parses 0 as false", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "0";
      expect(loadConfig().beadsSync).toBe(false);
    });

    test("parses yes as true", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "yes";
      expect(loadConfig().beadsSync).toBe(true);
    });

    test("is case-insensitive", () => {
      process.env.FLOW_MCP_BEADS_SYNC = "TRUE";
      expect(loadConfig().beadsSync).toBe(true);
    });
  });

  describe("FLOW_MCP_LOW_CONFIDENCE", () => {
    test("parses valid threshold", () => {
      process.env.FLOW_MCP_LOW_CONFIDENCE = "0.3";
      expect(loadConfig().lowConfidenceThreshold).toBe(0.3);
    });

    test("clamps to 0 minimum", () => {
      process.env.FLOW_MCP_LOW_CONFIDENCE = "-0.5";
      expect(loadConfig().lowConfidenceThreshold).toBe(0);
    });

    test("clamps to 1 maximum", () => {
      process.env.FLOW_MCP_LOW_CONFIDENCE = "1.5";
      expect(loadConfig().lowConfidenceThreshold).toBe(1);
    });
  });
});

describe("getDefaultConfig", () => {
  test("returns expected defaults", () => {
    const config = getDefaultConfig();

    expect(config.outputFormat).toBe("console");
    expect(config.maxHistorySize).toBe(100);
    expect(config.sessionTimeout).toBe(60);
    expect(config.maxBranchDepth).toBe(5);
    expect(config.beadsSync).toBe(true);
    expect(config.lowConfidenceThreshold).toBe(0.5);
  });

  test("returns new object each time", () => {
    const config1 = getDefaultConfig();
    const config2 = getDefaultConfig();

    expect(config1).not.toBe(config2);
    expect(config1).toEqual(config2);
  });
});
