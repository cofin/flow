/**
 * @fileoverview Safe `git` and `gh` CLI wrappers, remote repository locator,
 * and index-free branch commit helper for Flow.
 */

import { execFile, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

const GIT_TIMEOUT_MS = 15_000;
const GIT_READ_TIMEOUT_MS = 4_000;
const HUB_TIMEOUT_MS = 30_000;

function splitGitLines(stdout) {
  return String(stdout || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function unquoteGitPath(raw) {
  let s = String(raw || "").trim();
  if (s.startsWith('"') && s.endsWith('"') && s.length >= 2) {
    s = s.slice(1, -1);
    const bytes = [];
    for (let i = 0; i < s.length; i += 1) {
      if (s[i] !== "\\" || i + 1 >= s.length) {
        for (const b of Buffer.from(s[i], "utf8")) bytes.push(b);
        continue;
      }
      const next = s[i + 1];
      if (/[0-7]/.test(next)) {
        const oct = s.slice(i + 1, i + 4).match(/^[0-7]{1,3}/)?.[0] || next;
        bytes.push(Number.parseInt(oct, 8));
        i += oct.length;
      } else {
        const map = { a: 7, b: 8, t: 9, n: 10, v: 11, f: 12, r: 13, '"': 34, "\\": 92 };
        const code = map[next];
        if (code !== undefined) bytes.push(code);
        else for (const b of Buffer.from(next, "utf8")) bytes.push(b);
        i += 1;
      }
    }
    s = Buffer.from(bytes).toString("utf8");
  }
  return s.replace(/\\/g, "/").replace(/^\.\//, "");
}

function parsePorcelainStatusPaths(stdout) {
  const paths = [];
  for (const rawLine of String(stdout || "").split(/\r?\n/)) {
    if (rawLine.length < 4) continue;
    let rel = rawLine.slice(3).trim();
    const arrowIdx = rel.indexOf(" -> ");
    if (arrowIdx >= 0) rel = rel.slice(arrowIdx + 4).trim();
    rel = unquoteGitPath(rel);
    if (rel) paths.push(rel);
  }
  return paths;
}

function parsePorcelainStatusZ(stdout) {
  const paths = [];
  const entries = String(stdout || "").split("\0");
  for (let i = 0; i < entries.length; i += 1) {
    const entry = entries[i];
    if (entry.length < 4) continue;
    const code = entry.slice(0, 2);
    const rel = entry.slice(3).replace(/\\/g, "/").replace(/^\.\//, "");
    if (rel) paths.push(rel);
    if ((code[0] === "R" || code[0] === "C") && i + 1 < entries.length) {
      i += 1;
    }
  }
  return paths;
}

function parsePorcelainWorktrees(stdout) {
  const items = [];
  let current = null;
  for (const rawLine of String(stdout || "").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) {
      if (current?.path) items.push(current);
      current = null;
      continue;
    }
    if (line.startsWith("worktree ")) {
      if (current?.path) items.push(current);
      current = { path: line.slice(9).trim(), head: null, branch: null };
    } else if (current && line.startsWith("HEAD ")) {
      current.head = line.slice(5).trim().slice(0, 7);
    } else if (current && line.startsWith("branch ")) {
      current.branch = line.slice(7).trim().replace(/^refs\/heads\//, "");
    }
  }
  if (current?.path) items.push(current);
  return items;
}

function parseDiffNumstat(stdout) {
  const entries = [];
  const files = [];
  let insertions = 0;
  let deletions = 0;
  for (const rawLine of String(stdout || "").split(/\r?\n/)) {
    if (!rawLine.trim()) continue;
    const parts = rawLine.split("\t");
    if (parts.length < 3) continue;
    const ins = Number.parseInt(parts[0], 10);
    const del = Number.parseInt(parts[1], 10);
    const parsedIns = Number.isFinite(ins) ? ins : 0;
    const parsedDel = Number.isFinite(del) ? del : 0;
    insertions += parsedIns;
    deletions += parsedDel;
    const pathPart = parts.slice(2).join("\t").trim();
    if (pathPart) {
      entries.push({ path: pathPart, insertions: parsedIns, deletions: parsedDel });
      if (!files.includes(pathPart)) files.push(pathPart);
    }
  }
  return { files, insertions, deletions, entries };
}

/**
 * Parse and normalize Git remote URLs and `owner/repo` slugs.
 */
export class RepoLocator {
  static fromRemoteUrl(url) {
    if (typeof url !== "string" || !url.trim()) return null;
    const cleaned = url.trim().replace(/\.git$/i, "").replace(/\/+$/, "");
    const scpMatch = cleaned.match(/^(?:[^@]+@)?([A-Za-z0-9.-]+):([A-Za-z0-9._/-]+)$/);
    if (scpMatch && !cleaned.includes("://")) {
      return `${scpMatch[1].toLowerCase()}/${scpMatch[2].replace(/^\/+/, "")}`;
    }
    try {
      const parsed = new URL(cleaned);
      const cleanPath = parsed.pathname.replace(/^\/+/, "").replace(/\/+$/, "");
      if (!parsed.hostname || !cleanPath) return null;
      return `${parsed.hostname.toLowerCase()}/${cleanPath}`;
    } catch {
      return null;
    }
  }

  static parseSlug(url) {
    const trimmed = String(url || "").trim();
    if (!trimmed) return null;
    const bare = trimmed.match(/^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$/);
    if (bare) {
      return { host: "github.com", owner: bare[1], repo: bare[2].replace(/\.git$/i, "") };
    }
    const ssh = trimmed.match(/^(?:ssh:\/\/)?(?:[^@]+@)?([^:/]+)[:/](.+?)(?:\.git)?$/i);
    if (ssh && !trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
      const parts = ssh[2].split("/").filter(Boolean);
      if (parts.length >= 2) {
        return { host: ssh[1].toLowerCase(), owner: parts[parts.length - 2], repo: parts[parts.length - 1] };
      }
    }
    try {
      const parsed = new URL(trimmed);
      const parts = parsed.pathname.replace(/\.git$/i, "").split("/").filter(Boolean);
      if (parts.length >= 2) {
        return { host: parsed.hostname.toLowerCase(), owner: parts[parts.length - 2], repo: parts[parts.length - 1] };
      }
    } catch {
      return null;
    }
    return null;
  }
}

/**
 * Resolve current author `{ email, name, slug }` from Git config or OS user info.
 *
 * @param {string | null} workspacePath
 * @param {{ env?: NodeJS.ProcessEnv }} [options]
 */
export function resolveGitIdentity(workspacePath, { env = process.env } = {}) {
  let email = "";
  let name = "";
  if (workspacePath && fs.existsSync(workspacePath)) {
    const git = GitRunner.forWorkspace(workspacePath, { timeoutMs: 2500, env });
    const emailRes = git.readConfig("user.email");
    if (emailRes.ok && emailRes.value) email = emailRes.value;
    const nameRes = git.readConfig("user.name");
    if (nameRes.ok && nameRes.value) name = nameRes.value;
  }
  let fallbackUser = env?.USER || env?.USERNAME || "author";
  if (!email && !name) {
    try {
      const info = os.userInfo();
      if (info?.username) fallbackUser = info.username;
    } catch {
      fallbackUser = env?.USER || env?.USERNAME || "author";
    }
  }
  const finalEmail = email || `${fallbackUser}@local`;
  const finalName = name || (email ? email.split("@")[0] : fallbackUser);
  const slug = String(finalEmail || finalName)
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64)
    .replace(/-+$/g, "") || "author";
  return { email: finalEmail, name: finalName, slug };
}

/**
 * Executes `git` and `gh` CLI commands without shell interpolation.
 */
export class GitRunner {
  static forWorkspace(root, { timeoutMs = GIT_READ_TIMEOUT_MS, env = null, hubBinary = null, remote = "origin" } = {}) {
    const resolvedRoot = root ? path.resolve(String(root)) : "";
    return new GitRunner(resolvedRoot, { timeoutMs, env, hubBinary, remote });
  }

  constructor(
    workspace = process.cwd(),
    { remote = "origin", hubBinary = null, timeoutMs = GIT_TIMEOUT_MS, env = null } = {},
  ) {
    this.workspace = workspace ? path.resolve(String(workspace)) : "";
    this.remote = remote;
    this.hubBinaryOverride = hubBinary || env?.FLOW_GH_BIN || process.env.FLOW_GH_BIN || null;
    this.defaultTimeoutMs = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : GIT_READ_TIMEOUT_MS;
    this.env = env;
    this._repoRoot = null;
    this._remoteMeta = undefined;
  }

  readGit(args, { timeoutMs = this.defaultTimeoutMs, env = this.env } = {}) {
    if (!this.workspace || !fs.existsSync(this.workspace)) {
      return { ok: false, status: 1, stdout: "", stderr: "" };
    }
    try {
      const res = spawnSync("git", ["-C", this.workspace, ...args], {
        cwd: this.workspace,
        env: env ? { ...process.env, ...env } : process.env,
        encoding: "utf8",
        shell: false,
        timeout: timeoutMs,
        windowsHide: true,
        maxBuffer: 10 * 1024 * 1024,
      });
      if (res.error || res.status !== 0) {
        return { ok: false, status: res.status ?? 1, stdout: "", stderr: res.stderr || res.error?.message || "" };
      }
      return { ok: true, status: 0, stdout: res.stdout || "", stderr: res.stderr || "" };
    } catch (err) {
      return { ok: false, status: 1, stdout: "", stderr: err instanceof Error ? err.message : "" };
    }
  }

  async readGitAsync(args, { timeoutMs = this.defaultTimeoutMs, env = this.env } = {}) {
    if (!this.workspace || !fs.existsSync(this.workspace)) {
      return { ok: false, status: 1, stdout: "", stderr: "" };
    }
    try {
      const res = await execFileAsync("git", ["-C", this.workspace, ...args], {
        cwd: this.workspace,
        env: env ? { ...process.env, ...env } : process.env,
        encoding: "utf8",
        timeout: timeoutMs,
        windowsHide: true,
        maxBuffer: 10 * 1024 * 1024,
      });
      return { ok: true, status: 0, stdout: res.stdout || "", stderr: res.stderr || "" };
    } catch (err) {
      return { ok: false, status: typeof err?.code === "number" ? err.code : 1, stdout: "", stderr: err?.stderr || err?.message || "" };
    }
  }

  runGit(args, { allowFailure = false, env = null, input = undefined, timeoutMs = GIT_TIMEOUT_MS, cwd = null } = {}) {
    const mergedEnv = env ? { ...process.env, ...env } : this.env ? { ...process.env, ...this.env } : process.env;
    const res = spawnSync("git", args, {
      cwd: cwd || this.workspace,
      env: mergedEnv,
      input,
      encoding: "utf8",
      shell: false,
      timeout: timeoutMs,
      windowsHide: true,
      maxBuffer: 10 * 1024 * 1024,
    });
    if (res.error) {
      throw new Error(`git ${args[0]} failed: ${res.error.message}`);
    }
    if (!allowFailure && res.status !== 0) {
      throw new Error(`git ${args.join(" ")} exited ${res.status}: ${(res.stderr || res.stdout || "").trim()}`);
    }
    return { status: res.status ?? 1, stdout: res.stdout || "", stderr: res.stderr || "" };
  }

  isGitRepo() {
    const res = this.readGit(["rev-parse", "--is-inside-work-tree"]);
    return res.ok && res.stdout.trim() === "true";
  }

  getRepoRoot() {
    if (this._repoRoot) return this._repoRoot;
    const res = this.readGit(["rev-parse", "--show-toplevel"]);
    this._repoRoot = res.ok && res.stdout.trim() ? path.resolve(res.stdout.trim()) : this.workspace;
    return this._repoRoot;
  }

  gitCommonDir() {
    const res = this.readGit(["rev-parse", "--git-common-dir"]);
    if (!res.ok) return { ok: false, value: "" };
    const raw = res.stdout.trim();
    if (!raw) return { ok: false, value: "" };
    const resolved = path.isAbsolute(raw) ? path.resolve(raw) : path.resolve(this.workspace, raw);
    return { ok: true, value: resolved };
  }

  statusPorcelain({ untrackedFiles = null, nul = false } = {}) {
    const args = ["status", "--porcelain"];
    if (nul) args.push("-z");
    if (untrackedFiles) args.push(`--untracked-files=${untrackedFiles}`);
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, paths: [], stdout: "" };
    const paths = nul ? parsePorcelainStatusZ(res.stdout) : parsePorcelainStatusPaths(res.stdout);
    return { ok: true, paths, stdout: res.stdout };
  }

  logShortShas(range = null, { limit = 20 } = {}) {
    const cleanRange = range ? String(range).trim() : "";
    const args = cleanRange ? ["log", "--format=%h", cleanRange] : ["log", "-n", String(limit), "--format=%h"];
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, shas: [] };
    return { ok: true, shas: splitGitLines(res.stdout) };
  }

  showNameOnly(sha) {
    const cleanSha = sha ? String(sha).trim() : "";
    if (!cleanSha) return { ok: false, files: [] };
    const res = this.readGit(["show", "--name-only", "--format=", cleanSha]);
    if (!res.ok) return { ok: false, files: [] };
    return { ok: true, files: splitGitLines(res.stdout) };
  }

  remoteUrl(name = this.remote) {
    const cleanName = name ? String(name).trim() : "origin";
    const res = this.readGit(["remote", "get-url", cleanName]);
    if (res.ok && res.stdout.trim()) return { ok: true, url: res.stdout.trim() };
    const cfgRes = this.readConfig(`remote.${cleanName}.url`);
    if (cfgRes.ok && cfgRes.value) return { ok: true, url: cfgRes.value };
    return { ok: false, url: "" };
  }

  getRemoteMeta() {
    if (this._remoteMeta !== undefined) return this._remoteMeta;
    const rem = this.remoteUrl(this.remote);
    this._remoteMeta = rem.ok ? RepoLocator.parseSlug(rem.url) : null;
    return this._remoteMeta;
  }

  diffCachedNames({ diffFilter = "ACMR", paths = [] } = {}) {
    const args = ["diff", "--cached"];
    if (diffFilter) args.push(`--diff-filter=${diffFilter}`);
    args.push("--name-only");
    if (Array.isArray(paths) && paths.length > 0) args.push("--", ...paths);
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, files: [] };
    return { ok: true, files: splitGitLines(res.stdout) };
  }

  diffNames(range = null, { cached = false, paths = [] } = {}) {
    const args = ["diff"];
    if (cached) args.push("--cached");
    args.push("--name-only");
    if (range) {
      const cleanRange = String(range).trim();
      if (cleanRange.startsWith("-")) return { ok: false, files: [] };
      if (cleanRange) args.push(cleanRange);
    }
    if (Array.isArray(paths) && paths.length > 0) args.push("--", ...paths);
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, files: [] };
    return { ok: true, files: splitGitLines(res.stdout) };
  }

  worktreeList() {
    const res = this.readGit(["worktree", "list", "--porcelain"]);
    if (!res.ok) return { ok: false, worktrees: [] };
    return { ok: true, worktrees: parsePorcelainWorktrees(res.stdout) };
  }

  revParseVerify(ref, { short = null, abbrevRef = false } = {}) {
    const cleanRef = ref ? String(ref).trim() : "";
    if (!cleanRef) return { ok: false, value: "" };
    const args = ["rev-parse", "--verify"];
    if (short !== null && short !== undefined) args.push(`--short=${short}`);
    if (abbrevRef) args.push("--abbrev-ref");
    args.push(cleanRef);
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, value: "" };
    return { ok: true, value: res.stdout.trim() };
  }

  diffNumstat(range = null) {
    const args = ["diff", "--numstat"];
    if (range) args.push(String(range));
    const res = this.readGit(args);
    if (!res.ok) return { ok: false, files: [], insertions: 0, deletions: 0, entries: [] };
    return { ok: true, ...parseDiffNumstat(res.stdout) };
  }

  diffTreeNumstat(ref = "HEAD") {
    const res = this.readGit(["diff-tree", "--no-commit-id", "--numstat", "-r", "--root", String(ref || "HEAD")]);
    if (!res.ok) return { ok: false, files: [], insertions: 0, deletions: 0, entries: [] };
    return { ok: true, ...parseDiffNumstat(res.stdout) };
  }

  readConfig(key) {
    const cleanKey = key ? String(key).trim() : "";
    if (!cleanKey) return { ok: false, value: "" };
    const res = this.readGit(["config", "--get", cleanKey]);
    if (!res.ok) return { ok: false, value: "" };
    return { ok: true, value: res.stdout.trim() };
  }

  shouldSignCommits() {
    const cfg = this.readConfig("commit.gpgsign");
    return cfg.ok && cfg.value.toLowerCase() === "true";
  }

  resolveHubBinary() {
    if (this.hubBinaryOverride) return String(this.hubBinaryOverride);
    return "gh";
  }

  runHub(args, { allowFailure = false, timeoutMs = HUB_TIMEOUT_MS, input = undefined, host = null } = {}) {
    const binary = this.resolveHubBinary();
    const meta = this.getRemoteMeta();
    const effectiveHost = host || (meta && meta.host && meta.host !== "github.com" ? meta.host : null);
    const finalArgs = [...args];
    if (effectiveHost && (args[0] === "api" || args[0] === "pr") && !args.includes("--hostname")) {
      if (args[0] === "api") {
        finalArgs.push("--hostname", effectiveHost);
      }
    }
    const res = spawnSync(binary, finalArgs, {
      cwd: this.workspace && fs.existsSync(this.workspace) ? this.getRepoRoot() : os.tmpdir(),
      env: this.env ? { ...process.env, ...this.env } : process.env,
      input,
      encoding: "utf8",
      shell: false,
      timeout: timeoutMs,
      windowsHide: true,
    });
    if (res.error) {
      throw new Error(`${binary} ${finalArgs[0] || ""} failed: ${res.error.message}`);
    }
    if (!allowFailure && res.status !== 0) {
      throw new Error(`${binary} ${finalArgs.join(" ")} exited ${res.status}: ${(res.stderr || res.stdout || "").trim()}`);
    }
    return { status: res.status ?? 1, stdout: res.stdout || "", stderr: res.stderr || "", binary };
  }

  runHubJson(args, opts = {}) {
    const res = this.runHub(args, opts);
    if (res.status !== 0) return null;
    const text = res.stdout.trim();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch (err) {
      throw new Error(`${res.binary} returned invalid JSON for '${args.join(" ")}': ${err.message}`);
    }
  }

  runApiJson(endpointPath, { method = "GET", fields = [], headers = [], allowFailure = false, host = null } = {}) {
    const args = ["api", endpointPath];
    if (method && method !== "GET") args.push("-X", method);
    for (const header of headers) args.push("-H", header);
    for (const [k, v] of fields) args.push("-f", `${k}=${v}`);
    return this.runHubJson(args, { allowFailure, host });
  }
}

