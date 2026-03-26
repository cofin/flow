/**
 * Flow Framework plugin for OpenCode.ai
 *
 * Injects Flow's context via system prompt transform.
 * Auto-registers skills and commands directories via config hook.
 */

import path from 'path';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export const FlowPlugin = async ({ client, directory }) => {
  const homeDir = os.homedir();
  const flowSkillsDir = path.resolve(__dirname, '../../skills');
  const flowCommandsDir = path.resolve(__dirname, '../../templates/opencode/commands');
  const envConfigDir = process.env.OPENCODE_CONFIG_DIR ? path.resolve(process.env.OPENCODE_CONFIG_DIR) : path.join(homeDir, '.config/opencode');

  // Helper to load Flow's global context
  const getFlowContext = () => {
    const contextPath = path.resolve(__dirname, '../../AGENTS.md');
    if (!fs.existsSync(contextPath)) return null;
    const content = fs.readFileSync(contextPath, 'utf8');
    return `<context_context>
You are operating within the **Flow Framework** for Context-Driven Development.
Follow the core mandates and operational guidelines provided below:

${content}
</context_context>`;
  };

  return {
    // Inject skills and commands paths into live config
    config: async (config) => {
      // Register Flow's skills
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(flowSkillsDir)) {
        config.skills.paths.push(flowSkillsDir);
      }

      // Register Flow's commands (if OpenCode supports it via config)
      config.commands = config.commands || {};
      config.commands.paths = config.commands.paths || [];
      if (!config.commands.paths.includes(flowCommandsDir)) {
        config.commands.paths.push(flowCommandsDir);
      }
    },

    // Inject Flow's context into the system prompt
    'experimental.chat.system.transform': async (_input, output) => {
      const flowContext = getFlowContext();
      if (flowContext) {
        (output.system ||= []).push(flowContext);
      }
    }
  };
};
