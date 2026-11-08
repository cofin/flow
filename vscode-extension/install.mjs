#!/usr/bin/env node
/**
 * Zero-dependency installer for the Flow Studio VS Code / Cursor / Windsurf / Positron extension.
 *
 * Packages `vscode-extension/` together with the shared `sidecars/studio/` runtime and
 * installs a self-contained extension bundle (`cofin.flow-studio-<version>`) directly into
 * the target editor's extensions directory (or links the checkout when `--link` is passed).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const EXT_SRC_DIR = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(EXT_SRC_DIR, "..");
const STUDIO_SRC_DIR = path.join(REPO_ROOT, "sidecars", "studio");

const EDITOR_EXTENSION_DIRS = Object.freeze({
  vscode: path.join(os.homedir(), ".vscode", "extensions"),
  "vscode-insiders": path.join(os.homedir(), ".vscode-insiders", "extensions"),
  cursor: path.join(os.homedir(), ".cursor", "extensions"),
  windsurf: path.join(os.homedir(), ".windsurf", "extensions"),
  positron: path.join(os.homedir(), ".positron", "extensions"),
});

/**
 * Parse CLI flags for the Flow Studio extension installer.
 *
 * @param {string[]} argv
 */
export function parseArgs(argv) {
  let target = "auto";
  let customExtensionsDir = "";
  let link = false;
  let ifNeeded = false;
  let quiet = false;
  let help = false;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--target" && argv[i + 1]) {
      target = argv[i + 1].toLowerCase();
      i += 1;
    } else if (arg.startsWith("--target=")) {
      target = arg.slice("--target=".length).toLowerCase();
    } else if (arg === "--extensions-dir" && argv[i + 1]) {
      customExtensionsDir = path.resolve(argv[i + 1]);
      i += 1;
    } else if (arg.startsWith("--extensions-dir=")) {
      customExtensionsDir = path.resolve(arg.slice("--extensions-dir=".length));
    } else if (arg === "--link" || arg === "-l") {
      link = true;
    } else if (arg === "--if-needed") {
      ifNeeded = true;
    } else if (arg === "--quiet" || arg === "-q") {
      quiet = true;
    } else if (arg === "--help" || arg === "-h") {
      help = true;
    }
  }
  return { target, customExtensionsDir, link, ifNeeded, quiet, help };
}

export const USAGE = `Usage: flow-studio-vscode [options]

Install the Flow Studio extension (cofin.flow-studio) into VS Code-compatible editors.

Options:
  --target <name>          auto (default), all, vscode, vscode-insiders, cursor, windsurf, positron
  --extensions-dir <path>  Install into an explicit extensions directory
  --link, -l               Symlink this checkout instead of copying a bundle
  --if-needed              Skip editors that already have the current version
  --quiet, -q              Suppress output
  --help, -h               Show this help
`;

/**
 * Report whether this module is the process entry point.
 *
 * npm and npx launch bins through a `node_modules/.bin/<name>` symlink. Node resolves that
 * symlink for `import.meta.url` but keeps it in `process.argv[1]`, so both sides are
 * compared by real path.
 *
 * @param {string | undefined} [argv1]
 * @returns {boolean}
 */
export function isDirectInvocation(argv1 = process.argv[1]) {
  if (!argv1) return false;
  try {
    return fs.realpathSync(argv1) === fs.realpathSync(fileURLToPath(import.meta.url));
  } catch {
    return false;
  }
}

/**
 * Resolve target editor extension directories to install into.
 *
 * @param {{ target?: string, customExtensionsDir?: string, homeDir?: string, ifNeeded?: boolean }} [options]
 * @returns {{ editor: string, extensionsDir: string }[]}
 */
