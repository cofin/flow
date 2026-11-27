"use strict";

/**
 * CommonJS entrypoint shim for Flow Studio VS Code / Cursor / Windsurf extension.
 * Dynamically imports the ESM implementation (`./extension.mjs`) so the extension
 * activates reliably across all VS Code Extension Host versions.
 */

let loadedModule = null;

async function activate(context) {
  loadedModule = await import("./extension.mjs");
  return loadedModule.activate(context);
}

async function deactivate() {
  if (loadedModule && typeof loadedModule.deactivate === "function") {
    return loadedModule.deactivate();
  }
  return undefined;
}

module.exports = { activate, deactivate };
