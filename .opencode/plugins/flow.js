/** Static Flow routing for OpenCode. Project state remains in tracked Markdown. */

const ROUTING = 'Flow continuity is direct Markdown. Resolve the configured root from .agents/setup-state.json (default .agents/), read its index.md, then follow skills/flow/references/state.md. After compaction or session loss, use the journal-first direct-read continuity contract there; never treat hook context as authority.';

function isFlowDisabledByManagedConfig(ctx) {
  const managed = ctx?.config?.managedConfig ?? ctx?.config?.managed ?? null;
  if (!managed) return false;
  if (managed.disabledPlugins?.includes('flow')) return true;
  return Boolean(managed.allowedPlugins && !managed.allowedPlugins.includes('flow'));
}

export default async (ctx) => {
  if (isFlowDisabledByManagedConfig(ctx)) return {};

  return {
    'experimental.chat.system.transform': async (_input, output) => {
      output.system.push(ROUTING);
    },
  };
};
