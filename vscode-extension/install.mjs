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
    }
  }
  return { target, customExtensionsDir, link };
}

/**
 * Resolve target editor extension directories to install into.
 *
 * @param {{ target?: string, customExtensionsDir?: string, homeDir?: string }} [options]
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
  if (detected.length === 0) {
    detected.push({ editor: "vscode", extensionsDir: candidates.vscode });
  }
  return detected;
}

/**
 * Install Flow Studio into the resolved editor extension directories.
 *
 * @param {{ target?: string, customExtensionsDir?: string, link?: boolean, homeDir?: string }} [options]
 */
export function installFlowStudioExtension(options = {}) {
  const pkgPath = path.join(EXT_SRC_DIR, "package.json");
  const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));
  const publisher = String(pkg.publisher || "cofin");
  const name = String(pkg.name || "flow-studio");
  const version = String(pkg.version || "0.28.0");
  const bundleFolderName = `${publisher}.${name}-${version}`;

  const targets = resolveTargetExtensionDirs(options);
  const installed = [];

  for (const { editor, extensionsDir } of targets) {
    fs.mkdirSync(extensionsDir, { recursive: true });
    for (const entry of fs.readdirSync(extensionsDir)) {
      if (entry.startsWith(`${publisher}.${name}-`) && entry !== bundleFolderName) {
        fs.rmSync(path.join(extensionsDir, entry), { recursive: true, force: true });
      }
    }

    const destDir = path.join(extensionsDir, bundleFolderName);
    fs.rmSync(destDir, { recursive: true, force: true });

    if (options.link) {
      fs.symlinkSync(EXT_SRC_DIR, destDir, "dir");
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

    installed.push({ editor, mode: "bundle", path: destDir });
  }

  return {
    extensionId: `${publisher}.${name}`,
    version,
    installed,
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const opts = parseArgs(process.argv.slice(2));
  const result = installFlowStudioExtension(opts);
  for (const item of result.installed) {
    process.stdout.write(
      `[flow-studio] Installed ${result.extensionId}@${result.version} (${item.mode}) for ${item.editor}: ${item.path}\n`
    );
  }
}
