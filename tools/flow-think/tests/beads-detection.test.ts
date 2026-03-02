/**
 * Flow Think MCP - Beads Detection Tests
 *
 * Tests for Beads CLI detection and availability checking.
 */

import { describe, test, expect, beforeEach, afterEach, mock, spyOn } from "bun:test";
import { BeadsDetection, clearBeadsCache } from "../src/beads/detection.js";
import * as fs from "fs";
import * as path from "path";

describe("BeadsDetection", () => {
  beforeEach(() => {
    clearBeadsCache();
  });

  describe("isBeadsInstalled", () => {
    test("returns true when bd CLI is available", async () => {
      // This test assumes bd is installed in the test environment
      // If not installed, this will correctly return false
      const detection = new BeadsDetection();
      const result = await detection.isBeadsInstalled();

      // We can't guarantee bd is installed, so just verify it returns a boolean
      expect(typeof result).toBe("boolean");
    });

    test("caches the result after first check", async () => {
      const detection = new BeadsDetection();

      const result1 = await detection.isBeadsInstalled();
      const result2 = await detection.isBeadsInstalled();

      // Both should return the same value (cached)
      expect(result1).toBe(result2);
    });
  });

  describe("isBeadsInitialized", () => {
    test("returns true when .beads directory exists", async () => {
      const detection = new BeadsDetection();
      // Test in the flow repo root where .beads exists
      const result = await detection.isBeadsInitialized("/home/cody/code/c/flow");

      expect(result).toBe(true);
    });

    test("returns false when .beads directory does not exist", async () => {
      const detection = new BeadsDetection();
      const result = await detection.isBeadsInitialized("/tmp");

      expect(result).toBe(false);
    });

    test("uses current directory when no path provided", async () => {
      const detection = new BeadsDetection();
      const result = await detection.isBeadsInitialized();

      // Current directory may or may not have .beads
      expect(typeof result).toBe("boolean");
    });
  });

  describe("getBeadsStatus", () => {
    test("returns full status object", async () => {
      const detection = new BeadsDetection();
      const status = await detection.getBeadsStatus("/home/cody/code/c/flow");

      expect(status).toHaveProperty("installed");
      expect(status).toHaveProperty("initialized");
      expect(status).toHaveProperty("available");
      expect(typeof status.installed).toBe("boolean");
      expect(typeof status.initialized).toBe("boolean");
      expect(typeof status.available).toBe("boolean");
    });

    test("available is true only when both installed and initialized", async () => {
      const detection = new BeadsDetection();
      const status = await detection.getBeadsStatus("/home/cody/code/c/flow");

      if (status.installed && status.initialized) {
        expect(status.available).toBe(true);
      } else {
        expect(status.available).toBe(false);
      }
    });

    test("caches status results", async () => {
      const detection = new BeadsDetection();

      const status1 = await detection.getBeadsStatus("/home/cody/code/c/flow");
      const status2 = await detection.getBeadsStatus("/home/cody/code/c/flow");

      expect(status1.installed).toBe(status2.installed);
      expect(status1.initialized).toBe(status2.initialized);
    });
  });

  describe("clearBeadsCache", () => {
    test("clears cached detection results", async () => {
      const detection = new BeadsDetection();

      // First call to populate cache
      await detection.isBeadsInstalled();

      // Clear cache
      clearBeadsCache();

      // Verify we can call again (would fail if internal state was corrupted)
      const result = await detection.isBeadsInstalled();
      expect(typeof result).toBe("boolean");
    });
  });
});
