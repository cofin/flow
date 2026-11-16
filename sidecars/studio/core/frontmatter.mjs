/**
 * Shared OKF v0.2 YAML frontmatter codec, fence-aware heading checks,
 * truth-block extractor, wikilink scanner, and prompt-injection fences.
 */

const FRONTMATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/;
const TRUTH_RE = /<!--\s*truth:\s*start\s*-->([\s\S]*?)<!--\s*truth:\s*end\s*-->/g;
const HEADING_RE = /^(#{1,6})\s+(.+?)\s*$/;
const WIKILINK_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/g;
const YAML_KEY_LINE_RE = /^([A-Za-z_][\w-]*):(.*)$/;

/**
 * Parse scalar or inline `[a, b]` YAML value.
 *
 * @param {string} raw
 * @returns {any}
 */
export function parseYamlScalarOrInlineArray(raw) {
  const val = String(raw || "").trim();
  if (val.startsWith("[") && val.endsWith("]")) {
    const inner = val.slice(1, -1).trim();
    if (!inner) return [];
    return inner
      .split(",")
      .map((s) => s.trim().replace(/^["']|["']$/g, ""))
      .filter(Boolean);
  }
  const unquoted = val.replace(/^["']|["']$/g, "");
  if (unquoted === "true") return true;
  if (unquoted === "false") return false;
  if (unquoted === "null" || unquoted === "~") return null;
  return unquoted;
}

/**
 * Parse a lightweight OKF YAML subset preserving scalar types, lists, and shallow object lists.
 *
 * @param {string} yamlText
 * @returns {Record<string, any>}
 */
export function parseYamlSubset(yamlText) {
  /** @type {Record<string, any>} */
  const out = {};
  const lines = String(yamlText || "").split("\n");
  let idx = 0;

  while (idx < lines.length) {
    const line = lines[idx];
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !line.includes(":") || /^\s/.test(line)) {
      idx += 1;
      continue;
    }
    const colon = line.indexOf(":");
    const key = line.slice(0, colon).trim();
    const rest = line.slice(colon + 1).trim();

    if (rest) {
      out[key] = parseYamlScalarOrInlineArray(rest);
      idx += 1;
      continue;
    }

    /** @type {any[]} */
    const arr = [];
    idx += 1;
    while (idx < lines.length) {
      const sub = lines[idx];
      const subTrim = sub.trim();
      if (!subTrim || subTrim.startsWith("#")) {
        idx += 1;
        continue;
      }
      if (!/^\s/.test(sub)) break;
      if (subTrim.startsWith("- ")) {
        const itemBody = subTrim.slice(2).trim();
        if (itemBody.includes(":") && !itemBody.startsWith('"') && !itemBody.startsWith("'")) {
          /** @type {Record<string, any>} */
          const obj = {};
          const cIdx = itemBody.indexOf(":");
          obj[itemBody.slice(0, cIdx).trim()] = parseYamlScalarOrInlineArray(itemBody.slice(cIdx + 1).trim());
          const itemIndent = sub.length - sub.trimStart().length;
          idx += 1;
          while (idx < lines.length) {
            const nested = lines[idx];
            const nestedTrim = nested.trim();
            if (!nestedTrim || nestedTrim.startsWith("#")) {
              idx += 1;
              continue;
            }
            const nestedIndent = nested.length - nested.trimStart().length;
            if (nestedIndent <= itemIndent || nestedTrim.startsWith("- ")) break;
            const nc = nestedTrim.indexOf(":");
            if (nc > 0) {
              obj[nestedTrim.slice(0, nc).trim()] = parseYamlScalarOrInlineArray(nestedTrim.slice(nc + 1).trim());
            }
            idx += 1;
          }
          arr.push(obj);
          continue;
        }
        arr.push(parseYamlScalarOrInlineArray(itemBody));
      }
      idx += 1;
    }
    out[key] = arr;
  }
  return out;
}

/**
 * Parse YAML frontmatter and body from Markdown text.
 *
 * @param {string} rawText
 * @returns {{ frontmatter: Record<string, any>, data: Record<string, any>, body: string, hasFrontmatter: boolean, frontmatterEndLine: number, bodyLine: number }}
 */
export function parseFrontmatter(rawText) {
  const normalized = String(rawText || "").replace(/\r\n/g, "\n");
  const match = normalized.match(FRONTMATTER_RE);
  if (!match) {
    return {
      frontmatter: {},
      data: {},
      body: normalized,
      hasFrontmatter: false,
      frontmatterEndLine: 0,
      bodyLine: 1,
    };
  }
  const yamlText = match[1];
  const body = match[2];
  const fmLines = yamlText.split("\n").length;
  const parsed = parseYamlSubset(yamlText);
  return {
    frontmatter: parsed,
    data: parsed,
    body,
    hasFrontmatter: true,
    frontmatterEndLine: fmLines + 2,
    bodyLine: fmLines + 3,
  };
}

/**
 * Typed wrapper around parsed frontmatter + Markdown body.
 */
export class FrontmatterDocument {
  /**
   * @param {{ data: Record<string, any>, body: string, hasFrontmatter: boolean, frontmatterEndLine: number, bodyLine: number }} parsed
   */
  constructor(parsed) {
    this.data = parsed.data;
    this.frontmatter = parsed.frontmatter;
    this.body = parsed.body;
    this.hasFrontmatter = parsed.hasFrontmatter;
    this.frontmatterEndLine = parsed.frontmatterEndLine;
    this.bodyLine = parsed.bodyLine;
  }

  /**
   * @param {string} rawText
   * @returns {FrontmatterDocument}
   */
  static parse(rawText) {
    return new FrontmatterDocument(parseFrontmatter(rawText));
  }

  /**
   * @param {string} key
   * @returns {string}
   */
  text(key) {
    const v = this.data?.[key];
    if (v === null || v === undefined || Array.isArray(v) || typeof v === "object") return "";
    return String(v).trim();
  }

  /**
   * @param {string} key
   * @returns {boolean}
   */
  bool(key) {
    const v = this.data?.[key];
    if (typeof v === "boolean") return v;
    return String(v || "").trim().toLowerCase() === "true";
  }

  /**
   * @param {string} key
   * @returns {number | null}
   */
  integer(key) {
    const v = this.data?.[key];
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isInteger(n) ? n : null;
  }

  /**
   * @param {string} key
   * @returns {string[]}
   */
  textList(key) {
    const v = this.data?.[key];
    if (!Array.isArray(v)) return [];
    return v.map((item) => String(item || "").trim()).filter(Boolean);
  }
}

/**
 * Format and surgically update YAML frontmatter keys in-place without clobbering unrelated fields.
 */
export class FrontmatterCodec {
  /**
   * @param {unknown} val
   * @returns {string}
   */
  static formatScalar(val) {
    if (val === null || val === undefined) return "null";
    if (typeof val === "boolean" || typeof val === "number") return String(val);
    const str = String(val);
    if (!str) return '""';
    if (/^[A-Za-z0-9_./@-]+$/.test(str) && !["true", "false", "null", "yes", "no"].includes(str.toLowerCase())) {
      return str;
    }
    return JSON.stringify(str);
  }

  /**
   * Format a key assignment (scalar or array of scalars) as YAML line(s).
   *
   * @param {string} key
   * @param {any} value
   * @returns {string[]}
   */
  static formatFieldLines(key, value) {
    if (Array.isArray(value)) {
      if (value.length === 0) return [`${key}: []`];
      return [`${key}:`, ...value.map((item) => `  - ${FrontmatterCodec.formatScalar(item)}`)];
    }
    return [`${key}: ${FrontmatterCodec.formatScalar(value)}`];
  }

  /**
   * Update/insert keys in YAML frontmatter while preserving all existing unrelated keys and ordering.
   *
   * @param {string} rawText
   * @param {Record<string, any>} updates
   * @returns {string}
   */
  static updateKeys(rawText, updates) {
    const eol = String(rawText).includes("\r\n") ? "\r\n" : "\n";
    const normalized = String(rawText || "").replace(/\r\n/g, "\n");
    const entries = Object.entries(updates || {});
    if (entries.length === 0) return rawText;

    const match = normalized.match(/^---\n([\s\S]*?)\n---(?:\n([\s\S]*))?$/);
    if (!match) {
      const fmLines = ["---"];
      for (const [k, v] of entries) {
        fmLines.push(...FrontmatterCodec.formatFieldLines(k, v));
      }
      fmLines.push("---", "");
      return `${fmLines.join("\n")}${normalized}`.replace(/\n/g, eol);
    }

    const yamlLines = match[1].split("\n");
    const body = match[2] ?? "";
    const remaining = new Map(entries);
    /** @type {string[]} */
    const nextYaml = [];
    let i = 0;

    while (i < yamlLines.length) {
      const line = yamlLines[i];
      const keyMatch = line.match(YAML_KEY_LINE_RE);
      if (keyMatch && remaining.has(keyMatch[1])) {
        const key = keyMatch[1];
        const nextVal = remaining.get(key);
        remaining.delete(key);
        nextYaml.push(...FrontmatterCodec.formatFieldLines(key, nextVal));
        i += 1;
        while (i < yamlLines.length && (/^\s+/.test(yamlLines[i]) || yamlLines[i].trim() === "")) {
          i += 1;
        }
        continue;
      }
      nextYaml.push(line);
      i += 1;
    }

    for (const [key, val] of remaining.entries()) {
      nextYaml.push(...FrontmatterCodec.formatFieldLines(key, val));
    }

    const joined = `---\n${nextYaml.join("\n")}\n---\n${body}`;
    return eol === "\r\n" ? joined.replace(/\n/g, "\r\n") : joined;
  }
}

/**
 * Extract concatenated `<!-- truth: start --> ... <!-- truth: end -->` content.
 *
 * @param {string} body
 * @returns {string | null}
 */
export function extractTruthBlock(body) {
  const blocks = [];
  let match;
  TRUTH_RE.lastIndex = 0;
  while ((match = TRUTH_RE.exec(String(body || ""))) !== null) {
    const cleaned = match[1].trim();
    if (cleaned) blocks.push(cleaned);
  }
  return blocks.length > 0 ? blocks.join("\n") : null;
}

/**
 * Extract Markdown headings outside fenced code blocks.
 *
 * @param {string} body
 * @param {{ minLevel?: number, maxLevel?: number, lineOffset?: number }} [options]
 * @returns {Array<{ level: number, text: string, line: number }>}
 */
export function extractHeadings(body, { minLevel = 1, maxLevel = 6, lineOffset = 0 } = {}) {
  const lines = String(body || "").replace(/\r\n/g, "\n").split("\n");
  /** @type {Array<{ level: number, text: string, line: number }>} */
  const headings = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const hm = line.match(HEADING_RE);
    if (hm) {
      const level = hm[1].length;
      if (level >= minLevel && level <= maxLevel) {
        headings.push({ level, text: hm[2], line: lineOffset + i + 1 });
      }
    }
  }
  return headings;
}

/**
 * Check that all `requiredHeadings` appear in relative order within `presentHeadings`.
 *
 * @param {Array<string | { text: string }>} presentHeadings
 * @param {string[]} requiredHeadings
 * @returns {boolean}
 */
export function hasOrderedRequiredHeadings(presentHeadings, requiredHeadings) {
  const names = presentHeadings.map((h) => (typeof h === "string" ? h.trim() : String(h?.text || "").trim()));
  let cursor = 0;
  for (const target of requiredHeadings) {
    const foundIdx = names.indexOf(target, cursor);
    if (foundIdx === -1) return false;
    cursor = foundIdx + 1;
  }
  return true;
}

/**
 * Extract Obsidian/OKF `[[target#heading|alias]]` wikilinks outside code fences and inline code spans.
 *
 * @param {string} body
 * @returns {Array<{ target: string, heading: string | null, alias: string | null }>}
 */
export function scanWikilinks(body) {
  const out = [];
  let inFence = false;
  for (const rawLine of String(body || "").replace(/\r\n/g, "\n").split("\n")) {
    if (/^\s*(```|~~~)/.test(rawLine)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const strippedCode = rawLine.replace(/`[^`]*`/g, "");
    WIKILINK_RE.lastIndex = 0;
    let m;
    while ((m = WIKILINK_RE.exec(strippedCode)) !== null) {
      const target = String(m[1] || "").trim();
      if (!target) continue;
      out.push({
        target,
        heading: m[2] ? m[2].trim() : null,
        alias: m[3] ? m[3].trim() : null,
      });
    }
  }
  return out;
}

/**
 * Fence external/cross-workspace text in an explicit data-only wrapper for prompt inclusion.
 *
 * @param {string} text
 * @param {string} [sourceLabel]
 * @returns {string}
 */
export function wrapUntrustedSnippet(text, sourceLabel = "external") {
  const safeText = String(text || "").replace(/<\/?untrusted-snippet[^>]*>/gi, "[redacted-tag]");
  const safeSource = String(sourceLabel || "external").replace(/[^A-Za-z0-9._:/@-]/g, "_");
  return `<untrusted-snippet source="${safeSource}">\n${safeText}\n</untrusted-snippet>`;
}

/**
 * Strip HTML/embed tags and control characters from single-line system messages.
 *
 * @param {string} text
 * @returns {string}
 */
export function sanitizeSystemMessage(text) {
  return String(text || "")
    .replace(/<[^>]{1,120}>/g, "")
    .replace(/\r/g, "")
    .trim();
}