/**
 * Commit exact workspace files onto any Git branch without touching HEAD or switching worktrees.
 * Uses `git commit --only` on the checked-out branch (isolating unrelated staged index changes),
 * refuses to mutate a branch checked out in a different linked worktree, and uses a temporary
 * `GIT_INDEX_FILE` + `commit-tree` + `update-ref` for all non-checked-out branches.
 */
export class IndexFreeBranchWriter {
  /**
   * @param {{
   *   git: GitRunner,
   *   effectiveRoot: string,
   *   targetBranch: string,
   *   baseBranch?: string,
   *   relPaths: string[],
   *   message: string,
   *   env?: NodeJS.ProcessEnv,
   * }} options
   */
  static commitWorkspacePaths({
    git,
    effectiveRoot,
    targetBranch,
    baseBranch = "main",
    relPaths,
    message,
    env = process.env,
  }) {
    const root = path.resolve(effectiveRoot);
    const cleanTarget = String(targetBranch || "").trim().replace(/^refs\/heads\//, "");
    if (!cleanTarget) throw new Error("targetBranch is required.");

    const wtRes = git.worktreeList();
    if (wtRes.ok) {
      const otherWt = wtRes.worktrees.find(
        (wt) => wt.branch === cleanTarget && wt.path && path.resolve(wt.path) !== root,
      );
      if (otherWt) {
        throw new Error(
          `Branch '${cleanTarget}' is checked out in linked worktree '${path.resolve(otherWt.path)}'; commit or switch there instead of updating its ref externally.`,
        );
      }
    }

    const identity = resolveGitIdentity(root, { env });
    const commitEnv = {
      ...process.env,
      ...(env || {}),
      GIT_AUTHOR_NAME: env?.GIT_AUTHOR_NAME || identity.name,
      GIT_AUTHOR_EMAIL: env?.GIT_AUTHOR_EMAIL || identity.email,
      GIT_COMMITTER_NAME: env?.GIT_COMMITTER_NAME || identity.name,
      GIT_COMMITTER_EMAIL: env?.GIT_COMMITTER_EMAIL || identity.email,
    };
    const signArgs = git.shouldSignCommits() ? ["-S"] : [];

    const headBranchRes = git.revParseVerify("HEAD", { abbrevRef: true });
    const currentBranch = headBranchRes.ok && headBranchRes.value !== "HEAD" ? headBranchRes.value : null;

    if (currentBranch === cleanTarget) {
      git.runGit(["add", "--", ...relPaths], { cwd: root, env: commitEnv });
      const statusCheck = git.readGit(["status", "--porcelain", "--", ...relPaths]);
      if (!statusCheck.ok || !statusCheck.stdout.trim()) {
        return git.revParseVerify("HEAD").value;
      }
      git.runGit(["commit", "--only", ...signArgs, "-m", message, "--", ...relPaths], {
        cwd: root,
        env: commitEnv,
      });
      return git.revParseVerify("HEAD").value;
    }

    const branchRef = `refs/heads/${cleanTarget}`;
    let parentSha = git.revParseVerify(branchRef).value;
    if (!parentSha) {
      parentSha =
        git.revParseVerify(`refs/remotes/origin/${cleanTarget}`).value ||
        git.revParseVerify(`refs/remotes/origin/${baseBranch}`).value ||
        git.revParseVerify(`refs/heads/${baseBranch}`).value ||
        git.revParseVerify("HEAD").value;
    }
    if (!parentSha) {
      throw new Error(`Unable to resolve base commit for branch '${cleanTarget}'.`);
    }

    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "flow-spec-idx-"));
    const tempIndex = path.join(tmpDir, "index");
    const idxEnv = { ...commitEnv, GIT_INDEX_FILE: tempIndex };
    try {
      git.runGit(["read-tree", parentSha], { cwd: root, env: idxEnv });
      for (const relPath of relPaths) {
        const absPath = path.join(root, relPath);
        const blobSha = git
          .runGit(["hash-object", "-w", "--", absPath], { cwd: root, env: idxEnv })
          .stdout.trim();
        git.runGit(["update-index", "--add", "--cacheinfo", `100644,${blobSha},${relPath}`], {
          cwd: root,
          env: idxEnv,
        });
      }
      const treeSha = git.runGit(["write-tree"], { cwd: root, env: idxEnv }).stdout.trim();
      const parentTree = git.revParseVerify(`${parentSha}^{tree}`).value;
      if (treeSha === parentTree) {
        if (!git.revParseVerify(branchRef).ok) {
          git.runGit(["update-ref", branchRef, parentSha], { cwd: root, env: commitEnv });
        }
        return parentSha;
      }
      const commitSha = git
        .runGit(["commit-tree", treeSha, "-p", parentSha, ...signArgs, "-m", message], {
          cwd: root,
          env: commitEnv,
        })
        .stdout.trim();
      git.runGit(["update-ref", branchRef, commitSha], { cwd: root, env: commitEnv });
      return commitSha;
    } finally {
      fs.rmSync(tmpDir, { recursive: true, force: true });
    }
  }
}
