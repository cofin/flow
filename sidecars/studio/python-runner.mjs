/**
 * Python environment manager and entrypoint detector for Flow Studio.
 *
 * Detects uv, hatch, pdm, poetry, pipenv, and local .venv environments in both
 * target user repositories and the local Flow plugin checkout without assuming
 * Flow is published on PyPI.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const IS_WIN = process.platform === "win32";

/**
 * Locate an executable on PATH without spawning a shell.
 *
 * @param {string} binaryName
 * @returns {string | null}
 */
export function whichSync(binaryName) {
  const pathEnv = process.env.PATH || "";
  const pathSep = IS_WIN ? ";" : ":";
  const exts = IS_WIN
    ? (process.env.PATHEXT || ".EXE;.CMD;.BAT").split(";").map((e) => e.toLowerCase())
    : [""];

  for (const rawDir of pathEnv.split(pathSep)) {
    const dir = rawDir.trim();
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(dir, ext && !binaryName.toLowerCase().endsWith(ext) ? `${binaryName}${ext}` : binaryName);
      try {
        const stat = fs.statSync(candidate);
        if (stat.isFile()) return candidate;
      } catch {
        // Ignore missing candidate paths.
      }
    }
  }
  return null;
}

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
    if (fs.existsSync(full)) {
      return full;
    }
  }
  return null;
}

/**
 * Parse TOML section headers and key-value assignments relevant to Python
 * package managers and console script entrypoints.
 *
 * @param {string} tomlText
 * @returns {{ sections: Record<string, Record<string, string>>, rawSections: Set<string> }}
 */
