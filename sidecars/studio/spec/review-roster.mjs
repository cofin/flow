/**
 * Deterministic parallel review roster planner from a Git range,
 * risk escalation signals, repository `AGENTIC_REVIEW` lenses,
 * `false-positive-suppressions.md` rules, 3-seat committee mode,
 * and cross-vendor adversarial routing.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { readTextSafe, resolveConfinedPath, toPosixRelative } from "../core/fs-io.mjs";
import { FrontmatterDocument } from "../core/frontmatter.mjs";
import { resolveWorktreeContext } from "../core/worktree.mjs";

const SQL_PATH_RE = /(?:^|\/)(?:migrations|alembic|queries|sql)(?:\/|$)|\.sql$/i;
const AUTH_PATH_RE = /(?:auth|security|iam|oauth|iap|token|credential|crypto|permission|rbac|acl)/i;
const CONCURRENCY_PATH_RE = /(?:lease|lock|pool|queue|worker|stream|bridge|transaction|ipc|subprocess)/i;
const SEAM_PATH_RE = /^(?:plugin\.json|mcp_config\.json|hooks\.json|pyproject\.toml|package\.json)$|\/__init__\.py$/;
const DIFF_ESCALATION_RE =
  /\b(?:SELECT\s+.+\s+FROM|ALTER\s+TABLE|CREATE\s+INDEX|FOR\s+UPDATE|BEGIN\s+TRANSACTION|Authorization|id_token|access_token|Mutex|Semaphore|Lock\(|spawnSync)\b/i;

export class ReviewRoster {
  /**
   * Plan a deterministic review roster for a workspace Git range and optional spec.
   *
   * @param {string} workspacePath
   * @param {{
   *   range?: string,
   *   specPath?: string | null,
   *   mode?: "auto" | "single" | "dual" | "committee",
   *   harness?: string,
   *   authorVendor?: string | null,
   *   router?: any,
   * }} [options]
   */
  static plan(
    workspacePath,
    {
      range = "HEAD~1..HEAD",
      specPath = null,
      mode = "auto",
      harness = "agy",
      authorVendor = null,
      router = null,
    } = {},
  ) {
    const root = path.resolve(workspacePath);
    const { effectiveAgentsRoot: effectiveRoot } = resolveWorktreeContext(root);
    const diffInfo = ReviewRoster.#inspectDiff(root, range);

    let specDegraded = false;
    let resolvedSpecRel = null;
    if (specPath) {
      const absSpec = path.isAbsolute(specPath) ? path.resolve(specPath) : path.resolve(effectiveRoot, specPath);
      if (fs.existsSync(absSpec)) {
        resolvedSpecRel = toPosixRelative(effectiveRoot, absSpec);
        const doc = FrontmatterDocument.parse(readTextSafe(absSpec) || "");
        specDegraded = doc.text("planning_quality") === "degraded";
      }
    }

    const escalationReasons = [];
    if (diffInfo.files.some((f) => SQL_PATH_RE.test(f))) escalationReasons.push("SQL or migration files changed");
    if (diffInfo.files.some((f) => AUTH_PATH_RE.test(f))) escalationReasons.push("Authentication or security files changed");
    if (diffInfo.files.some((f) => CONCURRENCY_PATH_RE.test(f))) escalationReasons.push("Concurrency, lock, or transport files changed");
    if (diffInfo.files.some((f) => SEAM_PATH_RE.test(f)) || diffInfo.surfaces.length >= 3) {
      escalationReasons.push("Public manifest or multi-surface seam changed");
    }
    if (diffInfo.highRiskSnippet && escalationReasons.length === 0) {
      escalationReasons.push("SQL, auth, or concurrency primitives modified in diff");
    }
    if (specDegraded) escalationReasons.push("Plan marked planning_quality: degraded");

    const repoLenses = ReviewRoster.#discoverRepoReviewLenses(effectiveRoot, diffInfo.files);
    const suppressions = Array.from(new Set(repoLenses.map((l) => l.suppressions).filter(Boolean)));
    const isHighRisk = escalationReasons.length > 0;
    const isSmallSingleSurface =
      mode === "single" ||
      (mode === "auto" &&
        diffInfo.total_lines > 0 &&
        (isHighRisk
          ? diffInfo.total_lines < 150 && diffInfo.surfaces.length <= 1
          : diffInfo.total_lines < 350 && diffInfo.surfaces.length <= 2));

    const routeFor = (kind, riskVal = isHighRisk ? "high" : "normal", extra = {}) =>
      router
        ? router.route({
            harness,
            taskKind: kind,
            risk: riskVal,
            complexity: isHighRisk ? 3.5 : 2.0,
            authorVendor,
            ...extra,
          })
        : { model: null, effort: isHighRisk ? "high" : "medium", tier: isHighRisk ? "frontier" : "balanced" };

    const reviewers = [];
    if (mode === "committee") {
      for (const [seat, agentName, desc] of [
        ["architecture", "code-reviewer", "Long-term architectural boundaries and public seams"],
        ["correctness", "quality-reviewer", "Failure modes, test strength, and edge cases"],
        ["operations", "quality-reviewer", "Simplicity, runtime ergonomics, and reversible maintenance"],
      ]) {
        const r = routeFor("committee", "high");
        reviewers.push({
          id: `committee-${seat}`,
          agent: agentName,
          tier: r.tier,
          model: r.model,
          effort: r.effort,
          paths: diffInfo.files,
          ...(resolvedSpecRel ? { spec_path: resolvedSpecRel } : {}),
          suppressions,
          reason: desc,
        });
      }
    } else if (isSmallSingleSurface) {
      const combinedAgent = resolvedSpecRel || isHighRisk ? "code-reviewer" : "quality-reviewer";
      const r = routeFor("code_review");
      reviewers.push({
        id: "combined",
        agent: combinedAgent,
        tier: r.tier,
        model: r.model,
        effort: r.effort,
        paths: diffInfo.files,
        skills: repoLenses.map((l) => l.skill).filter(Boolean),
        agents: repoLenses.map((l) => l.custom_agent).filter(Boolean),
        suppressions,
        reason: isHighRisk ? escalationReasons.join("; ") : "Routine diff under 350 lines",
      });
    } else {
      const confRoute = routeFor(resolvedSpecRel ? "spec_review" : "code_review");
      const qualRoute = routeFor("code_review");
      reviewers.push({
        id: "conformance",
        agent: "code-reviewer",
        tier: confRoute.tier,
        model: confRoute.model,
        effort: confRoute.effort,
        paths: diffInfo.files,
        ...(resolvedSpecRel ? { spec_path: resolvedSpecRel } : {}),
        suppressions,
        reason: isHighRisk ? escalationReasons.join("; ") : "Specification and contract conformance",
      });
      reviewers.push({
        id: "quality",
        agent: "quality-reviewer",
        tier: qualRoute.tier,
        model: qualRoute.model,
        effort: qualRoute.effort,
        paths: diffInfo.files,
        suppressions,
        reason: "Dead code, prose hygiene, and public-seam test strength",
      });
      for (const lens of repoLenses) {
        const lr = routeFor("code_review", lens.matched_high_risk || specDegraded ? "high" : "normal");
        reviewers.push({
          id: lens.id,
          agent: "quality-reviewer",
          ...(lens.skill ? { skill: lens.skill } : {}),
          ...(lens.checklist ? { checklist: lens.checklist } : {}),
          ...(lens.suppressions ? { suppressions: [lens.suppressions] } : {}),
          ...(lens.custom_agent ? { custom_agent: lens.custom_agent } : {}),
          tier: lr.tier,
          model: lr.model,
          effort: lr.effort,
          paths: lens.paths.length > 0 ? lens.paths : diffInfo.files,
          source: lens.source,
          reason: lens.reason,
        });
      }
    }

    const advRoute = routeFor("adversarial", isHighRisk ? "high" : "normal", { requireVendorDiversity: true });
    const isHighComplexity = isHighRisk || diffInfo.total_lines >= 350 || diffInfo.surfaces.length >= 3;

    return {
      range,
      workspace: root,
      mode: isSmallSingleSurface ? "single" : mode === "committee" ? "committee" : "dual",
      spec_path: resolvedSpecRel,
      escalation_reasons: escalationReasons,
      suppressions,
      needs_frontier_recheck_on_fast_findings: reviewers.some((r) => r.tier !== "frontier"),
      adversarial_review: {
        recommended: Boolean(isHighComplexity || resolvedSpecRel),
        model: advRoute.model,
        effort: advRoute.effort,
        vendor: advRoute.vendor || null,
        cross_vendor: Boolean(authorVendor && advRoute.vendor && advRoute.vendor !== authorVendor),
        reason: isHighRisk
          ? `High-risk surfaces changed (${escalationReasons.join("; ")})`
          : "Complex diff or spec review; orthogonal-vendor pass when quota allows",
      },
      stats: {
        files_changed: diffInfo.files.length,
        insertions: diffInfo.insertions,
        deletions: diffInfo.deletions,
        total_lines: diffInfo.total_lines,
        surfaces: diffInfo.surfaces,
      },
      reviewers,
    };
  }

  /**
   * Determine whether fast-tier Critical/Important findings require a targeted Frontier verification pass.
   *
   * @param {any[]} findings
   */
  static needsFrontierRecheck(findings) {
    return (findings || []).some((f) => {
      const sev = String(f?.severity || "").toLowerCase();
      return (sev === "critical" || sev === "important") && f?.verified_by_frontier !== true;
    });
  }

  static #inspectDiff(root, range) {
    const safeGit = (args) => {
      try {
        return execFileSync("git", ["-C", root, ...args], {
          encoding: "utf8",
          timeout: 4000,
          stdio: ["ignore", "pipe", "ignore"],
        });
      } catch {
        return null;
      }
    };
    let numstatRaw = safeGit(["diff", "--numstat", range]);
    if (numstatRaw === null) numstatRaw = safeGit(["diff-tree", "--numstat", "--no-commit-id", "-r", "HEAD"]) || "";
    const files = [];
    let insertions = 0;
    let deletions = 0;
    for (const line of String(numstatRaw || "").trim().split("\n")) {
      if (!line.trim()) continue;
      const parts = line.split("\t");
      if (parts.length < 3) continue;
      const ins = Number(parts[0]);
      const del = Number(parts[1]);
      if (Number.isFinite(ins)) insertions += ins;
      if (Number.isFinite(del)) deletions += del;
      files.push(parts.slice(2).join("\t").trim());
    }

    const surfaces = Array.from(
      new Set(
        files
          .filter((f) => !f.startsWith("tests/"))
          .map((f) => {
            const segs = f.split("/");
            return segs.length > 1 ? `${segs[0]}/${segs[1]}` : segs[0];
          }),
      ),
    );
    const patch = safeGit(["diff", "--unified=0", range]) || "";
    const added = patch
      .split("\n")
      .filter((l) => l.startsWith("+") && !l.startsWith("+++"))
      .join("\n");

    return {
      files,
      insertions,
      deletions,
      total_lines: insertions + deletions,
      surfaces,
      highRiskSnippet: DIFF_ESCALATION_RE.test(added),
    };
  }

  static #discoverRepoReviewLenses(effectiveRoot, changedFiles) {
    const lenses = [];
    const seen = new Set();
    const addSkillLens = (relSkill, source, domainHint = "") => {
      const cleanRel = String(relSkill || "").replace(/\\/g, "/").replace(/^\.\//, "");
      if (!cleanRel || seen.has(cleanRel)) return;
      let absSkill;
      try {
        absSkill = resolveConfinedPath(effectiveRoot, cleanRel);
      } catch {
        return;
      }
      if (!fs.existsSync(absSkill)) return;
      seen.add(cleanRel);
      const skillDir = path.dirname(absSkill);
      const checklistAbs = path.join(skillDir, "references", "checklist.md");
      const suppAbs = path.join(skillDir, "references", "false-positive-suppressions.md");
      const matched = domainHint
        ? changedFiles.filter((f) => f.toLowerCase().includes(domainHint.toLowerCase()))
        : changedFiles;
      if (domainHint && changedFiles.length > 0 && matched.length === 0) return;
      lenses.push({
        id: `repo-${path.basename(skillDir)}`,
        skill: cleanRel,
        checklist: fs.existsSync(checklistAbs) ? toPosixRelative(effectiveRoot, checklistAbs) : null,
        suppressions: fs.existsSync(suppAbs) ? toPosixRelative(effectiveRoot, suppAbs) : null,
        custom_agent: null,
        paths: matched,
        matched_high_risk: matched.some((f) => SQL_PATH_RE.test(f) || AUTH_PATH_RE.test(f)),
        source,
        reason: `Repository review skill (${source})`,
      });
    };

    const agenticReview = path.join(effectiveRoot, "AGENTIC_REVIEW");
    if (fs.existsSync(agenticReview)) {
      for (const line of (readTextSafe(agenticReview) || "").split("\n")) {
        if (line.trimStart().startsWith("#")) continue;
        const m = line.match(/^\s*review_capability_skills\s*:\s*["']?([^"'\s#]+)/);
        if (m) addSkillLens(m[1], "AGENTIC_REVIEW");
      }
    }

    const localSkillsDir = path.join(effectiveRoot, ".agents", "skills");
    if (fs.existsSync(localSkillsDir) && fs.statSync(localSkillsDir).isDirectory()) {
      for (const ent of fs.readdirSync(localSkillsDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        if (!ent.isDirectory() || !ent.name.startsWith("review-")) continue;
        const relSkill = `.agents/skills/${ent.name}/SKILL.md`;
        const slug = ent.name.slice("review-".length);
        const repoWide = slug === path.basename(effectiveRoot);
        addSkillLens(relSkill, ".agents/skills", repoWide ? "" : slug);
      }
    }

    const localAgentsDir = path.join(effectiveRoot, ".agents", "agents");
    if (fs.existsSync(localAgentsDir) && fs.statSync(localAgentsDir).isDirectory()) {
      for (const ent of fs.readdirSync(localAgentsDir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
        if (!ent.isFile() || !ent.name.endsWith("-reviewer.md")) continue;
        const slug = ent.name.slice(0, -"-reviewer.md".length);
        const matched = changedFiles.filter((f) => f.toLowerCase().includes(slug.toLowerCase()));
        if (changedFiles.length > 0 && matched.length === 0) continue;
        lenses.push({
          id: `agent-${slug}-reviewer`,
          skill: null,
          checklist: null,
          suppressions: null,
          custom_agent: `.agents/agents/${ent.name}`,
          paths: matched,
          matched_high_risk: matched.some((f) => SQL_PATH_RE.test(f) || AUTH_PATH_RE.test(f)),
          source: ".agents/agents",
          reason: `Domain reviewer matched '${slug}' paths`,
        });
      }
    }
    return lenses;
  }
}
