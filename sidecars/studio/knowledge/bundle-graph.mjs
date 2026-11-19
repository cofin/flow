/**
 * @fileoverview Note-graph loader, health linter, and hash-guarded tri-state
 * claim corrector for OKF v0.2 bundles.
 */

import fs from "node:fs";
import path from "node:path";

import { extractH1, FrontmatterDocument, scanWikilinks } from "../core/frontmatter.mjs";
import { readTextSafe, sha256Hex, toPosixRelative, walkFiles, writeTextAtomic } from "../core/fs-io.mjs";

const RELATION_KEYS = Object.freeze(["corroborates", "complements", "extends", "contradicts", "supersedes"]);
const MENTION_TARGET_TYPES = new Set(["concept", "pattern", "synthesis"]);
const SYNTHESIS_TYPES = new Set(["synthesis", "index", "knowledge-base-index"]);
const HISTORICAL_DIR_RE = /(?:^|\/)(?:raw|research|specs)\//;

const FENCE_OPEN_RE = /^\s*(`{3,}|~{3,})/;
const FENCE_CLOSE_RE = /^\s*(`{3,}|~{3,})\s*$/;
const HEADING_LINE_RE = /^\s{0,3}#{1,6}(?:\s|$)/;
const TABLE_LINE_RE = /^\s*\|/;
const LINE_PREFIX_RE = /^(\s*(?:>\s*)*(?:(?:[-*+]|\d+[.)])\s+(?:\[[ xX~!-]\]\s+)?)?)/;

const STOP_WORDS = new Set([
  "about", "after", "against", "also", "been", "before", "being", "between", "both", "could", "does", "doing",
  "during", "each", "from", "further", "have", "having", "here", "into", "just", "might", "more", "most", "must",
  "once", "only", "other", "should", "some", "such", "than", "that", "their", "them", "then", "there", "these",
  "they", "this", "those", "through", "under", "until", "very", "what", "when", "where", "which", "while", "with",
  "would", "your",
]);

const GRAPH_META = new WeakMap();
const EDIT_META = new WeakMap();
const PLAN_META = new WeakMap();

