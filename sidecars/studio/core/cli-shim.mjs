/**
 * @fileoverview Installer and inspector for the global `flow` CLI shim (`~/.local/bin/flow`).
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";

/**
 * Installs and checks `~/.local/bin/flow` (or `flow.cmd` on Windows) pointing at `bin/flow.mjs`.
 */
export class CliShimInstaller {
  /**
   * @param {{ pluginRoot: string, env?: NodeJS.ProcessEnv }} options
   */
  constructor({ pluginRoot, env = process.env }) {
    this.pluginRoot = path.resolve(pluginRoot);
    this.env = env;
  }

  get binDir() {
    if (this.env.FLOW_CLI_BIN_DIR && String(this.env.FLOW_CLI_BIN_DIR).trim()) {
      return path.resolve(String(this.env.FLOW_CLI_BIN_DIR).trim());
    }
    const home = path.resolve(this.env.HOME || this.env.USERPROFILE || os.homedir());
    return path.join(home, ".local", "bin");
  }

  get shimPath() {
    return path.join(this.binDir, process.platform === "win32" ? "flow.cmd" : "flow");
  }

  get targetScript() {
    return path.join(this.pluginRoot, "bin", "flow.mjs");
  }

  /**
   * Report whether the `flow` shim is installed and whether `binDir` is on `PATH`.
   */
  status() {
    const shim = this.shimPath;
    const target = this.targetScript;
    let installed = false;
    try {
      const st = fs.lstatSync(shim);
      if (st.isSymbolicLink()) {
        const linked = path.resolve(path.dirname(shim), fs.readlinkSync(shim));
        installed = linked === target;
      } else if (st.isFile()) {
        installed = true;
      }
    } catch {
      installed = false;
    }

    const pathSep = process.platform === "win32" ? ";" : ":";
    const pathDirs = String(this.env.PATH || "")
      .split(pathSep)
      .filter(Boolean)
      .map((dir) => path.resolve(dir));
    return {
      installed,
      shim_path: shim,
      target_path: target,
      bin_dir: this.binDir,
      on_path: pathDirs.includes(this.binDir),
    };
  }

  /**
   * Create or update `~/.local/bin/flow` linking to `bin/flow.mjs`.
   */
  install() {
    const target = this.targetScript;
    if (!fs.existsSync(target)) {
      throw new Error(`CLI script not found at ${target}`);
    }
    try {
      fs.chmodSync(target, 0o755);
    } catch {
      // Read-only mounts (EROFS / EPERM) may prevent chmod on the plugin script.
    }
    fs.mkdirSync(this.binDir, { recursive: true });
    const shim = this.shimPath;

    if (process.platform === "win32") {
      const cmdBody = `@echo off\r\n"${process.execPath}" "${target}" %*\r\n`;
      fs.writeFileSync(shim, cmdBody, "utf8");
      return { ...this.status(), installed: true, mode: "cmd" };
    }

    try {
      const existing = fs.lstatSync(shim);
      if (existing.isSymbolicLink() || existing.isFile()) {
        fs.unlinkSync(shim);
      }
    } catch {
      // Absent shim is expected on first install.
    }
    fs.symlinkSync(target, shim);
    return { ...this.status(), installed: true, mode: "symlink" };
  }
}