export function resolveTargetExtensionDirs(options = {}) {
  if (options.customExtensionsDir) {
    return [{ editor: "custom", extensionsDir: path.resolve(options.customExtensionsDir) }];
  }
  const home = options.homeDir ? path.resolve(options.homeDir) : os.homedir();
  const candidates = {
    vscode: path.join(home, ".vscode", "extensions"),
    "vscode-insiders": path.join(home, ".vscode-insiders", "extensions"),
    cursor: path.join(home, ".cursor", "extensions"),
    windsurf: path.join(home, ".windsurf", "extensions"),
    positron: path.join(home, ".positron", "extensions"),
  };

  const target = (options.target || "auto").toLowerCase();
  if (target !== "auto" && target !== "all") {
    const selected = candidates[target];
    if (!selected) {
      throw new Error(
        `Unknown --target '${target}'. Expected one of: auto, all, ${Object.keys(candidates).join(", ")}`
      );
    }
    return [{ editor: target, extensionsDir: selected }];
  }

  const detected = [];
  for (const [editor, extDir] of Object.entries(candidates)) {
    const parentDir = path.dirname(extDir);
    if (target === "all" || fs.existsSync(parentDir) || fs.existsSync(extDir)) {
      detected.push({ editor, extensionsDir: extDir });
    }
  }
  if (detected.length === 0 && !options.ifNeeded) {
    detected.push({ editor: "vscode", extensionsDir: candidates.vscode });
  }
  return detected;
}

/**
 * Register or update the extension entry in `<extensionsDir>/extensions.json` and remove stale `.obsolete` entries.
 *
 * @param {string} extensionsDir
 * @param {string} extensionId
 * @param {string} version
 * @param {string} bundleFolderName
 * @param {string} destDir
 */
function registerInExtensionsJson(extensionsDir, extensionId, version, bundleFolderName, destDir) {
  const manifestPath = path.join(extensionsDir, "extensions.json");
  let entries = [];
  if (fs.existsSync(manifestPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
      if (Array.isArray(parsed)) entries = parsed;
    } catch {
      entries = [];
    }
  }
  const normalizedFsPath = destDir.replace(/\\/g, "/");
  const urlPath = normalizedFsPath.startsWith("/") ? normalizedFsPath : `/${normalizedFsPath}`;
  const entry = {
    identifier: { id: extensionId.toLowerCase() },
    version,
    location: {
      $mid: 1,
      fsPath: destDir,
      path: urlPath,
      external: `file://${urlPath}`,
      scheme: "file",
    },
    relativeLocation: bundleFolderName,
    metadata: {
      installedTimestamp: Date.now(),
      pinned: false,
      source: "vsix",
    },
  };
  const filtered = entries.filter(
    (item) => String(item?.identifier?.id || "").toLowerCase() !== extensionId.toLowerCase()
  );
  filtered.push(entry);
  fs.writeFileSync(manifestPath, JSON.stringify(filtered), "utf8");

  const obsoletePath = path.join(extensionsDir, ".obsolete");
  if (fs.existsSync(obsoletePath)) {
    try {
      const obsolete = JSON.parse(fs.readFileSync(obsoletePath, "utf8"));
      if (obsolete && typeof obsolete === "object") {
        let changed = false;
        for (const key of Object.keys(obsolete)) {
          if (key.toLowerCase().startsWith(`${extensionId.toLowerCase()}-`)) {
            delete obsolete[key];
            changed = true;
          }
        }
        if (changed) {
          fs.writeFileSync(obsoletePath, JSON.stringify(obsolete), "utf8");
        }
      }
    } catch {
      // Ignore malformed .obsolete file
    }
  }
}

/**
 * Return true if `destDir` is already installed and registered in `extensions.json`.
 *
 * @param {string} extensionsDir
 * @param {string} extensionId
 * @param {string} version
 * @param {string} destDir
 */
function isExtensionUpToDate(extensionsDir, extensionId, version, destDir) {
  if (!fs.existsSync(path.join(destDir, "package.json"))) return false;
  if (!fs.existsSync(path.join(destDir, "extension.mjs"))) return false;
  const manifestPath = path.join(extensionsDir, "extensions.json");
  if (!fs.existsSync(manifestPath)) return false;
  try {
    const parsed = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    if (!Array.isArray(parsed)) return false;
    return parsed.some(
      (item) =>
        String(item?.identifier?.id || "").toLowerCase() === extensionId.toLowerCase() &&
        String(item?.version || "") === version
    );
  } catch {
    return false;
  }
}

