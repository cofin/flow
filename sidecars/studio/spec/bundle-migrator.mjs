/**
 * @fileoverview Workspace OKF v0.2 bundle auditor, non-destructive brownfield migrator,
 * and over-split chapter compactor (`WorkspaceBundleMigrator`).
 */

import fs from "node:fs";
import path from "node:path";

import {
  extractH1,
  FrontmatterCodec,
  FrontmatterDocument,
  hasBodyHorizontalRule,
  stripBodyHorizontalRules,
} from "../core/frontmatter.mjs";
import { isClosedState, toPosixRelative, walkFiles, writeTextAtomic } from "../core/fs-io.mjs";
import {
  DEFAULT_FEEDBACK_STORE_DIR,
  DEFAULT_SPEC_BRANCH,
  discoverSpecRoots,
  FRONTMATTER_FREE_NAMES,
  readSetupConfig,
} from "../core/worktree.mjs";
import { SpecEngine } from "./spec-engine.mjs";

/**
 * Audits `.agents/` setup, migrates legacy spec layouts, strips stray frontmatter/HRs,
 * and compacts over-split multi-chapter specs while keeping completed states and dependencies.
 */
export class WorkspaceBundleMigrator {
  static DEPRECATED_PATHS = Object.freeze([
    ".beads",
    ".agents/beads.json",
    ".agents/transactions",
    ".agents/skills/flow-memory-keeper",
  ]);

  constructor(workspacePath, { env = process.env } = {}) {
    this.workspace = path.resolve(workspacePath);
    this.env = env;
    this.setup = readSetupConfig(this.workspace);
    this.effectiveRoot = this.setup.effective_root;
  }

