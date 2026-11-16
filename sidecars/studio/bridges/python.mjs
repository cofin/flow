/**
 * Python environment manager and entrypoint detector for Flow Studio.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

import { whichSync } from "../core/fs-io.mjs";

const IS_WIN = process.platform === "win32";

export { whichSync };

/**
 * Resolve a binary inside a virtual environment directory.
 *
 * @param {string} venvDir
 * @param {string} name
 * @returns {string | null}
 */
export function resolveVenvExecutable(venvDir, name) {
  const binSubdir = IS_WIN ? "Scripts" : "bin";
  const candidates = IS_WIN ? [`${name}.exe`, `${name}.cmd`, name] : [name];
  for (const fileName of candidates) {
    const full = path.join(venvDir, binSubdir, fileName);
    if (fs.existsSync(full)) return full;
  }
  return null;
}

/**
 * Parse TOML section headers and key-value assignments relevant to Python managers and scripts.
 *
 * @param {string} tomlText
 */
export function parseTomlSections(tomlText) {
  /** @type {Record<string, Record<string, string>>} */
  const sections = {};
  /** @type {Set<string>} */
  const rawSections = new Set();
  let currentSection = "";

  for (const raw of String(tomlText || "").split(/\r?\n/)) {
    const trimmed = raw.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const headerMatch = trimmed.match(/^\[([^\[\]]+)\]$/);
    if (headerMatch) {
      currentSection = headerMatch[1].trim();
      rawSections.add(currentSection);
      if (!sections[currentSection]) sections[currentSection] = {};
      continue;
    }
    if (trimmed.startsWith("[[")) {
      currentSection = "";
      continue;
    }
    if (!currentSection) continue;

    const eqIdx = trimmed.indexOf("=");
    if (eqIdx <= 0) continue;
    const key = trimmed.slice(0, eqIdx).trim().replace(/^["']|["']$/g, "");
    let value = trimmed.slice(eqIdx + 1).trim();
    const commentIdx = findUnquotedHash(value);
    if (commentIdx >= 0) value = value.slice(0, commentIdx).trim();
    value = value.replace(/^["']|["']$/g, "");
    if (key) sections[currentSection][key] = value;
  }
  return { sections, rawSections };
}

function findUnquotedHash(text) {
  let inSingle = false;
  let inDouble = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (ch === "'" && !inDouble) inSingle = !inSingle;
    else if (ch === '"' && !inSingle && text[i - 1] !== "\\") inDouble = !inDouble;
    else if (ch === "#" && !inSingle && !inDouble) return i;
  }
  return -1;
}

function hasSectionPrefix(rawSections, prefix) {
  for (const sec of rawSections) {
    if (sec === prefix || sec.startsWith(`${prefix}.`)) return true;
  }
  return false;
}

/**
 * Detect active Python manager, run prefix, entrypoints, and task scripts in `workspaceDir`.
 *
 * @param {string} workspaceDir
 */
export function detectWorkspacePython(workspaceDir) {
  const root = path.resolve(workspaceDir);
  const pyprojectPath = path.join(root, "pyproject.toml");
  const hatchTomlPath = path.join(root, "hatch.toml");
  const hasPyproject = fs.existsSync(pyprojectPath);
  const hasHatchToml = fs.existsSync(hatchTomlPath);

  const parsedPy = hasPyproject
    ? parseTomlSections(fs.readFileSync(pyprojectPath, "utf8"))
    : { sections: {}, rawSections: new Set() };
  const parsedHatch = hasHatchToml
    ? parseTomlSections(fs.readFileSync(hatchTomlPath, "utf8"))
    : { sections: {}, rawSections: new Set() };

  const { sections, rawSections } = parsedPy;
  /** @type {Record<string, string>} */
  const entrypointTargets = {};
  for (const secName of ["project.scripts", "project.gui-scripts", "tool.poetry.scripts"]) {
    const table = sections[secName];
    if (!table) continue;
    for (const [scriptName, target] of Object.entries(table)) entrypointTargets[scriptName] = target;
  }

  /** @type {Record<string, { manager: string, env: string, command: string }>} */
  const taskScripts = {};
  if (sections["tool.pdm.scripts"]) {
    for (const [name, cmd] of Object.entries(sections["tool.pdm.scripts"])) {
      taskScripts[name] = { manager: "pdm", env: "default", command: cmd };
    }
  }
  for (const [secName, table] of Object.entries(sections)) {
    const m = secName.match(/^tool\.hatch\.envs\.([^.]+)\.scripts$/);
    if (!m) continue;
    for (const [name, cmd] of Object.entries(table)) {
      const q = m[1] === "default" ? name : `${m[1]}:${name}`;
      taskScripts[q] = { manager: "hatch", env: m[1], command: cmd };
    }
  }
  for (const [secName, table] of Object.entries(parsedHatch.sections)) {
    const m = secName.match(/^envs\.([^.]+)\.scripts$/);
    if (!m) continue;
    for (const [name, cmd] of Object.entries(table)) {
      const q = m[1] === "default" ? name : `${m[1]}:${name}`;
      taskScripts[q] = { manager: "hatch", env: m[1], command: cmd };
    }
  }

  const venvPython = resolveVenvExecutable(path.join(root, ".venv"), "python");
  let manager = "system";
  let runPrefix = [IS_WIN ? "python" : "python3"];
  let reason = "fallback system python";

  if (fs.existsSync(path.join(root, "uv.lock")) || hasSectionPrefix(rawSections, "tool.uv")) {
    manager = "uv";
    runPrefix = ["uv", "run"];
    reason = fs.existsSync(path.join(root, "uv.lock")) ? "uv.lock" : "[tool.uv]";
  } else if (hasHatchToml || hasSectionPrefix(rawSections, "tool.hatch")) {
    manager = "hatch";
    runPrefix = ["hatch", "run"];
    reason = hasHatchToml ? "hatch.toml" : "[tool.hatch]";
  } else if (fs.existsSync(path.join(root, "pdm.lock")) || hasSectionPrefix(rawSections, "tool.pdm")) {
    manager = "pdm";
    runPrefix = ["pdm", "run"];
    reason = fs.existsSync(path.join(root, "pdm.lock")) ? "pdm.lock" : "[tool.pdm]";
  } else if (fs.existsSync(path.join(root, "poetry.lock")) || hasSectionPrefix(rawSections, "tool.poetry")) {
    manager = "poetry";
    runPrefix = ["poetry", "run"];
    reason = fs.existsSync(path.join(root, "poetry.lock")) ? "poetry.lock" : "[tool.poetry]";
  } else if (fs.existsSync(path.join(root, "Pipfile.lock")) || fs.existsSync(path.join(root, "Pipfile"))) {
    manager = "pipenv";
    runPrefix = ["pipenv", "run"];
    reason = "Pipfile";
  } else if (venvPython) {
    manager = "venv";
    runPrefix = [venvPython];
    reason = ".venv";
  }

  return {
    workspaceDir: root,
    projectName: sections.project?.name || sections["tool.poetry"]?.name || path.basename(root),
    manager,
    reason,
    runPrefix,
    venvPython,
    hasPyproject,
    entrypoints: Object.keys(entrypointTargets).sort(),
    entrypointTargets,
    taskScripts,
  };
}

export function buildEntrypointCommand(workspaceDir, entrypointOrScript, extraArgs = []) {
  const info = detectWorkspacePython(workspaceDir);
  if (info.manager === "venv" && info.venvPython) {
    const directBin = resolveVenvExecutable(path.join(info.workspaceDir, ".venv"), entrypointOrScript);
    if (directBin) return { command: directBin, args: [...extraArgs], cwd: info.workspaceDir, manager: info.manager };
    const target = info.entrypointTargets[entrypointOrScript];
    if (target && target.includes(":")) {
      return { command: info.venvPython, args: ["-m", target.split(":", 1)[0], ...extraArgs], cwd: info.workspaceDir, manager: info.manager };
    }
  }
  if (info.manager === "system") {
    const target = info.entrypointTargets[entrypointOrScript];
    if (target && target.includes(":")) {
      return { command: info.runPrefix[0], args: ["-m", target.split(":", 1)[0], ...extraArgs], cwd: info.workspaceDir, manager: info.manager };
    }
  }
  const [command, ...prefixArgs] = info.runPrefix;
  return { command, args: [...prefixArgs, entrypointOrScript, ...extraArgs], cwd: info.workspaceDir, manager: info.manager };
}

function canImportCatalogDeps(command, prefixArgs, cwd) {
  const resolved = path.isAbsolute(command) ? command : whichSync(command);
  if (!resolved) return false;
  const probe = spawnSync(resolved, [...prefixArgs, "-c", "import duckdb, msgspec, sqlspec"], {
    cwd,
    encoding: "utf8",
    timeout: 4000,
  });
  return probe.status === 0;
}

export function resolveCatalogWorkerCommand(pluginRoot, workspaceDir) {
  const resolvedPluginRoot = path.resolve(pluginRoot);
  const resolvedWorkspace = workspaceDir ? path.resolve(workspaceDir) : resolvedPluginRoot;

  if (process.env.FLOW_DISABLE_DUCKDB === "1") {
    return { strategy: "disabled", command: null, args: [], cwd: resolvedWorkspace, env: {} };
  }

  const pluginVenvCatalog = resolveVenvExecutable(path.join(resolvedPluginRoot, ".venv"), "flow-catalog");
  if (pluginVenvCatalog) {
    return { strategy: "plugin-venv", command: pluginVenvCatalog, args: ["serve-stdio"], cwd: resolvedPluginRoot, env: {} };
  }

  const pluginVenvPython = resolveVenvExecutable(path.join(resolvedPluginRoot, ".venv"), "python");
  if (pluginVenvPython && canImportCatalogDeps(pluginVenvPython, [], resolvedPluginRoot)) {
    return { strategy: "plugin-venv", command: pluginVenvPython, args: ["-m", "tools.catalog", "serve-stdio"], cwd: resolvedPluginRoot, env: { PYTHONPATH: resolvedPluginRoot } };
  }

  const uvBin = whichSync("uv");
  if (uvBin && fs.existsSync(path.join(resolvedPluginRoot, "pyproject.toml"))) {
    return { strategy: "uv-project-group", command: uvBin, args: ["run", "--project", resolvedPluginRoot, "--group", "catalog", "flow-catalog", "serve-stdio"], cwd: resolvedPluginRoot, env: {} };
  }

  const wsInfo = detectWorkspacePython(resolvedWorkspace);
  if (wsInfo.manager === "venv" && wsInfo.venvPython && canImportCatalogDeps(wsInfo.venvPython, [], resolvedWorkspace)) {
    return { strategy: "workspace-venv-pythonpath", command: wsInfo.venvPython, args: ["-m", "tools.catalog", "serve-stdio"], cwd: resolvedWorkspace, env: { PYTHONPATH: resolvedPluginRoot } };
  }
  if (["hatch", "pdm", "poetry", "pipenv"].includes(wsInfo.manager)) {
    const [mgrBin, ...mgrPrefix] = wsInfo.runPrefix;
    if (canImportCatalogDeps(mgrBin, [...mgrPrefix, "python"], resolvedWorkspace)) {
      return { strategy: "workspace-manager-pythonpath", command: mgrBin, args: [...mgrPrefix, "python", "-m", "tools.catalog", "serve-stdio"], cwd: resolvedWorkspace, env: { PYTHONPATH: resolvedPluginRoot } };
    }
  }

  return { strategy: "node-bm25-fallback", command: null, args: [], cwd: resolvedWorkspace, env: {} };
}