/** Error thrown when a file changed on disk between claim planning and apply. */
export class ClaimConflictError extends Error {
  constructor(message, { conflictedFiles = [] } = {}) {
    super(message);
    this.name = "ClaimConflictError";
    this.conflictedFiles = conflictedFiles;
  }
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizePosix(rawPath) {
  return String(rawPath || "").trim().replace(/\\/g, "/").replace(/^\.\//, "").replace(/^\/+/, "");
}

function unwrapNoteTarget(rawValue) {
  let text = String(rawValue || "").trim();
  if (text.startsWith("[[") && text.endsWith("]]")) text = text.slice(2, -2).trim();
  const pipeIdx = text.indexOf("|");
  if (pipeIdx >= 0) text = text.slice(0, pipeIdx).trim();
  const hashIdx = text.indexOf("#");
  if (hashIdx >= 0) text = text.slice(0, hashIdx).trim();
  return text.replace(/\.md$/i, "");
}

function parseDateMillis(rawVal) {
  if (!rawVal) return null;
  const ms = Date.parse(String(rawVal).trim());
  return Number.isFinite(ms) ? ms : null;
}

function extractTokenSet(body) {
  const cleaned = String(body || "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`[^`\n]+`/g, " ")
    .toLowerCase();
  const tokens = new Set();
  for (const m of cleaned.matchAll(/\b[a-z][a-z0-9_-]{3,}\b/g)) {
    const w = m[0];
    if (!STOP_WORDS.has(w)) tokens.add(w);
  }
  return tokens;
}

function jaccardSimilarity(setA, setB) {
  if (!setA.size || !setB.size) return 0;
  let inter = 0;
  for (const x of setA) {
    if (setB.has(x)) inter += 1;
  }
  return inter / (setA.size + setB.size - inter);
}

function maskInlineCodeInLine(content) {
  return String(content || "").replace(/`[^`\n]+`/g, (span) => " ".repeat(span.length));
}

function replaceMatchedSpans(content, searchable, claimRe, replacer) {
  claimRe.lastIndex = 0;
  let out = "";
  let cursor = 0;
  let match;
  while ((match = claimRe.exec(searchable)) !== null) {
    out += content.slice(cursor, match.index) + replacer(match[0]);
    cursor = match.index + match[0].length;
  }
  out += content.slice(cursor);
  return out;
}

function buildClaimRegex(claimText) {
  const escaped = escapeRegExp(claimText);
  const startBoundary = /^[A-Za-z0-9_]/.test(claimText) ? "\\b" : "";
  const endBoundary = /[A-Za-z0-9_]$/.test(claimText) ? "\\b" : "";
  return new RegExp(`${startBoundary}${escaped}${endBoundary}`, "gi");
}

function formatCanonicalLink(graph, sourceNote, canonicalNote) {
  const rel = sourceNote?.path && canonicalNote?.path
    ? path.posix.relative(path.posix.dirname(sourceNote.path), canonicalNote.path)
    : canonicalNote.path;
  const cleanRel = rel.startsWith(".") ? rel : `./${rel}`;
  return `See [${canonicalNote.title || canonicalNote.name}](${cleanRel}).`;
}

function replaceRestatementSentences(content, claimRe, linkSentence, searchable) {
  claimRe.lastIndex = 0;
  if (!claimRe.test(searchable)) return content;
  const sentences = content.split(/(?<=[.!?])\s+/);
  let replaced = false;
  const next = sentences.map((s) => {
    const sSearch = maskInlineCodeInLine(s);
    claimRe.lastIndex = 0;
    if (claimRe.test(sSearch)) {
      replaced = true;
      return linkSentence;
    }
    return s;
  });
  return replaced ? next.join(" ") : linkSentence;
}

/**
 * Loads an OKF bundle note graph with wikilinks and typed relation edges.
 */
export class BundleGraph {
  static load(bundleDir, { files = null, workspaceRoot = null } = {}) {
    const absBundle = path.resolve(bundleDir);
    const absWs = workspaceRoot ? path.resolve(workspaceRoot) : path.resolve(absBundle, "../..");
    const targetFiles = Array.isArray(files)
      ? files.map((f) => path.resolve(f))
      : walkFiles(absBundle, { extensions: [".md"], maxDepth: 6 });

    const notes = [];
    for (const absPath of targetFiles) {
      if (!fs.existsSync(absPath)) continue;
      const relBundle = normalizePosix(toPosixRelative(absBundle, absPath));
      if (relBundle.startsWith(".") || relBundle === "log.md") continue;
      const raw = readTextSafe(absPath) || "";
      const doc = FrontmatterDocument.parse(raw);
      const name = path.basename(absPath, ".md");
      const title = doc.text("title") || extractH1(doc.body) || name;
      const aliases = doc.textList("aliases");
      const type = (doc.text("type") || (relBundle.includes("specs/") ? "spec" : "concept")).toLowerCase();
      const status = (doc.text("status") || "draft").toLowerCase();
      const updated = doc.text("updated") || doc.text("verified_at") || "";
      const relations = {};
      for (const relKey of RELATION_KEYS) {
        const list = doc.textList(relKey);
        if (list.length > 0) relations[relKey] = list;
      }

      notes.push({
        name,
        path: relBundle,
        relPath: toPosixRelative(absWs, absPath),
        absPath,
        title,
        aliases,
        type,
        status,
        updated,
        body: doc.body,
        bodyStartLine: doc.bodyLine || 1,
        relations,
        outLinks: scanWikilinks(doc.body).map((wl) => ({ ...wl, resolved: null })),
      });
    }

    const byName = new Map();
    for (const note of notes) {
      for (const key of [note.name, normalizePosix(note.path).replace(/\.md$/i, ""), note.title, ...note.aliases]) {
        const norm = String(key || "").trim().toLowerCase();
        if (norm && !byName.has(norm)) byName.set(norm, note);
      }
    }

    for (const note of notes) {
      for (const link of note.outLinks) {
        const clean = unwrapNoteTarget(link.target).toLowerCase();
        const hit = byName.get(clean) || null;
        if (hit) link.resolved = hit.path;
      }
    }

    const graph = { bundleDir: absBundle, workspaceRoot: absWs, notes, byName };
    GRAPH_META.set(graph, { filesProvided: Array.isArray(files) });
    return graph;
  }
}

/**
 * Inspects an OKF `BundleGraph` for broken wikilinks, unlinked mentions, stale syntheses, and duplicates.
 */
export class BundleGraphLinter {
  static lint(graph, { duplicateThreshold = 0.72 } = {}) {
    const notes = Array.isArray(graph?.notes) ? graph.notes : [];
    const byName = graph?.byName || new Map();
    const byPath = new Map(notes.map((n) => [n.path, n]));

    const wantedCounts = new Map();
    for (const note of notes) {
      for (const link of note.outLinks || []) {
        if (link.resolved) continue;
        const target = unwrapNoteTarget(link.target);
        if (!target) continue;
        const k = target.toLowerCase();
        const prev = wantedCounts.get(k) || { target, count: 0, referencedFrom: [] };
        prev.count += 1;
        if (!prev.referencedFrom.includes(note.path)) prev.referencedFrom.push(note.path);
        wantedCounts.set(k, prev);
      }
    }
    const wanted_concepts = [...wantedCounts.values()].sort((a, b) => b.count - a.count || a.target.localeCompare(b.target));

    const targetSpecs = [];
    for (const n of notes) {
      if (!MENTION_TARGET_TYPES.has(n.type)) continue;
      if (HISTORICAL_DIR_RE.test(n.path)) continue;
      const terms = [...new Set([n.title, ...(n.aliases || [])].map((t) => String(t || "").trim()).filter((t) => t.length >= 4))];
      if (terms.length === 0) continue;
      targetSpecs.push({
        targetNote: n,
        matchers: terms.map((term) => ({ term, re: new RegExp(`\\b${escapeRegExp(term)}\\b`, "i") })),
      });
    }

    const unlinked_mentions = [];
    for (const sourceNote of notes) {
      if (HISTORICAL_DIR_RE.test(sourceNote.path)) continue;
      const alreadyLinked = new Set((sourceNote.outLinks || []).map((l) => l.resolved).filter(Boolean));
      const lines = String(sourceNote.body || "").split("\n");
      let activeFence = null;
      for (let i = 0; i < lines.length; i += 1) {
        const lineText = lines[i];
        const fenceMatch = lineText.match(FENCE_OPEN_RE);
        if (fenceMatch) {
          if (!activeFence) activeFence = fenceMatch[1][0];
          else if (FENCE_CLOSE_RE.test(lineText)) activeFence = null;
          continue;
        }
        if (activeFence || !lineText.trim() || HEADING_LINE_RE.test(lineText)) continue;
        const masked = lineText.replace(/\[\[[^\]]+\]\]/g, " ").replace(/\[[^\]]+\]\([^)]+\)/g, " ").replace(/`[^`\n]+`/g, " ");
        for (const { targetNote, matchers } of targetSpecs) {
          if (targetNote.path === sourceNote.path || alreadyLinked.has(targetNote.path)) continue;
          const hit = matchers.find((m) => m.re.test(masked));
          if (hit) {
            unlinked_mentions.push({
              path: sourceNote.path,
              line: (sourceNote.bodyStartLine || 1) + i,
              target: targetNote.path,
              targetTitle: targetNote.title,
              matched: hit.term,
            });
          }
        }
      }
    }

    const stale_syntheses = [];
    for (const note of notes) {
      if (!SYNTHESIS_TYPES.has(note.type)) continue;
      const synthMs = parseDateMillis(note.updated);
      if (synthMs === null) continue;
      const newerLinks = [];
      for (const l of note.outLinks || []) {
        const target = l.resolved ? byPath.get(l.resolved) : null;
        if (!target || target.path === note.path) continue;
        const tMs = parseDateMillis(target.updated);
        if (tMs !== null && synthMs < tMs) newerLinks.push({ path: target.path, updated: target.updated, millis: tMs });
      }
      if (newerLinks.length > 0) {
        stale_syntheses.push({
          path: note.path,
          updated: note.updated,
          newerLinks: newerLinks.sort((a, b) => b.millis - a.millis).map(({ path: p, updated }) => ({ path: p, updated })),
        });
      }
    }

    const nameSets = notes.map((n) => new Set([n.title, ...(n.aliases || [])].map((s) => String(s || "").trim().toLowerCase()).filter(Boolean)));
    const tokenSets = notes.map((n) => extractTokenSet(n.body));
    const duplicate_candidates = [];
    for (let i = 0; i < notes.length; i += 1) {
      for (let j = i + 1; j < notes.length; j += 1) {
        const sharedName = [...nameSets[i]].some((name) => nameSets[j].has(name));
        const jaccard = jaccardSimilarity(tokenSets[i], tokenSets[j]);
        if (sharedName || jaccard >= duplicateThreshold) {
          const pairPaths = [notes[i].path, notes[j].path].sort();
          duplicate_candidates.push({
            paths: pairPaths,
            pathA: pairPaths[0],
            pathB: pairPaths[1],
            score: sharedName ? 1 : Number(jaccard.toFixed(4)),
            reason: sharedName ? "shared_title_or_alias" : "content_similarity",
          });
        }
      }
    }

    void byName;
    return { wanted_concepts, unlinked_mentions, stale_syntheses, duplicate_candidates };
  }
}