  audit() {
    const setupFile = path.join(this.effectiveRoot, ".agents", "setup-state.json");
    const setupExists = fs.existsSync(setupFile);
    let rawSetup = null;
    const setupIssues = [];
    if (!setupExists) {
      setupIssues.push("missing_setup_state");
    } else {
      try {
        rawSetup = JSON.parse(fs.readFileSync(setupFile, "utf8"));
        if (!rawSetup || typeof rawSetup !== "object" || Array.isArray(rawSetup)) {
          setupIssues.push("invalid_setup_state_json");
          rawSetup = null;
        }
      } catch {
        setupIssues.push("invalid_setup_state_json");
      }
    }
    if (rawSetup) {
      if (String(rawSetup.bundle_root || "").trim() !== ".agents/bundles") setupIssues.push("nonstandard_bundle_root");
      if (String(rawSetup.okf_version || "").trim() !== "0.2") setupIssues.push("missing_okf_version");
      if (!rawSetup.workflow_preferences || typeof rawSetup.workflow_preferences !== "object") {
        setupIssues.push("missing_workflow_preferences");
      }
    }

    const bundleDir = path.join(this.effectiveRoot, ".agents", "bundles");
    const rootIndexPath = path.join(bundleDir, "index.md");
    const missingBundleIndex = !fs.existsSync(rootIndexPath);
    let rootIndexVersionBad = false;
    if (!missingBundleIndex) {
      const idxDoc = FrontmatterDocument.parse(fs.readFileSync(rootIndexPath, "utf8"));
      if (!idxDoc.hasFrontmatter || idxDoc.text("okf_version") !== "0.2") {
        rootIndexVersionBad = true;
      }
    }

    const legacySpecRoots = [];
    for (const cand of discoverSpecRoots(this.effectiveRoot)) {
      if (cand.canonical || !fs.existsSync(cand.root) || !fs.statSync(cand.root).isDirectory()) continue;
      const specIds = fs
        .readdirSync(cand.root, { withFileTypes: true })
        .filter((d) => d.isDirectory() && fs.existsSync(path.join(cand.root, d.name, "spec.md")))
        .map((d) => d.name)
        .sort();
      if (specIds.length > 0) legacySpecRoots.push({ rel: cand.rel, kind: cand.kind, spec_ids: specIds });
    }

    const engine = new SpecEngine({ workspacePath: this.effectiveRoot, env: this.env });
    const allSpecs = engine.listSpecs({ includeArchived: true });
    const fragmentedSpecs = WorkspaceBundleMigrator.#findFragmentedSpecs(allSpecs);

    const nestedIndexFrontmatter = [];
    const bodyHrFiles = [];
    const unindexedDocs = [];
    const rootIndexText = !missingBundleIndex ? fs.readFileSync(rootIndexPath, "utf8") : "";

    if (fs.existsSync(bundleDir) && fs.statSync(bundleDir).isDirectory()) {
      for (const file of walkFiles(bundleDir, { extensions: [".md"] })) {
        const rel = toPosixRelative(this.effectiveRoot, file);
        const name = path.basename(file);
        const content = fs.readFileSync(file, "utf8");
        const doc = FrontmatterDocument.parse(content);
        if (file !== rootIndexPath && FRONTMATTER_FREE_NAMES.has(name) && doc.hasFrontmatter) {
          nestedIndexFrontmatter.push(rel);
        }
        if (hasBodyHorizontalRule(doc.hasFrontmatter ? doc.body : content)) {
          bodyHrFiles.push(rel);
        }
        const subRel = toPosixRelative(bundleDir, file);
        const topDir = subRel.split("/")[0];
        if (["knowledge", "product", "research"].includes(topDir) && !FRONTMATTER_FREE_NAMES.has(name)) {
          if (!rootIndexText.includes(subRel)) unindexedDocs.push(subRel);
        }
      }
    }

    const deprecatedArtifacts = WorkspaceBundleMigrator.DEPRECATED_PATHS.filter((rel) =>
      fs.existsSync(path.join(this.effectiveRoot, rel)),
    );

    const issues = [];
    for (const code of setupIssues) {
      issues.push({
        code,
        severity: "warning",
        path: ".agents/setup-state.json",
        message: `Setup state alignment needed (${code}).`,
        auto_fixable: true,
      });
    }
    if (missingBundleIndex || rootIndexVersionBad) {
      issues.push({
        code: missingBundleIndex ? "missing_bundle_index" : "bundle_index_okf_version",
        severity: "error",
        path: ".agents/bundles/index.md",
        message: missingBundleIndex ? "Missing .agents/bundles/index.md." : 'Root index.md missing okf_version: "0.2".',
        auto_fixable: true,
      });
    }
    for (const leg of legacySpecRoots) {
      issues.push({
        code: "legacy_spec_root",
        severity: "warning",
        path: leg.rel,
        message: `${leg.spec_ids.length} spec(s) stored in legacy layout '${leg.rel}'.`,
        auto_fixable: true,
      });
    }
    for (const idxRel of nestedIndexFrontmatter) {
      issues.push({
        code: "nested_index_frontmatter",
        severity: "error",
        path: idxRel,
        message: `Nested bundle file '${idxRel}' must not contain YAML frontmatter.`,
        auto_fixable: true,
      });
    }
    for (const hrRel of bodyHrFiles) {
      issues.push({
        code: "body_horizontal_rule",
        severity: "warning",
        path: hrRel,
        message: `Bundle document '${hrRel}' contains standalone Markdown --- separators.`,
        auto_fixable: true,
      });
    }
    for (const depRel of deprecatedArtifacts) {
      issues.push({
        code: "deprecated_artifact",
        severity: "warning",
        path: depRel,
        message: `Deprecated legacy artifact '${depRel}' present.`,
        auto_fixable: false,
      });
    }
    for (const docRel of unindexedDocs) {
      issues.push({
        code: "unindexed_bundle_doc",
        severity: "warning",
        path: `.agents/bundles/${docRel}`,
        message: `Document '${docRel}' is missing from .agents/bundles/index.md.`,
        auto_fixable: true,
      });
    }
    for (const frag of fragmentedSpecs) {
      issues.push({
        code: "fragmented_spec",
        severity: "warning",
        path: frag.spec_path,
        message: `Spec '${frag.flow_id}' splits small open work across ${frag.total_chapters} chapters and can be compacted.`,
        auto_fixable: true,
      });
    }

    const needsMigration =
      setupIssues.length > 0 ||
      missingBundleIndex ||
      rootIndexVersionBad ||
      legacySpecRoots.length > 0 ||
      nestedIndexFrontmatter.length > 0 ||
      bodyHrFiles.length > 0 ||
      fragmentedSpecs.length > 0;

    return {
      workspace: this.workspace,
      effective_root: this.effectiveRoot,
      initialized: fs.existsSync(path.join(this.effectiveRoot, ".agents")),
      bundle_initialized: fs.existsSync(bundleDir),
      bundle_root: ".agents/bundles",
      ignore_policy: this.setup.ignore_policy,
      needs_migration: needsMigration,
      issues,
      legacy_spec_roots: legacySpecRoots,
      fragmented_specs: fragmentedSpecs,
      nested_index_frontmatter: nestedIndexFrontmatter,
      body_hr_files: bodyHrFiles,
      deprecated_artifacts: deprecatedArtifacts,
      unindexed_docs: unindexedDocs,
    };
  }