export function parseTomlSections(tomlText) {
  /** @type {Record<string, Record<string, string>>} */
  const sections = {};
  /** @type {Set<string>} */
  const rawSections = new Set();
  let currentSection = "";

  const lines = tomlText.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const raw = lines[i];
    const trimmed = raw.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const headerMatch = trimmed.match(/^\[([^\[\]]+)\]$/);
    if (headerMatch) {
      currentSection = headerMatch[1].trim();
      rawSections.add(currentSection);
      if (!sections[currentSection]) {
        sections[currentSection] = {};
      }
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
    if (commentIdx >= 0) {
      value = value.slice(0, commentIdx).trim();
    }
    value = value.replace(/^["']|["']$/g, "");
    if (key) {
      sections[currentSection][key] = value;
    }
  }

  return { sections, rawSections };
}

/**
 * Find an unquoted TOML comment delimiter.
 *
 * @param {string} text
 * @returns {number}
 */
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

/**
 * Check whether any parsed TOML section equals or starts with prefix.
 *
 * @param {Set<string>} rawSections
 * @param {string} prefix
 * @returns {boolean}
 */
function hasSectionPrefix(rawSections, prefix) {
  for (const sec of rawSections) {
    if (sec === prefix || sec.startsWith(`${prefix}.`)) return true;
  }
  return false;
}

/**
 * Detect the Python environment manager, run prefix, console script entrypoints,
 * and tool scripts configured in a target workspace directory.
 *
 * @param {string} workspaceDir
 */
export function detectWorkspacePython(workspaceDir) {
  const root = path.resolve(workspaceDir);
  const pyprojectPath = path.join(root, "pyproject.toml");
  const hatchTomlPath = path.join(root, "hatch.toml");
  const hasPyproject = fs.existsSync(pyprojectPath);
  const hasHatchToml = fs.existsSync(hatchTomlPath);

  const parsedPyproject = hasPyproject
    ? parseTomlSections(fs.readFileSync(pyprojectPath, "utf8"))
    : { sections: {}, rawSections: new Set() };
  const parsedHatch = hasHatchToml
    ? parseTomlSections(fs.readFileSync(hatchTomlPath, "utf8"))
    : { sections: {}, rawSections: new Set() };

  const { sections, rawSections } = parsedPyproject;

  /** @type {Record<string, string>} */
  const entrypointTargets = {};
  for (const secName of ["project.scripts", "project.gui-scripts", "tool.poetry.scripts"]) {
    const table = sections[secName];
    if (!table) continue;
    for (const [scriptName, target] of Object.entries(table)) {
      entrypointTargets[scriptName] = target;
    }
  }

  /** @type {Record<string, { manager: string, env: string, command: string }>} */
  const taskScripts = {};
  if (sections["tool.pdm.scripts"]) {
    for (const [name, cmd] of Object.entries(sections["tool.pdm.scripts"])) {
      taskScripts[name] = { manager: "pdm", env: "default", command: cmd };
    }
  }
  for (const [secName, table] of Object.entries(sections)) {
    const hatchMatch = secName.match(/^tool\.hatch\.envs\.([^.]+)\.scripts$/);
    if (hatchMatch) {
      const envName = hatchMatch[1];
      for (const [name, cmd] of Object.entries(table)) {
        const qualified = envName === "default" ? name : `${envName}:${name}`;
        taskScripts[qualified] = { manager: "hatch", env: envName, command: cmd };
      }
    }
  }
  for (const [secName, table] of Object.entries(parsedHatch.sections)) {
    const hatchMatch = secName.match(/^envs\.([^.]+)\.scripts$/);
    if (hatchMatch) {
      const envName = hatchMatch[1];
      for (const [name, cmd] of Object.entries(table)) {
        const qualified = envName === "default" ? name : `${envName}:${name}`;
        taskScripts[qualified] = { manager: "hatch", env: envName, command: cmd };
      }
    }
  }

  const venvDir = path.join(root, ".venv");
  const venvPython = resolveVenvExecutable(venvDir, "python");

  let manager = "system";
  /** @type {string[]} */
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

  const projectName =
    sections.project?.name ||
    sections["tool.poetry"]?.name ||
    path.basename(root);

  return {
    workspaceDir: root,
    projectName,
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

/**
 * Build an argv command array to invoke a detected project entrypoint or task script
 * using the workspace's active environment manager.
 *
 * @param {string} workspaceDir
 * @param {string} entrypointOrScript
 * @param {string[]} [extraArgs]
 */
export function buildEntrypointCommand(workspaceDir, entrypointOrScript, extraArgs = []) {
  const info = detectWorkspacePython(workspaceDir);
  if (info.manager === "venv" && info.venvPython) {
    const directBin = resolveVenvExecutable(path.join(info.workspaceDir, ".venv"), entrypointOrScript);
    if (directBin) {
      return { command: directBin, args: [...extraArgs], cwd: info.workspaceDir, manager: info.manager };
    }
    const target = info.entrypointTargets[entrypointOrScript];
    if (target && target.includes(":")) {
      const [modName] = target.split(":", 1);
      return {
        command: info.venvPython,
        args: ["-m", modName, ...extraArgs],
        cwd: info.workspaceDir,
        manager: info.manager,
      };
    }
  }
  if (info.manager === "system") {
    const target = info.entrypointTargets[entrypointOrScript];
    if (target && target.includes(":")) {
      const [modName] = target.split(":", 1);
      return {
        command: info.runPrefix[0],
        args: ["-m", modName, ...extraArgs],
        cwd: info.workspaceDir,
        manager: info.manager,
      };
    }
  }
  const [command, ...prefixArgs] = info.runPrefix;
  return {
    command,
    args: [...prefixArgs, entrypointOrScript, ...extraArgs],
    cwd: info.workspaceDir,
    manager: info.manager,
  };
}

/**
 * Probe whether a Python command can import sqlspec and duckdb.
 *
 * @param {string} command
 * @param {string[]} prefixArgs
 * @param {string} cwd
 * @returns {boolean}
 */
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

/**
 * Resolve the command used to launch Flow's local DuckDB catalog stdio worker
 * without ever assuming Flow is published on PyPI.
 *
 * @param {string} pluginRoot
 * @param {string} [workspaceDir]
 */
export function resolveCatalogWorkerCommand(pluginRoot, workspaceDir) {
  const resolvedPluginRoot = path.resolve(pluginRoot);
  const resolvedWorkspace = workspaceDir ? path.resolve(workspaceDir) : resolvedPluginRoot;

  if (process.env.FLOW_DISABLE_DUCKDB === "1") {
    return {
      strategy: "disabled",
      command: null,
      args: [],
      cwd: resolvedWorkspace,
      env: {},
    };
  }

  const pluginVenvCatalog = resolveVenvExecutable(path.join(resolvedPluginRoot, ".venv"), "flow-catalog");
  if (pluginVenvCatalog) {
    return {
      strategy: "plugin-venv",
      command: pluginVenvCatalog,
      args: ["serve-stdio"],
      cwd: resolvedPluginRoot,
      env: {},
    };
  }

  const pluginVenvPython = resolveVenvExecutable(path.join(resolvedPluginRoot, ".venv"), "python");
  if (pluginVenvPython && canImportCatalogDeps(pluginVenvPython, [], resolvedPluginRoot)) {
    return {
      strategy: "plugin-venv",
      command: pluginVenvPython,
      args: ["-m", "tools.catalog", "serve-stdio"],
      cwd: resolvedPluginRoot,
      env: { PYTHONPATH: resolvedPluginRoot },
    };
  }

  const uvBin = whichSync("uv");
  if (uvBin && fs.existsSync(path.join(resolvedPluginRoot, "pyproject.toml"))) {
    return {
      strategy: "uv-project-group",
      command: uvBin,
      args: ["run", "--project", resolvedPluginRoot, "--group", "catalog", "flow-catalog", "serve-stdio"],
      cwd: resolvedPluginRoot,
      env: {},
    };
  }

  const wsInfo = detectWorkspacePython(resolvedWorkspace);
  if (wsInfo.manager === "venv" && wsInfo.venvPython) {
    if (canImportCatalogDeps(wsInfo.venvPython, [], resolvedWorkspace)) {
      return {
        strategy: "workspace-venv-pythonpath",
        command: wsInfo.venvPython,
        args: ["-m", "tools.catalog", "serve-stdio"],
        cwd: resolvedWorkspace,
        env: { PYTHONPATH: resolvedPluginRoot },
      };
    }
  } else if (["hatch", "pdm", "poetry", "pipenv"].includes(wsInfo.manager)) {
    const [mgrBin, ...mgrPrefix] = wsInfo.runPrefix;
    if (canImportCatalogDeps(mgrBin, [...mgrPrefix, "python"], resolvedWorkspace)) {
      return {
        strategy: "workspace-manager-pythonpath",
        command: mgrBin,
        args: [...mgrPrefix, "python", "-m", "tools.catalog", "serve-stdio"],
        cwd: resolvedWorkspace,
        env: { PYTHONPATH: resolvedPluginRoot },
      };
    }
  }

  return {
    strategy: "node-bm25-fallback",
    command: null,
    args: [],
    cwd: resolvedWorkspace,
    env: {},
  };
}
