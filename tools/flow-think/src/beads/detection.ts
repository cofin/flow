/**
 * Flow Think MCP - Beads CLI Detection
 *
 * Detects if the Beads CLI (bd) is installed and if Beads is
 * initialized in the current project.
 */

import { existsSync } from "fs";
import { join } from "path";

/**
 * Status of Beads availability.
 */
export interface BeadsStatus {
  /** Whether the bd CLI is installed */
  installed: boolean;
  /** Whether .beads directory exists */
  initialized: boolean;
  /** Whether Beads is fully available (installed AND initialized) */
  available: boolean;
  /** Error message if detection failed */
  error?: string;
}

/**
 * Cache for detection results.
 */
let installedCache: boolean | null = null;
const initializedCache: Map<string, boolean> = new Map();

/**
 * Clear all cached detection results.
 * Useful for testing or when environment changes.
 */
export function clearBeadsCache(): void {
  installedCache = null;
  initializedCache.clear();
}

/**
 * Beads detection service.
 *
 * Provides methods to check if Beads CLI is installed and
 * if Beads is initialized in a project.
 */
export class BeadsDetection {
  /**
   * Check if the Beads CLI (bd) is installed.
   *
   * Uses `which bd` or `where bd` depending on platform.
   * Results are cached after first check.
   */
  async isBeadsInstalled(): Promise<boolean> {
    if (installedCache !== null) {
      return installedCache;
    }

    try {
      // Use Bun's shell for subprocess
      const proc = Bun.spawn(["which", "bd"], {
        stdout: "pipe",
        stderr: "pipe",
      });

      const exitCode = await proc.exited;
      installedCache = exitCode === 0;

      if (installedCache) {
        console.error("🔗 Beads CLI detected");
      }

      return installedCache;
    } catch {
      // If which fails (e.g., Windows without which), try running bd --version
      try {
        const proc = Bun.spawn(["bd", "--version"], {
          stdout: "pipe",
          stderr: "pipe",
        });

        const exitCode = await proc.exited;
        installedCache = exitCode === 0;
        return installedCache;
      } catch {
        installedCache = false;
        return false;
      }
    }
  }

  /**
   * Check if Beads is initialized in a directory.
   *
   * Checks for the existence of `.beads/` directory.
   *
   * @param directory - Directory to check (defaults to cwd)
   */
  async isBeadsInitialized(directory?: string): Promise<boolean> {
    const dir = directory ?? process.cwd();
    const cacheKey = dir;

    if (initializedCache.has(cacheKey)) {
      return initializedCache.get(cacheKey)!;
    }

    const beadsDir = join(dir, ".beads");
    const exists = existsSync(beadsDir);

    initializedCache.set(cacheKey, exists);

    if (exists) {
      console.error(`📦 Beads initialized in ${dir}`);
    }

    return exists;
  }

  /**
   * Get full Beads status.
   *
   * Checks both installation and initialization.
   *
   * @param directory - Directory to check for initialization
   */
  async getBeadsStatus(directory?: string): Promise<BeadsStatus> {
    try {
      const installed = await this.isBeadsInstalled();
      const initialized = await this.isBeadsInitialized(directory);

      return {
        installed,
        initialized,
        available: installed && initialized,
      };
    } catch (error) {
      return {
        installed: false,
        initialized: false,
        available: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}