  apply({ migrateSpecs = false, compactSpecs = false, policy = null, dryRun = false } = {}) {
    const updatedFiles = [];
    const actions = [];
    const migratedSpecs = [];
    const compactedSpecs = [];
    const bundleDir = path.join(this.effectiveRoot, ".agents", "bundles");
    const canonicalSpecsDir = path.join(bundleDir, "specs");

    if (!dryRun) {
      for (const dir of [
        path.join(this.effectiveRoot, ".agents"),
        bundleDir,
        path.join(bundleDir, "knowledge"),
        path.join(bundleDir, "product"),
        path.join(bundleDir, "research"),
        canonicalSpecsDir,
      ]) {
        if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      }
    }

    const setupFile = path.join(this.effectiveRoot, ".agents", "setup-state.json");
    let existingSetup = {};
    if (fs.existsSync(setupFile)) {
      try {
        const parsed = JSON.parse(fs.readFileSync(setupFile, "utf8"));
        if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) existingSetup = parsed;
      } catch {
        existingSetup = {};
      }
    }
    const prevPrefs =
      existingSetup.workflow_preferences && typeof existingSetup.workflow_preferences === "object"
        ? existingSetup.workflow_preferences
        : {};
    const isPlugin = fs.existsSync(path.join(this.effectiveRoot, "plugin.json"));
    const requestedPolicy = policy === "shared" || policy === "local-only" ? policy : prevPrefs.ignore_policy || this.setup.ignore_policy;
    const nextPolicy = isPlugin ? "local-only" : requestedPolicy;
    const nextSetup = {
      ...existingSetup,
      setup_status: "complete",
      schema_version: "0.2",
      okf_version: "0.2",
      root_directory: ".agents",
      bundle_root: ".agents/bundles",
      workflow_preferences: {
        ...prevPrefs,
        ignore_policy: nextPolicy,
        spec_branch: prevPrefs.spec_branch || DEFAULT_SPEC_BRANCH,
        feedback_store_dir: prevPrefs.feedback_store_dir || DEFAULT_FEEDBACK_STORE_DIR,
      },
    };
    const nextSetupText = `${JSON.stringify(nextSetup, null, 2)}\n`;
    const curSetupText = fs.existsSync(setupFile) ? fs.readFileSync(setupFile, "utf8") : "";
    if (curSetupText !== nextSetupText) {
      if (!dryRun) writeTextAtomic(setupFile, nextSetupText);
      updatedFiles.push(".agents/setup-state.json");
      actions.push("normalized_setup_state");
    }

    if (migrateSpecs) {
      for (const leg of discoverSpecRoots(this.effectiveRoot).filter((c) => !c.canonical)) {
        if (!fs.existsSync(leg.root) || !fs.statSync(leg.root).isDirectory()) continue;
        const specDirs = fs
          .readdirSync(leg.root, { withFileTypes: true })
          .filter((d) => d.isDirectory() && fs.existsSync(path.join(leg.root, d.name, "spec.md")))
          .sort((a, b) => a.name.localeCompare(b.name));
        for (const entry of specDirs) {
          const srcDir = path.join(leg.root, entry.name);
          const dstDir = path.join(canonicalSpecsDir, entry.name);
          if (!fs.existsSync(path.join(dstDir, "spec.md"))) {
            if (!dryRun) {
              fs.mkdirSync(path.dirname(dstDir), { recursive: true });
              fs.cpSync(srcDir, dstDir, { recursive: true, force: true });
              if (leg.kind !== "legacy_root_specs") fs.rmSync(srcDir, { recursive: true, force: true });
            }
            migratedSpecs.push(entry.name);
            updatedFiles.push(`.agents/bundles/specs/${entry.name}/spec.md`);
            actions.push(`moved_spec:${entry.name}`);
          }
        }
      }
    }

    const rootIndexPath = path.join(bundleDir, "index.md");
    if (fs.existsSync(bundleDir)) {
      for (const file of walkFiles(bundleDir, { extensions: [".md"] })) {
        const orig = fs.readFileSync(file, "utf8");
        let next = orig;
        if (file !== rootIndexPath && FRONTMATTER_FREE_NAMES.has(path.basename(file))) {
          const parsed = FrontmatterDocument.parse(next);
          if (parsed.hasFrontmatter) next = parsed.body.replace(/^\r?\n+/, "");
        }
        next = stripBodyHorizontalRules(next);
        if (next !== orig) {
          if (!dryRun) writeTextAtomic(file, next);
          const rel = toPosixRelative(this.effectiveRoot, file);
          if (!updatedFiles.includes(rel)) updatedFiles.push(rel);
          actions.push(`cleaned_markdown:${rel}`);
        }
      }
    }

    if (!fs.existsSync(rootIndexPath)) {
      const bundleName = path.basename(this.effectiveRoot);
      const lines = ["---", 'okf_version: "0.2"', `bundle: ${bundleName}`, "---", "", `# ${bundleName} Bundle`, ""];
      if (!dryRun) writeTextAtomic(rootIndexPath, lines.join("\n"));
      updatedFiles.push(".agents/bundles/index.md");
      actions.push("created_bundle_index");
    }

