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

function getFlowContext() {
  const contextPath = path.join(PLUGIN_ROOT, 'AGENTS.md');
  if (!fs.existsSync(contextPath)) return null;
  return fs.readFileSync(contextPath, 'utf8');
}

function buildSessionContext() {
  if (cachedContext !== null) return cachedContext;

  const agentsContent = getFlowContext();
  if (!agentsContent) {
    cachedContext = '';
    return cachedContext;
  }

  cachedContext = [
    'You are operating within the **Flow Framework** for Context-Driven Development.',
    '',
    'Flow is installed and MUST be used for all development work in projects with a .agents/ directory.',
    'Use official Beads (`bd`) when persistence is needed; allow no-Beads degraded mode when the user wants less admin.',
    '',
    'AUTO-TRIGGER RULES:',
    '- When .agents/ directory exists: ALWAYS invoke the flow skill at session start',
    '- When user says "implement", "plan", "spec", "prd", "sync", "status": immediately invoke the matching Flow workflow rather than staying in generic chat mode',
    '- When editing files in .agents/specs/: invoke flow skill for context',
    '- When user mentions "beads", "bd", or backend migration: invoke flow skill',
    '- When a spec or PRD exists but task detail is coarse: invoke flow-refine before implementation or subagent dispatch',
    '- Do not finish PRD or planning work while obvious research gaps remain',
    '',
    'Key commands: /flow:setup, /flow:prd, /flow:plan, /flow:implement, /flow:sync, /flow:status, /flow:refresh',
    '',
    'All spec/design docs go in .agents/specs/ (not docs/superpowers/specs/).',
    'Before dispatching subagents, preserve context with the relevant spec/PRD, patterns, knowledge chapters, learnings, affected files, and verification requirements.',
    '',
    agentsContent,
  ].join('\n');

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
