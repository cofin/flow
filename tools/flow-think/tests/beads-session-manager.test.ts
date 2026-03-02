/**
 * Flow Think MCP - Beads Session Manager Tests
 *
 * Tests for session-to-epic mapping.
 */

import { describe, test, expect, beforeEach } from "bun:test";
import { BeadsSessionManager } from "../src/beads/session-manager.js";
import { clearBeadsCache } from "../src/beads/detection.js";

describe("BeadsSessionManager", () => {
  let manager: BeadsSessionManager;

  beforeEach(() => {
    clearBeadsCache();
    manager = new BeadsSessionManager();
  });

  describe("registerMapping", () => {
    test("creates new mapping", () => {
      const mapping = manager.registerMapping("session-1", "epic-123");

      expect(mapping.session_id).toBe("session-1");
      expect(mapping.epic_id).toBe("epic-123");
      expect(mapping.synced_count).toBe(0);
      expect(mapping.created_at).toBeDefined();
    });

    test("updates existing mapping", () => {
      manager.registerMapping("session-1", "epic-123");
      const updated = manager.registerMapping("session-1", "epic-456");

      expect(updated.epic_id).toBe("epic-456");
      expect(manager.getEpicForSession("session-1")).toBe("epic-456");
    });
  });

  describe("getEpicForSession", () => {
    test("returns epic ID for registered session", () => {
      manager.registerMapping("session-1", "epic-123");

      expect(manager.getEpicForSession("session-1")).toBe("epic-123");
    });

    test("returns undefined for unknown session", () => {
      expect(manager.getEpicForSession("unknown")).toBeUndefined();
    });
  });

  describe("getMapping", () => {
    test("returns full mapping object", () => {
      manager.registerMapping("session-1", "epic-123");
      const mapping = manager.getMapping("session-1");

      expect(mapping).toBeDefined();
      expect(mapping?.session_id).toBe("session-1");
      expect(mapping?.epic_id).toBe("epic-123");
    });
  });

  describe("recordSync", () => {
    test("increments sync count", () => {
      manager.registerMapping("session-1", "epic-123");

      manager.recordSync("session-1");
      manager.recordSync("session-1");
      manager.recordSync("session-1");

      const mapping = manager.getMapping("session-1");
      expect(mapping?.synced_count).toBe(3);
      expect(mapping?.last_synced_at).toBeDefined();
    });

    test("does nothing for unknown session", () => {
      // Should not throw
      manager.recordSync("unknown");
    });
  });

  describe("removeMapping", () => {
    test("removes existing mapping", () => {
      manager.registerMapping("session-1", "epic-123");

      const removed = manager.removeMapping("session-1");

      expect(removed).toBe(true);
      expect(manager.getEpicForSession("session-1")).toBeUndefined();
    });

    test("returns false for unknown session", () => {
      const removed = manager.removeMapping("unknown");
      expect(removed).toBe(false);
    });
  });

  describe("listMappings", () => {
    test("lists all mappings", () => {
      manager.registerMapping("session-1", "epic-1");
      manager.registerMapping("session-2", "epic-2");
      manager.registerMapping("session-3", "epic-3");

      const mappings = manager.listMappings();

      expect(mappings).toHaveLength(3);
      expect(mappings.map((m) => m.session_id)).toContain("session-1");
      expect(mappings.map((m) => m.session_id)).toContain("session-2");
      expect(mappings.map((m) => m.session_id)).toContain("session-3");
    });

    test("returns empty array when no mappings", () => {
      const mappings = manager.listMappings();
      expect(mappings).toHaveLength(0);
    });
  });

  describe("resolveEpicId", () => {
    test("prioritizes step-level epic ID", () => {
      manager.registerMapping("session-1", "registered-epic");

      const resolved = manager.resolveEpicId("session-1", "step-epic");

      expect(resolved).toBe("step-epic");
      // Also updates the registered mapping
      expect(manager.getEpicForSession("session-1")).toBe("step-epic");
    });

    test("falls back to registered mapping", () => {
      manager.registerMapping("session-1", "registered-epic");

      const resolved = manager.resolveEpicId("session-1", undefined);

      expect(resolved).toBe("registered-epic");
    });

    test("returns undefined when no mapping exists", () => {
      const resolved = manager.resolveEpicId("unknown-session", undefined);
      expect(resolved).toBeUndefined();
    });
  });

  describe("clear", () => {
    test("removes all mappings", () => {
      manager.registerMapping("session-1", "epic-1");
      manager.registerMapping("session-2", "epic-2");

      manager.clear();

      expect(manager.listMappings()).toHaveLength(0);
    });
  });

  describe("getEpicInfo", () => {
    test("returns null when Beads not available", async () => {
      // Create manager with non-existent directory
      const mgr = new BeadsSessionManager("/tmp/nonexistent");
      const info = await mgr.getEpicInfo("any-epic");

      expect(info).toBeNull();
    });
  });
});