/**
 * Install Flow Studio into the resolved editor extension directories.
 *
 * @param {{ target?: string, customExtensionsDir?: string, link?: boolean, homeDir?: string, ifNeeded?: boolean, quiet?: boolean }} [options]
 */
export function installFlowStudioExtension(options = {}) {
  const pkgPath = path.join(EXT_SRC_DIR, "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const publisher = String(pkg.publisher || "cofin");
  const name = String(pkg.name || "flow-studio");
  const version = String(pkg.version || "0.28.0");
  const extensionId = `${publisher}.${name}`;
  const bundleFolderName = `${extensionId}-${version}`;

  const targets = resolveTargetExtensionDirs(options);
  const installed = [];

  for (const { editor, extensionsDir } of targets) {
    fs.mkdirSync(extensionsDir, { recursive: true });
    const destDir = path.join(extensionsDir, bundleFolderName);

    if (options.ifNeeded && !options.link && isExtensionUpToDate(extensionsDir, extensionId, version, destDir)) {
      installed.push({ editor, mode: "up-to-date", path: destDir });
      continue;
    }

    for (const entry of fs.readdirSync(extensionsDir)) {
      if (entry.startsWith(`${extensionId}-`) && entry !== bundleFolderName) {
        fs.rmSync(path.join(extensionsDir, entry), { recursive: true, force: true });
      }
    }

    fs.rmSync(destDir, { recursive: true, force: true });

    if (options.link) {
      fs.symlinkSync(EXT_SRC_DIR, destDir, "dir");
      registerInExtensionsJson(extensionsDir, extensionId, version, bundleFolderName, destDir);
      installed.push({ editor, mode: "symlink", path: destDir });
      continue;
    }

    fs.mkdirSync(destDir, { recursive: true });
    for (const fileName of ["package.json", "logo.svg", "icon.png", "README.md"]) {
      const srcFile = path.join(EXT_SRC_DIR, fileName);
      if (fs.existsSync(srcFile)) {
        fs.copyFileSync(srcFile, path.join(destDir, fileName));
      }
    }

    const rawExtJs = fs.readFileSync(path.join(EXT_SRC_DIR, "extension.mjs"), "utf8");
    const bundledExtJs = rawExtJs.replaceAll("../sidecars/studio/", "./sidecars/studio/");
    fs.writeFileSync(path.join(destDir, "extension.mjs"), bundledExtJs, "utf8");

    const destStudioDir = path.join(destDir, "sidecars", "studio");
    fs.mkdirSync(destStudioDir, { recursive: true });
    for (const entry of fs.readdirSync(STUDIO_SRC_DIR, { withFileTypes: true })) {
      if (entry.isFile()) {
        fs.copyFileSync(path.join(STUDIO_SRC_DIR, entry.name), path.join(destStudioDir, entry.name));
      }
    }

    registerInExtensionsJson(extensionsDir, extensionId, version, bundleFolderName, destDir);
    installed.push({ editor, mode: "bundle", path: destDir });
  }

  return {
    extensionId,
    version,
    installed,
  };
}

if (isDirectInvocation()) {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    process.stdout.write(USAGE);
    process.exit(0);
  }
  const result = installFlowStudioExtension(opts);
  if (!opts.quiet) {
    for (const item of result.installed) {
      process.stdout.write(
        `[flow-studio] Installed ${result.extensionId}@${result.version} (${item.mode}) for ${item.editor}: ${item.path}\n`
      );
    }
    if (result.installed.length === 0) {
      process.stdout.write("[flow-studio] No VS Code-compatible editor detected; pass --target or --extensions-dir.\n");
    }
  }
}
