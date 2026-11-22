/**
 * @fileoverview Spec closeout validation, hygiene and graph checks, provenance stamping,
 * index/log updates, and optional cleanup (`SpecCloseout`).
 */

import fs from "node:fs";
import path from "node:path";

import { FrontmatterCodec } from "../core/frontmatter.mjs";
import { isClosedState, readTextSafe, sha256Hex, toPosixRelative, writeTextAtomic } from "../core/fs-io.mjs";
import { GitRunner, resolveGitIdentity } from "../core/git.mjs";
import { BundleGraph, BundleGraphLinter } from "../knowledge/bundle-graph.mjs";
import { AgentsBranchSync } from "./git-spec-branch.mjs";
import { SpecEngine } from "./spec-engine.mjs";

/**
 * Validates spec completion, runs bundle graph checks, stamps `verified_*` metadata,
 * updates `specs/index.md` + `log.md`, and optionally archives/removes the spent spec folder.
 */
export class SpecCloseout {
  constructor(workspacePath, { env = process.env } = {}) {
    this.workspace = path.resolve(workspacePath);
    this.env = env;
    this.engine = new SpecEngine({ workspacePath: this.workspace, env });
    this.git = GitRunner.forWorkspace(this.engine.effectiveRoot, { env });
  }

  run(flowId, { apply = false, keep = true, verifiedBy = null } = {}) {
    const cleanFlow = String(flowId || "").trim();
    if (!cleanFlow || /[\\/]|\.\./.test(cleanFlow)) {
      throw new Error(`Invalid flowId: ${flowId}`);
    }
    const { spec } = this.engine.status(cleanFlow);
    const allTasks = spec.has_chapters ? (spec.chapters || []).flatMap((c) => c.tasks || []) : spec.tasks || [];
    const openTasks = allTasks.filter((t) => !isClosedState(t.state));
    const reasons = [];
    if (openTasks.length > 0) reasons.push("open_tasks");

    if (String(spec.type || "").toUpperCase() === "PRD") {
      const openChildren = this.engine
        .listSpecs({ includeArchived: true })
        .filter((s) => s.parent_prd === cleanFlow && !isClosedState(s.state));
      if (openChildren.length > 0) reasons.push("open_child_specs");
    }

    const graph = BundleGraph.load(this.engine.bundleDir, { workspaceRoot: this.engine.effectiveRoot });
    const graphFindings = BundleGraphLinter.lint(graph);
    const headSha = this.git.isGitRepo()
      ? this.git.revParseVerify("HEAD", { short: 7 }).value || spec.last_reviewed_commit || "0000000"
      : spec.last_reviewed_commit || "0000000";
    const identity = resolveGitIdentity(this.workspace, { env: this.env });
    const by = verifiedBy || `human:${identity.email}`;
    const at = new Date().toISOString();

    if (reasons.length > 0) {
      return {
        ok: false,
        flow_id: cleanFlow,
        reasons,
        open_tasks: openTasks.map((t) => t.id),
        graph: graphFindings,
        message: `${openTasks.length} open task(s) or child specs block closeout.`,
      };
    }

    const updatedFiles = [];
    let removedSpecDir = false;
    if (apply) {
      const rawSpec = readTextSafe(spec.spec_path) || "";
      const next = FrontmatterCodec.updateKeys(rawSpec, {
        state: "completed",
        status: "stable",
        last_reviewed_commit: headSha,
        verified_by: by,
        verified_at: at,
      });
      if (next !== rawSpec) {
        writeTextAtomic(spec.spec_path, next);
        updatedFiles.push(spec.rel_path);
      }
      this.engine.syncChecklists({ flowId: cleanFlow });
      this.#prependArchiveLog(cleanFlow, spec.title, headSha);
      updatedFiles.push(toPosixRelative(this.engine.effectiveRoot, path.join(this.engine.bundleDir, "log.md")));

      if (!keep && spec.spec_dir && fs.existsSync(spec.spec_dir)) {
        fs.rmSync(spec.spec_dir, { recursive: true, force: true });
        removedSpecDir = true;
      }
      AgentsBranchSync.rebuildSpecsIndex(path.join(this.engine.bundleDir, "specs"), { dryRun: false });
    }

    return {
      ok: true,
      flow_id: cleanFlow,
      verified: { by, at },
      last_reviewed_commit: headSha,
      graph: graphFindings,
      updated_files: [...new Set(updatedFiles)],
      removed_spec_dir: removedSpecDir,
      spec_sha256: spec.spec_path && fs.existsSync(spec.spec_path) ? sha256Hex(readTextSafe(spec.spec_path) || "") : null,
    };
  }

  #prependArchiveLog(flowId, title, headSha) {
    const logPath = path.join(this.engine.bundleDir, "log.md");
    const dateStr = new Date().toISOString().slice(0, 10);
    const entry = `- ${dateStr} **archive**: \`${flowId}\` — ${title} (verified at \`${headSha}\`)`;
    const raw = readTextSafe(logPath);
    if (raw && raw.includes(entry)) return;
    if (!raw || !raw.trim()) {
      writeTextAtomic(logPath, `# Bundle Log\n\n${entry}\n`);
      return;
    }
    const lines = raw.replace(/\r\n/g, "\n").split("\n");
    const headingIdx = lines.findIndex((line) => /^#\s+/.test(line.trim()));
    if (headingIdx === -1) {
      const rest = raw.trimEnd();
      writeTextAtomic(logPath, `# Bundle Log\n\n${entry}\n${rest ? `${rest}\n` : ""}`);
      return;
    }
    const before = lines.slice(0, headingIdx + 1).join("\n");
    const afterLines = lines.slice(headingIdx + 1);
    while (afterLines.length > 0 && afterLines[0].trim() === "") afterLines.shift();
    const after = afterLines.join("\n").trimEnd();
    const next = after ? `${before}\n\n${entry}\n${after}\n` : `${before}\n\n${entry}\n`;
    writeTextAtomic(logPath, next);
  }
}
