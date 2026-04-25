/**
 * Flow Framework plugin for OpenCode.ai
 *
 * Injects Flow context into the system prompt via experimental.chat.system.transform
 * (the supported injection point as of @opencode-ai/plugin@1.3.6 — there is no
 * SessionStart hook). Also exposes FLOW_PLUGIN_ROOT to spawned shells.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(__dirname, '../..');

let cachedContext = null;

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
    'Prefer official Beads (`bd`) when persistence is needed, keep `br` as compatibility mode, and allow no-Beads degraded mode when the user wants less admin.',
    '',
    'AUTO-TRIGGER RULES:',
    '- When .agents/ directory exists: ALWAYS invoke the flow skill at session start',
    '- When user says "implement", "plan", "spec", "prd", "sync", "status": immediately invoke the matching Flow workflow rather than staying in generic chat mode',
    '- When editing files in .agents/specs/: invoke flow skill for context',
    '- When user mentions "beads", "bd", "br", or backend migration: invoke flow skill',
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

export default async () => {
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