/**
 * Plans and applies hash-guarded claim corrections across authoritative, restatement, and historical docs.
 */
export class TriStateClaimCorrector {
  static classify(note, canonicalPath = null) {
    const pathCandidates = typeof note === "string" ? [note] : [note?.relPath, note?.path].filter(Boolean);
    const status = String(note?.status || "").trim().toLowerCase();
    if (status === "deprecated" || status === "archived") return "historical";
    if (pathCandidates.some((p) => HISTORICAL_DIR_RE.test(normalizePosix(p)))) return "historical";
    if (canonicalPath) {
      const normCanon = normalizePosix(canonicalPath);
      if (
        (note?.absPath && path.isAbsolute(canonicalPath) && path.resolve(canonicalPath) === path.resolve(note.absPath)) ||
        pathCandidates.some((p) => normalizePosix(p) === normCanon)
      ) {
        return "authoritative";
      }
    }
    return "restatement";
  }

  static plan(graph, { claim, replacement, canonicalPath }) {
    const claimText = String(claim ?? "").trim();
    if (!claimText) throw new Error("Claim text must not be empty.");
    const replacementText = String(replacement ?? "");
    const notes = Array.isArray(graph?.notes) ? graph.notes : [];
    const normCanon = normalizePosix(canonicalPath);

    const canonicalNote = notes.find((note) => {
      if (note.absPath && canonicalPath && path.resolve(canonicalPath) === path.resolve(note.absPath)) return true;
      return normalizePosix(note.path) === normCanon || normalizePosix(note.relPath) === normCanon;
    });
    if (!canonicalNote) throw new Error(`Canonical note not found in bundle graph: ${canonicalPath}`);
    if (TriStateClaimCorrector.classify(canonicalNote, canonicalNote.path) === "historical") {
      throw new Error(`Canonical note cannot be a historical document: ${canonicalNote.path}`);
    }

    const claimRe = buildClaimRegex(claimText);
    const maskInlineCode = !claimText.includes("`");
    const edits = [];
    const skipped = [];

    for (const note of notes) {
      const rawText = note.absPath ? readTextSafe(note.absPath) : note.body;
      if (rawText === null) continue;
      const role = TriStateClaimCorrector.classify(note, canonicalNote.path);
      const normalizedText = String(rawText).replace(/\r\n/g, "\n");
      const lines = normalizedText.split("\n");
      const bodyStart = note.bodyStartLine || 1;
      const contentSha = sha256Hex(rawText);

      let activeFence = null;
      for (let idx = bodyStart - 1; idx < lines.length; idx += 1) {
        const line = lines[idx];
        const lineNum = idx + 1;
        const fenceMatch = line.match(FENCE_OPEN_RE);
        if (fenceMatch) {
          if (!activeFence) activeFence = { char: fenceMatch[1][0], len: fenceMatch[1].length };
          else if (fenceMatch[1][0] === activeFence.char && fenceMatch[1].length >= activeFence.len && FENCE_CLOSE_RE.test(line)) activeFence = null;
          continue;
        }
        if (activeFence !== null || HEADING_LINE_RE.test(line) || TABLE_LINE_RE.test(line)) continue;

        const prefixMatch = line.match(LINE_PREFIX_RE);
        const prefix = prefixMatch ? prefixMatch[1] : "";
        const content = line.slice(prefix.length);
        const searchable = maskInlineCode ? maskInlineCodeInLine(content) : content;
        claimRe.lastIndex = 0;
        if (!claimRe.test(searchable)) continue;

        if (role === "historical") {
          skipped.push({ path: note.path, line: lineNum, role: "historical" });
          continue;
        }

        let newContent;
        if (role === "authoritative") {
          if (maskInlineCode) {
            newContent = replaceMatchedSpans(content, searchable, claimRe, () => replacementText);
          } else {
            claimRe.lastIndex = 0;
            newContent = content.replace(claimRe, () => replacementText);
          }
        } else {
          const linkSentence = formatCanonicalLink(graph, note, canonicalNote);
          newContent = replaceRestatementSentences(content, claimRe, linkSentence, searchable);
        }

        const edit = {
          path: note.path,
          line: lineNum,
          role,
          before: line,
          after: `${prefix}${newContent}`,
          content_sha256: contentSha,
        };
        if (note.absPath) EDIT_META.set(edit, { absPath: note.absPath });
        edits.push(edit);
      }
    }

    const plan = { canonical: canonicalNote.path, edits, skipped };
    PLAN_META.set(plan, { workspaceRoot: graph?.workspaceRoot || null, bundleDir: graph?.bundleDir || null });
    return plan;
  }

