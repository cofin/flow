/**
 * @fileoverview Git workflow linters and helpers: PR body validation,
 * stacked branch inspection/restack planning, and Co-authored-by checking.
 */

import path from "node:path";

import { GitRunner } from "./git.mjs";

const COAUTHOR_TRAILER_RE = /^Co-authored-by:\s*(.+?)\s*<([^>\s]+)>\s*$/gim;
const BOT_AUTHOR_RE = /(?:\[bot\]|dependabot|github-actions|renovate|copilot)/i;
const INTERNAL_CEREMONY_RE =
  /(?:##\s*(?:Verification|Merge Danger|Blast Radius)\b|\*\*(?:Door|Blast Radius):\*\*|ai-review-remediation)/i;

function normalizeEmail(raw) {
  return String(raw || "").trim().toLowerCase();
}

function splitNameEmail(raw) {
  const m = String(raw || "").trim().match(/^(.+?)\s*<([^>\s]+)>$/);
  if (!m) return null;
  return { name: m[1].trim(), email: normalizeEmail(m[2]) };
}

/**
 * Validate PR title and body text against concise repository engineering style.
 */
export class PRBodyValidator {
  /**
   * @param {string} title
   * @param {string} body
   * @returns {Array<{ code: string, severity: string, message: string }>}
   */
  validate(title, body) {
    /** @type {Array<{ code: string, severity: string, message: string }>} */
    const findings = [];
    const cleanTitle = String(title || "").trim();
    const cleanBody = String(body || "").trim();
    if (!cleanTitle) {
      findings.push({ code: "PR_TITLE_EMPTY", severity: "error", message: "PR title cannot be empty." });
    }
    if (cleanTitle.includes("!")) {
      findings.push({ code: "PR_EXCLAMATION", severity: "error", message: "Avoid exclamation marks in PR titles." });
    }
    if (!cleanBody) {
      findings.push({ code: "PR_BODY_EMPTY", severity: "error", message: "PR body cannot be empty." });
    }
    if (INTERNAL_CEREMONY_RE.test(cleanBody)) {
      findings.push({
        code: "PR_CEREMONY_LEAK",
        severity: "error",
        message: "Remove template ceremony headings or verification command blocks from PR descriptions.",
      });
    }
    return findings;
  }
}

/**
 * Inspect branch ancestry against `base` to build a clean stacked branch view.
 */
export class StackInspector {
  constructor(workspace = process.cwd(), opts = {}) {
    this.runner = opts.runner || GitRunner.forWorkspace(workspace, opts);
  }

  inspect({ base = "main", branches = null } = {}) {
    const baseRef = this.runner.revParseVerify(`refs/heads/${base}`).ok
      ? base
      : this.runner.revParseVerify(`refs/remotes/origin/${base}`).ok
        ? `origin/${base}`
        : "HEAD";
    const listed = Array.isArray(branches) && branches.length > 0
      ? branches
      : this.runner
          .runGit(["for-each-ref", "--format=%(refname:short)", "refs/heads"], { allowFailure: true })
          .stdout.split(/\r?\n/)
          .map((s) => s.trim())
          .filter((b) => b && b !== base && b !== "main" && b !== "master");

    const entries = [];
    for (const branch of listed) {
      const tip = this.runner.revParseVerify(branch);
      if (!tip.ok) continue;
      const ahead = this.runner.runGit(["rev-list", "--count", `${baseRef}..${branch}`], { allowFailure: true });
      const count = Number.parseInt(ahead.stdout.trim(), 10) || 0;
      if (count === 0) continue;
      entries.push({
        branch,
        tip_sha: tip.value.slice(0, 7),
        commits_ahead: count,
      });
    }
    entries.sort((a, b) => a.commits_ahead - b.commits_ahead || a.branch.localeCompare(b.branch));
    return { base: baseRef, stack: entries };
  }
}

/**
 * Produce ordered `git rebase --onto` commands for updating downstream stacked branches.
 */
export class StackRestackPlanner {
  constructor(workspace = process.cwd(), opts = {}) {
    this.inspector = new StackInspector(workspace, opts);
  }

  plan({ base = "main", branches = null } = {}) {
    const info = this.inspector.inspect({ base, branches });
    const steps = [];
    let prev = info.base;
    for (const item of info.stack) {
      steps.push({
        branch: item.branch,
        onto: prev,
        command: `git checkout ${item.branch} && git rebase ${prev}`,
      });
      prev = item.branch;
    }
    return { ...info, steps };
  }
}

/**
 * Audit `Co-authored-by` trailers across `base..head` commits.
 */
export class CoAuthorAuditor {
  constructor(workspace = process.cwd(), opts = {}) {
    this.workspace = path.resolve(workspace);
    this.runner = opts.runner || GitRunner.forWorkspace(this.workspace, opts);
  }

  check({ base = "main", head = "HEAD" } = {}) {
    const res = this.runner.runGit(
      ["log", "--format=%H%x1f%an%x1f%ae%x1f%B%x1e", `${base}..${head}`],
      { allowFailure: true },
    );
    const contributors = new Map();
    const trailers = new Map();
    if (res.status === 0 && res.stdout) {
      for (const chunk of res.stdout.split("\x1e")) {
        const trimmed = chunk.replace(/^\n+/, "");
        if (!trimmed) continue;
        const [sha = "", an = "", ae = "", ...bodyParts] = trimmed.split("\x1f");
        if (!sha) continue;
        const email = normalizeEmail(ae);
        if (email && !BOT_AUTHOR_RE.test(`${an} ${email}`) && !contributors.has(email)) {
          contributors.set(email, { name: an.trim() || email, email });
        }
        const body = bodyParts.join("\x1f");
        COAUTHOR_TRAILER_RE.lastIndex = 0;
        for (const m of body.matchAll(COAUTHOR_TRAILER_RE)) {
          const parsed = splitNameEmail(`${m[1]} <${m[2]}>`);
          if (parsed && !BOT_AUTHOR_RE.test(parsed.email) && !trailers.has(parsed.email)) {
            trailers.set(parsed.email, parsed);
          }
        }
      }
    }
    const survivingAuthors = [...contributors.values()];
    const existingTrailers = [...trailers.values()];
    const primaryEmail = survivingAuthors[0]?.email || null;
    const expectedSecondary = survivingAuthors.filter((a) => a.email !== primaryEmail);
    const missing = expectedSecondary.filter((a) => !trailers.has(a.email));
    return {
      base,
      head,
      surviving_authors: survivingAuthors,
      existing_trailers: existingTrailers,
      missing,
      findings: missing.map((p) => ({
        code: "COAUTHOR_MISSING",
        severity: "error",
        message: `Missing Co-authored-by trailer on ${head} for ${p.name} <${p.email}>.`,
      })),
    };
  }
}
