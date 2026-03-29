/**
 * Flow Framework plugin for OpenCode.ai
 *
 * Uses OpenCode's plugin API to inject Flow context at session start
 * and register skills/commands directories.
 */

import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGIN_ROOT = path.resolve(__dirname, '../..');

/**
 * Load Flow's AGENTS.md context for injection.
 */
function getFlowContext() {
  const contextPath = path.join(PLUGIN_ROOT, 'AGENTS.md');
  if (!fs.existsSync(contextPath)) return null;
  return fs.readFileSync(contextPath, 'utf8');
}

/**
 * Build the session context string with auto-trigger rules.
 */
function buildSessionContext() {
  const agentsContent = getFlowContext();
  if (!agentsContent) return null;

  return [
    'You are operating within the **Flow Framework** for Context-Driven Development.',
    '',
    'Flow is installed and MUST be used for all development work in projects with a .agents/ directory.',
    '',
    'AUTO-TRIGGER RULES:',
    '- When .agents/ directory exists: ALWAYS invoke the flow skill at session start',
    '- When user says "implement", "plan", "spec", "prd", "sync", "status": invoke the matching flow command',
    '- When editing files in .agents/specs/: invoke flow skill for context',
    '- When user mentions "beads", "br ready", "br status": invoke flow skill',
    '',
    'Key commands: /flow:setup, /flow:prd, /flow:plan, /flow:implement, /flow:sync, /flow:status, /flow:refresh',
    '',
    'All spec/design docs go in .agents/specs/ (not docs/superpowers/specs/).',
    '',
    agentsContent,
  ].join('\n');
}

export default async ({ client, directory }) => {
  return {
    'session.created': async (session) => {
      const context = buildSessionContext();
      if (context) {
        (session.system ||= []).push(context);
      }
    },

    'shell.env': async () => {
      return {
        FLOW_PLUGIN_ROOT: PLUGIN_ROOT,
      };
    },
  };
};
