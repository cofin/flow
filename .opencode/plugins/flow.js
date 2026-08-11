/**
 * Flow Framework plugin for OpenCode.ai
 *
 * Injects Flow context into the system prompt via experimental.chat.system.transform
 * (the supported injection point as of @opencode-ai/plugin@1.3.6 — there is no
 * SessionStart hook). Also exposes FLOW_PLUGIN_ROOT to spawned shells.
 *
 * Honors MDM-managed config (ai.opencode.managed PayloadType): when an admin
 * has marked Flow disabled or restricted via the managed-config layer, this
 * plugin no-ops its system-prompt injection. Managed config has the highest
 * precedence and cannot be overridden by user/project config.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { execFileSync } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(__dirname, '../..');

let cachedContext = null;

function isFlowDisabledByManagedConfig(ctx) {
  // Managed config is merged into context.config and has read-only highest precedence.
  // Plugins that respect MDM should early-return when an admin has restricted them.
  const managed = ctx?.config?.managedConfig ?? ctx?.config?.managed ?? null;
  if (!managed) return false;
  if (managed.disabledPlugins && managed.disabledPlugins.includes('flow')) return true;
  if (managed.allowedPlugins && !managed.allowedPlugins.includes('flow')) return true;
  return false;
}

function buildSessionContext() {
  if (cachedContext !== null) return cachedContext;

  try {
    const primingScript = path.join(PLUGIN_ROOT, 'tools', 'priming.py');
    const result = execFileSync('python3', [primingScript], { encoding: 'utf8' });
    const payload = JSON.parse(result);
    cachedContext = payload.hookSpecificOutput?.additionalContext || '';
  } catch (e) {
    console.warn('Flow Priming failed:', e.message);
    cachedContext = '';
  }

  return cachedContext;
}

export default async (ctx) => {
  if (isFlowDisabledByManagedConfig(ctx)) {
    return {};
  }
  return {
    'experimental.chat.system.transform': async (_input, output) => {
      const context = buildSessionContext();
      if (context) output.system.push(context);
    },

    'shell.env': async () => ({
      env: { FLOW_PLUGIN_ROOT: PLUGIN_ROOT },
    }),
  };
};
