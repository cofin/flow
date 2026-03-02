/**
 * Flow Think MCP - Doctor/Verification Command
 *
 * Provides comprehensive health checks for the MCP installation.
 * Verifies server startup, Beads CLI availability, configuration,
 * and dependency installation.
 */

import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { loadConfig } from "./config.js";
import { BeadsDetection, clearBeadsCache } from "./beads/detection.js";

/**
 * Status of an individual health check.
 */
export type CheckStatus = "pass" | "fail" | "warn" | "skip";

/**
 * Result of a single health check.
 */
export interface CheckResult {
  name: string;
  status: CheckStatus;
  message: string;
  details?: string;
  duration_ms?: number;
}

/**
 * Overall doctor report.
 */
export interface DoctorReport {
  healthy: boolean;
  timestamp: string;
  duration_ms: number;
  checks: CheckResult[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    warnings: number;
    skipped: number;
  };
}

const SYMBOLS = {
  pass: "\u2713",
  fail: "\u2717",
  warn: "!",
  skip: "-",
} as const;

const COLORS = {
  reset: "\x1b[0m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  yellow: "\x1b[33m",
  gray: "\x1b[90m",
  bold: "\x1b[1m",
} as const;

/**
 * FlowThink Doctor - Health check system.
 */
export class FlowThinkDoctor {
  private beadsDetection: BeadsDetection;
  private workingDirectory: string;

  constructor(workingDirectory?: string) {
    this.beadsDetection = new BeadsDetection();
    this.workingDirectory = workingDirectory ?? process.cwd();
  }

  async runAllChecks(): Promise<DoctorReport> {
    const startTime = Date.now();
    const checks: CheckResult[] = [];

    clearBeadsCache();

    checks.push(await this.checkPackageJson());
    checks.push(await this.checkDependencies());
    checks.push(await this.checkTypeScript());
    checks.push(await this.checkConfiguration());
    checks.push(await this.checkBeadsCli());
    checks.push(await this.checkBeadsInitialized());
    checks.push(await this.checkMcpServer());
    checks.push(await this.checkSourceFiles());

    const summary = {
      total: checks.length,
      passed: checks.filter((c) => c.status === "pass").length,
      failed: checks.filter((c) => c.status === "fail").length,
      warnings: checks.filter((c) => c.status === "warn").length,
      skipped: checks.filter((c) => c.status === "skip").length,
    };

    return {
      healthy: summary.failed === 0,
      timestamp: new Date().toISOString(),
      duration_ms: Date.now() - startTime,
      checks,
      summary,
    };
  }

  async checkPackageJson(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Package Configuration";

    try {
      const packagePath = this.resolveProjectPath("package.json");

      if (!existsSync(packagePath)) {
        return {
          name,
          status: "fail",
          message: "package.json not found",
          details: `Expected at: ${packagePath}`,
          duration_ms: Date.now() - start,
        };
      }

      const content = readFileSync(packagePath, "utf8");
      const pkg = JSON.parse(content);

      if (!pkg.name || !pkg.version) {
        return {
          name,
          status: "warn",
          message: "package.json missing name or version",
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "pass",
        message: `${pkg.name}@${pkg.version}`,
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to parse package.json",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkDependencies(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Dependencies";

    try {
      const nodeModulesPath = this.resolveProjectPath("node_modules");

      if (!existsSync(nodeModulesPath)) {
        return {
          name,
          status: "fail",
          message: "node_modules not found",
          details: "Run: bun install",
          duration_ms: Date.now() - start,
        };
      }

      const requiredDeps = ["@modelcontextprotocol/sdk"];
      const missingDeps: string[] = [];

      for (const dep of requiredDeps) {
        const depPath = join(nodeModulesPath, dep);
        if (!existsSync(depPath)) {
          missingDeps.push(dep);
        }
      }

      if (missingDeps.length > 0) {
        return {
          name,
          status: "fail",
          message: `Missing dependencies: ${missingDeps.join(", ")}`,
          details: "Run: bun install",
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "pass",
        message: "All required dependencies installed",
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to check dependencies",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkTypeScript(): Promise<CheckResult> {
    const start = Date.now();
    const name = "TypeScript";

    try {
      const tsconfigPath = this.resolveProjectPath("tsconfig.json");

      if (!existsSync(tsconfigPath)) {
        return {
          name,
          status: "warn",
          message: "tsconfig.json not found",
          details: "TypeScript configuration may use defaults",
          duration_ms: Date.now() - start,
        };
      }

      const distPath = this.resolveProjectPath("dist");
      if (!existsSync(distPath)) {
        return {
          name,
          status: "warn",
          message: "dist directory not found",
          details: "Run: bun run build",
          duration_ms: Date.now() - start,
        };
      }

      const entryPath = this.resolveProjectPath("dist/index.js");
      if (!existsSync(entryPath)) {
        return {
          name,
          status: "warn",
          message: "Compiled entry point not found",
          details: "Run: bun run build",
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "pass",
        message: "TypeScript configured and built",
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to check TypeScript",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkConfiguration(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Configuration";

    try {
      const config = loadConfig();

      if (
        typeof config.outputFormat !== "string" ||
        typeof config.maxHistorySize !== "number"
      ) {
        return {
          name,
          status: "fail",
          message: "Configuration has invalid structure",
          duration_ms: Date.now() - start,
        };
      }

      const envVarsSet: string[] = [];
      if (process.env.FLOW_MCP_OUTPUT_FORMAT) envVarsSet.push("OUTPUT_FORMAT");
      if (process.env.FLOW_MCP_MAX_HISTORY) envVarsSet.push("MAX_HISTORY");
      if (process.env.FLOW_MCP_BEADS_SYNC) envVarsSet.push("BEADS_SYNC");

      const message =
        envVarsSet.length > 0
          ? `Loaded with env overrides: ${envVarsSet.join(", ")}`
          : "Using defaults";

      return {
        name,
        status: "pass",
        message,
        details: `Output: ${config.outputFormat}, History: ${config.maxHistorySize}, Beads: ${config.beadsSync ? "enabled" : "disabled"}`,
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to load configuration",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkBeadsCli(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Beads CLI";

    try {
      const installed = await this.beadsDetection.isBeadsInstalled();

      if (installed) {
        return {
          name,
          status: "pass",
          message: "bd CLI installed",
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "warn",
        message: "bd CLI not found",
        details: "Install with: npm install -g beads-cli",
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "warn",
        message: "Failed to detect Beads CLI",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkBeadsInitialized(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Beads Project";

    try {
      const initialized = await this.beadsDetection.isBeadsInitialized(
        this.workingDirectory
      );

      if (initialized) {
        return {
          name,
          status: "pass",
          message: `.beads directory found in ${this.workingDirectory}`,
          duration_ms: Date.now() - start,
        };
      }

      const parentDir = dirname(this.workingDirectory);
      const parentInitialized =
        await this.beadsDetection.isBeadsInitialized(parentDir);

      if (parentInitialized) {
        return {
          name,
          status: "pass",
          message: `.beads directory found in parent: ${parentDir}`,
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "skip",
        message: "Beads not initialized (optional)",
        details: "Initialize with: bd init --stealth",
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "warn",
        message: "Failed to check Beads initialization",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkMcpServer(): Promise<CheckResult> {
    const start = Date.now();
    const name = "MCP Server";

    try {
      const { FlowThinkServer } = await import("./server.js");
      const config = loadConfig();
      const server = new FlowThinkServer(config);

      if (
        typeof server.processStep !== "function" ||
        typeof server.getHistory !== "function"
      ) {
        return {
          name,
          status: "fail",
          message: "Server missing required methods",
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "pass",
        message: "Server instantiation successful",
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to instantiate MCP server",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  async checkSourceFiles(): Promise<CheckResult> {
    const start = Date.now();
    const name = "Source Files";

    const requiredFiles = [
      "src/index.ts",
      "src/server.ts",
      "src/config.ts",
      "src/types.ts",
      "src/schema.ts",
      "src/formatter.ts",
      "src/beads/index.ts",
      "src/beads/detection.ts",
    ];

    try {
      const missingFiles: string[] = [];

      for (const file of requiredFiles) {
        const filePath = this.resolveProjectPath(file);
        if (!existsSync(filePath)) {
          missingFiles.push(file);
        }
      }

      if (missingFiles.length > 0) {
        return {
          name,
          status: "fail",
          message: `Missing source files: ${missingFiles.join(", ")}`,
          duration_ms: Date.now() - start,
        };
      }

      return {
        name,
        status: "pass",
        message: `All ${requiredFiles.length} source files present`,
        duration_ms: Date.now() - start,
      };
    } catch (error) {
      return {
        name,
        status: "fail",
        message: "Failed to check source files",
        details: error instanceof Error ? error.message : String(error),
        duration_ms: Date.now() - start,
      };
    }
  }

  private resolveProjectPath(relativePath: string): string {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    const projectRoot = dirname(__dirname);

    return join(projectRoot, relativePath);
  }

  formatReport(report: DoctorReport, useColors = true): string {
    const c = useColors
      ? COLORS
      : { reset: "", green: "", red: "", yellow: "", gray: "", bold: "" };
    const lines: string[] = [];

    lines.push("");
    lines.push(`${c.bold}Flow Think MCP - Health Check${c.reset}`);
    lines.push("=".repeat(40));
    lines.push("");

    for (const check of report.checks) {
      const symbol = SYMBOLS[check.status];
      let color: string;

      switch (check.status) {
        case "pass":
          color = c.green;
          break;
        case "fail":
          color = c.red;
          break;
        case "warn":
          color = c.yellow;
          break;
        default:
          color = c.gray;
      }

      lines.push(
        `${color}[${symbol}]${c.reset} ${check.name}: ${check.message}`
      );

      if (check.details) {
        lines.push(`    ${c.gray}${check.details}${c.reset}`);
      }
    }

    lines.push("");
    lines.push("-".repeat(40));

    const { summary } = report;
    const statusText = report.healthy
      ? `${c.green}${c.bold}HEALTHY${c.reset}`
      : `${c.red}${c.bold}UNHEALTHY${c.reset}`;

    lines.push(
      `Status: ${statusText} | ` +
        `${c.green}${summary.passed} passed${c.reset}, ` +
        `${c.red}${summary.failed} failed${c.reset}, ` +
        `${c.yellow}${summary.warnings} warnings${c.reset}, ` +
        `${c.gray}${summary.skipped} skipped${c.reset}`
    );
    lines.push(`Duration: ${report.duration_ms}ms`);
    lines.push("");

    return lines.join("\n");
  }

  formatReportJson(report: DoctorReport): string {
    return JSON.stringify(report, null, 2);
  }
}

export async function runDoctor(
  options: {
    json?: boolean;
    noColor?: boolean;
    workingDirectory?: string;
  } = {}
): Promise<boolean> {
  const doctor = new FlowThinkDoctor(options.workingDirectory);
  const report = await doctor.runAllChecks();

  if (options.json) {
    console.log(doctor.formatReportJson(report));
  } else {
    console.log(doctor.formatReport(report, !options.noColor));
  }

  return report.healthy;
}

// CLI entry point
if (import.meta.main) {
  const args = process.argv.slice(2);
  const json = args.includes("--json");
  const noColor = args.includes("--no-color") || process.env.NO_COLOR === "1";

  runDoctor({ json, noColor })
    .then((healthy) => {
      process.exit(healthy ? 0 : 1);
    })
    .catch((error) => {
      console.error("Doctor check failed:", error);
      process.exit(1);
    });
}
