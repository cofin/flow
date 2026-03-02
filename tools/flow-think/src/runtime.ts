/**
 * Flow Think MCP - Runtime Detection
 *
 * Detects the JavaScript runtime environment (Bun vs Node.js)
 * and provides runtime-specific utilities.
 *
 * @module runtime
 */

/**
 * Supported JavaScript runtimes.
 */
export type RuntimeType = "bun" | "node" | "unknown";

/**
 * Information about the detected runtime.
 */
export interface RuntimeInfo {
  /** The detected runtime type */
  type: RuntimeType;
  /** Runtime version string */
  version: string;
  /** Whether this is the preferred runtime (Bun) */
  isPreferred: boolean;
  /** Human-readable description */
  description: string;
}

/**
 * Detect the current JavaScript runtime.
 *
 * Checks for Bun first (preferred), then falls back to Node.js detection.
 * Returns "unknown" if neither can be detected.
 *
 * @returns The detected runtime type
 */
export function detectRuntime(): RuntimeType {
  // Check for Bun first (preferred runtime)
  if (typeof globalThis !== "undefined" && "Bun" in globalThis) {
    return "bun";
  }

  // Check for Node.js
  if (
    typeof process !== "undefined" &&
    process.versions &&
    process.versions.node
  ) {
    return "node";
  }

  return "unknown";
}

/**
 * Get detailed runtime information.
 *
 * Provides version information and whether the runtime
 * is the preferred one (Bun).
 *
 * @returns Detailed runtime information
 */
export function getRuntimeInfo(): RuntimeInfo {
  const type = detectRuntime();

  switch (type) {
    case "bun": {
      // Access Bun version safely
      const bunGlobal = globalThis as unknown as { Bun: { version: string } };
      const version = bunGlobal.Bun?.version ?? "unknown";
      return {
        type: "bun",
        version,
        isPreferred: true,
        description: "Bun " + version,
      };
    }

    case "node": {
      const version = process.versions.node ?? "unknown";
      return {
        type: "node",
        version,
        isPreferred: false,
        description: "Node.js " + version,
      };
    }

    default:
      return {
        type: "unknown",
        version: "unknown",
        isPreferred: false,
        description: "Unknown runtime",
      };
  }
}

/**
 * Check if running in Bun.
 *
 * @returns true if running in Bun
 */
export function isBun(): boolean {
  return detectRuntime() === "bun";
}

/**
 * Check if running in Node.js.
 *
 * @returns true if running in Node.js
 */
export function isNode(): boolean {
  return detectRuntime() === "node";
}

/**
 * Log runtime information to stderr.
 *
 * Outputs the detected runtime for debugging purposes.
 */
export function logRuntime(): void {
  const info = getRuntimeInfo();
  console.error("   Runtime: " + info.description);

  if (!info.isPreferred && info.type === "node") {
    console.error(
      "   Note: Install Bun for better performance (https://bun.sh)"
    );
  }
}

/**
 * Spawn a subprocess using the appropriate runtime API.
 *
 * Uses Bun.spawn when available, falls back to Node.js child_process.
 *
 * @param command - Command and arguments to execute
 * @param options - Spawn options
 * @returns Promise resolving to exit code and output
 */
export async function spawn(
  command: string[],
  options: {
    stdout?: "pipe" | "inherit";
    stderr?: "pipe" | "inherit";
    cwd?: string;
  } = {}
): Promise<{ exitCode: number; stdout?: string; stderr?: string }> {
  const runtime = detectRuntime();

  if (runtime === "bun") {
    // Use Bun's native spawn
    const bunGlobal = globalThis as unknown as {
      Bun: {
        spawn: (
          command: string[],
          options: { stdout?: string; stderr?: string; cwd?: string }
        ) => {
          exited: Promise<number>;
          stdout: { text: () => Promise<string> } | null;
          stderr: { text: () => Promise<string> } | null;
        };
      };
    };

    const proc = bunGlobal.Bun.spawn(command, {
      stdout: options.stdout ?? "pipe",
      stderr: options.stderr ?? "pipe",
      ...(options.cwd ? { cwd: options.cwd } : {}),
    });

    const exitCode = await proc.exited;
    const stdout = proc.stdout ? await proc.stdout.text() : undefined;
    const stderr = proc.stderr ? await proc.stderr.text() : undefined;

    return { exitCode, stdout, stderr };
  } else {
    // Fall back to Node.js child_process
    const { spawn: nodeSpawn } = await import("node:child_process");

    return new Promise((resolve, reject) => {
      const [cmd, ...args] = command;
      const child = nodeSpawn(cmd, args, {
        stdio: [
          "pipe",
          options.stdout === "inherit" ? "inherit" : "pipe",
          options.stderr === "inherit" ? "inherit" : "pipe",
        ],
        ...(options.cwd ? { cwd: options.cwd } : {}),
      });

      let stdout = "";
      let stderr = "";

      if (child.stdout) {
        child.stdout.on("data", (data) => {
          stdout += data.toString();
        });
      }

      if (child.stderr) {
        child.stderr.on("data", (data) => {
          stderr += data.toString();
        });
      }

      child.on("error", reject);
      child.on("close", (code) => {
        resolve({
          exitCode: code ?? 1,
          stdout: stdout || undefined,
          stderr: stderr || undefined,
        });
      });
    });
  }
}