  static apply(plan, { dryRun = false } = {}) {
    const edits = Array.isArray(plan?.edits) ? plan.edits : [];
    if (edits.length === 0) {
      return { ok: true, dry_run: Boolean(dryRun), applied: false, written_files: [], edit_count: 0 };
    }
    const planMeta = PLAN_META.get(plan) || {};
    const rootFallback = planMeta.workspaceRoot || planMeta.bundleDir || process.cwd();
    const byFile = new Map();

    for (const edit of edits) {
      const editMeta = EDIT_META.get(edit);
      const absPath = editMeta?.absPath
        ? path.resolve(editMeta.absPath)
        : path.isAbsolute(edit.path)
          ? path.resolve(edit.path)
          : path.resolve(rootFallback, edit.path);
      if (!byFile.has(absPath)) byFile.set(absPath, { displayPath: edit.path, fileEdits: [] });
      byFile.get(absPath).fileEdits.push(edit);
    }

    const conflictedFiles = [];
    const preparedWrites = [];
    for (const [absPath, { displayPath, fileEdits }] of byFile.entries()) {
      let currentRaw;
      try {
        currentRaw = fs.readFileSync(absPath, "utf8");
      } catch {
        conflictedFiles.push(displayPath);
        continue;
      }
      const currentSha = sha256Hex(currentRaw);
      if (fileEdits.some((edit) => edit.content_sha256 !== currentSha)) {
        conflictedFiles.push(displayPath);
        continue;
      }
      const eol = currentRaw.includes("\r\n") ? "\r\n" : "\n";
      const lines = currentRaw.replace(/\r\n/g, "\n").split("\n");
      for (const edit of fileEdits) {
        const lineIdx = Number(edit.line) - 1;
        if (lineIdx >= 0 && lineIdx < lines.length && lines[lineIdx] === edit.before) lines[lineIdx] = edit.after;
        else if (lineIdx >= 0 && lineIdx < lines.length && lines[lineIdx].includes(edit.before)) {
          lines[lineIdx] = lines[lineIdx].replace(edit.before, () => edit.after);
        }
      }
      preparedWrites.push({ absPath, displayPath, nextText: lines.join(eol) });
    }

    if (conflictedFiles.length > 0) {
      throw new ClaimConflictError(`Claim correction aborted because file(s) changed after planning: ${conflictedFiles.join(", ")}`, {
        conflictedFiles,
      });
    }
    if (dryRun) {
      return { ok: true, dry_run: true, applied: false, written_files: [], edit_count: edits.length };
    }

    const writtenFiles = [];
    for (const { absPath, displayPath, nextText } of preparedWrites) {
      writeTextAtomic(absPath, nextText);
      writtenFiles.push(displayPath);
    }
    return { ok: true, dry_run: false, applied: writtenFiles.length > 0, written_files: writtenFiles, edit_count: edits.length };
  }
}
