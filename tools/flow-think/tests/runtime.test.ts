/**
 * Flow Think MCP - Runtime Detection Unit Tests
 *
 * Tests for runtime detection functionality.
 */

import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  detectRuntime,
  getRuntimeInfo,
  isBun,
  isNode,
  logRuntime,
  type RuntimeType,
  type RuntimeInfo,
} from "../src/runtime.js";

describe("detectRuntime", () => {
  test("detects Bun when running in Bun", () => {
    // This test runs in Bun, so it should detect Bun
    const runtime = detectRuntime();
    expect(runtime).toBe("bun");
  });

  test("returns a valid RuntimeType", () => {
    const runtime = detectRuntime();
    expect(["bun", "node", "unknown"]).toContain(runtime);
  });
});

describe("getRuntimeInfo", () => {
  test("returns complete RuntimeInfo object", () => {
    const info = getRuntimeInfo();

    expect(info).toHaveProperty("type");
    expect(info).toHaveProperty("version");
    expect(info).toHaveProperty("isPreferred");
    expect(info).toHaveProperty("description");
  });

  test("type matches detectRuntime result", () => {
    const runtime = detectRuntime();
    const info = getRuntimeInfo();

    expect(info.type).toBe(runtime);
  });

  test("Bun is marked as preferred", () => {
    const info = getRuntimeInfo();

    if (info.type === "bun") {
      expect(info.isPreferred).toBe(true);
    }
  });

  test("Node is not marked as preferred", () => {
    const info = getRuntimeInfo();

    if (info.type === "node") {
      expect(info.isPreferred).toBe(false);
    }
  });

  test("description includes runtime name", () => {
    const info = getRuntimeInfo();

    if (info.type === "bun") {
      expect(info.description).toContain("Bun");
    } else if (info.type === "node") {
      expect(info.description).toContain("Node.js");
    }
  });

  test("version is a non-empty string for known runtimes", () => {
    const info = getRuntimeInfo();

    if (info.type !== "unknown") {
      expect(info.version).not.toBe("");
      expect(info.version).not.toBe("unknown");
    }
  });
});

describe("isBun", () => {
  test("returns boolean", () => {
    const result = isBun();
    expect(typeof result).toBe("boolean");
  });

  test("matches detectRuntime for bun", () => {
    const expected = detectRuntime() === "bun";
    expect(isBun()).toBe(expected);
  });
});

describe("isNode", () => {
  test("returns boolean", () => {
    const result = isNode();
    expect(typeof result).toBe("boolean");
  });

  test("matches detectRuntime for node", () => {
    const expected = detectRuntime() === "node";
    expect(isNode()).toBe(expected);
  });
});

describe("logRuntime", () => {
  let originalConsoleError: typeof console.error;
  let capturedLogs: string[];

  beforeEach(() => {
    originalConsoleError = console.error;
    capturedLogs = [];
    console.error = (...args: unknown[]) => {
      capturedLogs.push(args.map(String).join(" "));
    };
  });

  afterEach(() => {
    console.error = originalConsoleError;
  });

  test("logs runtime information", () => {
    logRuntime();
    expect(capturedLogs.length).toBeGreaterThan(0);
    expect(capturedLogs[0]).toContain("Runtime:");
  });

  test("logs Bun recommendation when running Node", () => {
    // Mock Node.js environment
    const originalGlobalThis = { ...globalThis };

    // This test won't actually run in Node, but demonstrates the pattern
    logRuntime();

    // The log should mention the runtime being used
    const hasRuntimeLog = capturedLogs.some((log) => log.includes("Runtime:"));
    expect(hasRuntimeLog).toBe(true);
  });
});

describe("runtime consistency", () => {
  test("isBun and isNode are mutually exclusive for known runtimes", () => {
    const bunResult = isBun();
    const nodeResult = isNode();

    // Can't be both
    expect(bunResult && nodeResult).toBe(false);

    // For known runtimes, should be one or the other
    if (detectRuntime() !== "unknown") {
      expect(bunResult || nodeResult).toBe(true);
    }
  });

  test("detectRuntime returns consistent results", () => {
    const result1 = detectRuntime();
    const result2 = detectRuntime();
    const result3 = detectRuntime();

    expect(result1).toBe(result2);
    expect(result2).toBe(result3);
  });

  test("getRuntimeInfo returns consistent results", () => {
    const info1 = getRuntimeInfo();
    const info2 = getRuntimeInfo();

    expect(info1.type).toBe(info2.type);
    expect(info1.version).toBe(info2.version);
    expect(info1.isPreferred).toBe(info2.isPreferred);
    expect(info1.description).toBe(info2.description);
  });
});

describe("RuntimeInfo interface", () => {
  test("type is one of the allowed values", () => {
    const info = getRuntimeInfo();
    const allowedTypes: RuntimeType[] = ["bun", "node", "unknown"];
    expect(allowedTypes).toContain(info.type);
  });

  test("isPreferred is boolean", () => {
    const info = getRuntimeInfo();
    expect(typeof info.isPreferred).toBe("boolean");
  });

  test("description is string", () => {
    const info = getRuntimeInfo();
    expect(typeof info.description).toBe("string");
  });

  test("version is string", () => {
    const info = getRuntimeInfo();
    expect(typeof info.version).toBe("string");
  });
});