    if (compactSpecs && fs.existsSync(canonicalSpecsDir)) {
      const engine = new SpecEngine({ workspacePath: this.effectiveRoot, env: this.env });
      for (const frag of WorkspaceBundleMigrator.#findFragmentedSpecs(engine.listSpecs({ includeArchived: true }))) {
        const comp = this.compactSpec(frag.flow_id, { dryRun });
        if (comp.compacted) {
          compactedSpecs.push(frag.flow_id);
          for (const f of comp.updated_files) {
            if (!updatedFiles.includes(f)) updatedFiles.push(f);
          }
          actions.push(`compacted_spec:${frag.flow_id}`);
        }
      }
    }

    return {
      ok: true,
      dry_run: Boolean(dryRun),
      ignore_policy: nextPolicy,
      updated_files: updatedFiles,
      migrated_specs: migratedSpecs,
      compacted_specs: compactedSpecs,
      actions,
    };
  }

  compactSpec(flowId, { dryRun = false } = {}) {
    const engine = new SpecEngine({ workspacePath: this.effectiveRoot, env: this.env });
    const { spec } = engine.status(flowId);
    if (!spec.has_chapters || (spec.chapters || []).length < 2) {
      return { ok: true, flow_id: flowId, compacted: false, updated_files: [] };
    }
    const eligibleChapters = (spec.chapters || []).filter(
      (c) => !isClosedState(c.state) && c.planning_status !== "empirical_dependent",
    );
    if (eligibleChapters.length < 2) {
      return { ok: true, flow_id: flowId, compacted: false, updated_files: [] };
    }

    const updatedFiles = [];
    const targetChapter = eligibleChapters[0];
    const targetTasksDir = path.join(spec.spec_dir, "chapters", targetChapter.chapter_id, "tasks");
    if (!dryRun) fs.mkdirSync(targetTasksDir, { recursive: true });

    const allEligibleTasks = eligibleChapters.flatMap((c) => c.tasks || []);
    const renameMap = new Map();
    let nextIdx = 1;
    for (const t of allEligibleTasks) {
      const newShort = `t${String(nextIdx).padStart(2, "0")}`;
      nextIdx += 1;
      const newId = `${spec.flow_id}:${targetChapter.chapter_id.split("-")[0]}:${newShort}`;
      renameMap.set(t.id, newId);
    }

    for (let i = 0; i < allEligibleTasks.length; i += 1) {
      const task = allEligibleTasks[i];
      const newId = renameMap.get(task.id);
      const newShort = newId.split(":").pop();
      const slugBase = String(task.filename || `${newShort}.md`).replace(/^[a-z0-9]+-/, "");
      const newPath = path.join(targetTasksDir, `${newShort}-${slugBase}`);
      const nextDeps = (task.depends_on || []).map((dep) => renameMap.get(dep) || dep);
      if (!dryRun && task.abs_path && fs.existsSync(task.abs_path)) {
        const nextText = FrontmatterCodec.updateKeys(fs.readFileSync(task.abs_path, "utf8"), {
          id: newId,
          chapter_id: targetChapter.chapter_id,
          depends_on: nextDeps,
        });
        writeTextAtomic(newPath, nextText);
        if (path.resolve(newPath) !== path.resolve(task.abs_path)) fs.rmSync(task.abs_path, { force: true });
      }
      updatedFiles.push(toPosixRelative(this.effectiveRoot, newPath));
    }

    const removedChapters = new Set(eligibleChapters.slice(1).map((c) => c.chapter_id));
    if (!dryRun) {
      for (const remId of removedChapters) {
        fs.rmSync(path.join(spec.spec_dir, "chapters", remId), { recursive: true, force: true });
      }
      const nextChapters = (spec.chapters || []).map((c) => c.chapter_id).filter((id) => !removedChapters.has(id));
      const rootSpecRaw = fs.readFileSync(spec.spec_path, "utf8");
      writeTextAtomic(
        spec.spec_path,
        FrontmatterCodec.updateKeys(rootSpecRaw, { chapters: nextChapters, current_chapter: targetChapter.chapter_id }),
      );
      updatedFiles.push(spec.rel_path);
    }

    return { ok: true, flow_id: flowId, compacted: true, updated_files: updatedFiles };
  }

  static #findFragmentedSpecs(allSpecs) {
    const out = [];
    for (const s of allSpecs || []) {
      if (!s.has_chapters || isClosedState(s.state)) continue;
      const openChapters = (s.chapters || []).filter((c) => !isClosedState(c.state) && c.planning_status !== "empirical_dependent");
      if (openChapters.length >= 3 && openChapters.every((c) => (c.tasks || []).length <= 2)) {
        out.push({ flow_id: s.flow_id, total_chapters: openChapters.length, spec_path: s.rel_path });
      }
    }
    return out;
  }
}
