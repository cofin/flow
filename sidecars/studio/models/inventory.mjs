/**
 * Zero-regex live multi-harness model discovery and capability vector normalization.
 *
 * Probes native harness inventories (`agy`, `claude`, `codex`, `cursor`, `opencode`,
 * `vscode`, `/v1/models`) and joins structured metadata from a cached SWR
 * `https://models.dev/api.json` snapshot without guessing capabilities from model name substrings.
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { readJsonSafe, readTextSafe, StudioStateStore, whichSync } from "../core/fs-io.mjs";

const MODELS_DEV_URL = "https://models.dev/api.json";
const MODELS_DEV_TTL_MS = 24 * 60 * 60 * 1000;
const MODELS_DEV_GRACE_MS = 7 * 24 * 60 * 60 * 1000;

export const EFFORT_RANK = Object.freeze({
  default: 0.55,
  minimal: 0.2,
  low: 0.35,
  medium: 0.62,
  high: 0.86,
  xhigh: 0.96,
  max: 1.0,
});

/**
 * Load optional user calibration (`~/.config/flow/models.json`) and project `.agents/setup-state.json`.
 *
 * @param {{ projectRoot?: string | null, configPath?: string | null, env?: NodeJS.ProcessEnv }} [options]
 */
export function loadModelCalibrationConfig({ projectRoot = null, configPath = null, env = process.env } = {}) {
  const baseConfigDir = StudioStateStore.resolveConfigDir(env);
  const resolvedCfg = configPath ? path.resolve(configPath) : path.join(baseConfigDir, "models.json");
  const userCfg = readJsonSafe(resolvedCfg) || {};
  const projectSetup = projectRoot ? readJsonSafe(path.join(path.resolve(projectRoot), ".agents", "setup-state.json")) : {};
  const projectRouting = projectSetup?.model_routing && typeof projectSetup.model_routing === "object" ? projectSetup.model_routing : {};

  return {
    pro_quota_floor: Number(projectRouting.pro_quota_floor ?? userCfg.pro_quota_floor ?? 25),
    swarm_quota_floor: Number(projectRouting.swarm_quota_floor ?? userCfg.swarm_quota_floor ?? 25),
    adversarial_quota_floor: Number(projectRouting.adversarial_quota_floor ?? userCfg.adversarial_quota_floor ?? 20),
    decision_provider: String(projectRouting.decision_provider ?? userCfg.decision_provider ?? env.FLOW_DECISION_PROVIDER ?? "builtin"),
    decision_endpoint: String(projectRouting.decision_endpoint ?? userCfg.decision_endpoint ?? env.FLOW_SYSTEMONE_URL ?? ""),
    models: {
      ...(userCfg.models && typeof userCfg.models === "object" ? userCfg.models : {}),
      ...(projectRouting.models && typeof projectRouting.models === "object" ? projectRouting.models : {}),
    },
  };
}

/**
 * Normalize raw quota (`0..1`, `0..100`, `"77%"`) onto `0..1`.
 *
 * @param {unknown} raw
 * @returns {number | null}
 */
export function normalizeQuotaFraction(raw) {
  if (raw === null || raw === undefined || typeof raw === "boolean") return null;
  const cleaned = String(raw).trim().replace(/%$/, "");
  if (!cleaned) return null;
  const num = Number(cleaned);
  if (!Number.isFinite(num)) return null;
  const clamped = Math.max(0, Math.min(100, num));
  return clamped > 1 ? clamped / 100 : clamped;
}

/**
 * Manage cross-harness live model inventories and `(model, effort)` capability vectors.
 */
export class DynamicModelCatalog {
  /**
   * @param {{ env?: NodeJS.ProcessEnv, projectRoot?: string | null, stateStore?: StudioStateStore, fetchImpl?: typeof fetch }} [options]
   */
  constructor({ env = process.env, projectRoot = null, stateStore = null, fetchImpl = globalThis.fetch } = {}) {
    this.env = env;
    this.projectRoot = projectRoot ? path.resolve(projectRoot) : null;
    this.stateStore = stateStore || new StudioStateStore({ env });
    this.fetchImpl = typeof fetchImpl === "function" ? fetchImpl : null;
    /** @type {Record<string, any>} */
    this.vscodeModelsById = new Map();
    /** @type {Record<string, any> | null} */
    this.modelsDevFlatCache = null;
  }

  /**
   * Ingest live VS Code / Copilot `vscode.lm.selectChatModels({})` entries.
   *
   * @param {any[]} chatModels
   */
  ingestVsCodeChatModels(chatModels = []) {
    this.vscodeModelsById.clear();
    for (const m of chatModels) {
      if (!m || !m.id) continue;
      this.vscodeModelsById.set(String(m.id), {
        id: String(m.id),
        vendor: String(m.vendor || "copilot").toLowerCase(),
        family: String(m.family || m.id),
        version: String(m.version || ""),
        maxInputTokens: Number(m.maxInputTokens) || 128000,
        tool_call: m.capabilities?.toolCalling !== false,
        reasoning: Boolean(m.capabilities?.reasoning),
        supported_efforts: Array.isArray(m.capabilities?.efforts) && m.capabilities.efforts.length > 0
          ? m.capabilities.efforts
          : ["default"],
      });
    }
    return this.vscodeModelsById.size;
  }

  /**
   * Refresh or load `https://models.dev/api.json` SWR metadata without failing offline.
   *
   * @param {{ allowNetwork?: boolean }} [options]
   * @returns {Promise<Record<string, any>>}
   */
  async loadModelsDevMetadata({ allowNetwork = false } = {}) {
    if (this.modelsDevFlatCache) return this.modelsDevFlatCache;
    const state = this.stateStore.load();
    const fetchedMs = state.modelsDevFetchedAt ? Date.parse(state.modelsDevFetchedAt) : 0;
    const ageMs = Date.now() - fetchedMs;
    if (state.modelsDevSnapshot && Number.isFinite(ageMs) && ageMs < MODELS_DEV_TTL_MS) {
      this.modelsDevFlatCache = this.#flattenModelsDev(state.modelsDevSnapshot);
      return this.modelsDevFlatCache;
    }

    if (allowNetwork && this.fetchImpl && this.env.FLOW_OFFLINE !== "1") {
      try {
        const res = await this.fetchImpl(MODELS_DEV_URL, { signal: AbortSignal.timeout(4000) });
        if (res.ok) {
          const rawJson = await res.json();
          if (rawJson && typeof rawJson === "object") {
            const compacted = this.#compactModelsDevSnapshot(rawJson);
            this.stateStore.update((draft) => {
              draft.modelsDevSnapshot = compacted;
              draft.modelsDevFetchedAt = new Date().toISOString();
            });
            this.modelsDevFlatCache = this.#flattenModelsDev(compacted);
            return this.modelsDevFlatCache;
          }
        }
      } catch {
        // Fall through to stale-while-revalidate grace snapshot.
      }
    }

    if (state.modelsDevSnapshot && (!fetchedMs || Date.now() - fetchedMs < MODELS_DEV_GRACE_MS)) {
      this.modelsDevFlatCache = this.#flattenModelsDev(state.modelsDevSnapshot);
      return this.modelsDevFlatCache;
    }
    this.modelsDevFlatCache = {};
    return this.modelsDevFlatCache;
  }

  /**
   * Discover live models for `harness` and normalize into `(model_id, effort)` candidates.
   *
   * @param {{
   *   harness: string,
   *   antigravityCatalog?: any,
   *   codexAppModels?: any[],
   *   customInventory?: any[],
   *   calibration?: Record<string, any>,
   *   allowNetwork?: boolean,
   * }} params
   */
  async discoverHarnessCatalog({
    harness = "agy",
    antigravityCatalog = null,
    codexAppModels = null,
    customInventory = null,
    calibration = null,
    allowNetwork = false,
  } = {}) {
    const cleanHarness = String(harness || "agy").toLowerCase();
    const cfg = calibration || loadModelCalibrationConfig({ projectRoot: this.projectRoot, env: this.env });
    const modelsDev = await this.loadModelsDevMetadata({ allowNetwork });

    /** @type {any[]} */
    let rawEntries = [];
    if (Array.isArray(customInventory)) {
      rawEntries = customInventory;
    } else if (cleanHarness === "agy" || cleanHarness === "antigravity") {
      rawEntries = this.#probeAntigravityEntries(antigravityCatalog);
    } else if (cleanHarness === "codex") {
      rawEntries = this.#probeCodexEntries(codexAppModels);
    } else if (cleanHarness === "claude") {
      rawEntries = this.#probeClaudeEntries();
    } else if (cleanHarness === "opencode") {
      rawEntries = this.#probeOpenCodeEntries();
    } else if (cleanHarness === "cursor" || cleanHarness === "cursor-agent") {
      rawEntries = this.#probeCursorEntries();
    } else if (cleanHarness === "vscode" || cleanHarness === "copilot") {
      rawEntries = this.#probeVsCodeEntries();
    }

    return this.normalizeCandidates(cleanHarness, rawEntries, { modelsDev, calibration: cfg });
  }

  /**
   * Expand raw harness model descriptors into normalized `(model, effort)` capability vectors.
   *
   * @param {string} harness
   * @param {any[]} rawEntries
   * @param {{ modelsDev?: Record<string, any>, calibration?: Record<string, any>, nowMs?: number }} [options]
   */
  normalizeCandidates(harness, rawEntries, { modelsDev = {}, calibration = {}, nowMs = Date.now() } = {}) {
    const cleanHarness = String(harness || "agy").toLowerCase();
    const overrideMap = calibration?.models || {};
    /** @type {any[]} */
    const out = [];

    for (const raw of rawEntries) {
      const entry = typeof raw === "string" ? { model: raw } : raw && typeof raw === "object" ? raw : null;
      if (!entry) continue;
      const modelId = String(entry.model || entry.model_id || entry.id || "").trim();
      if (!modelId || entry.disabled === true) continue;

      const devMeta = this.#lookupModelsDev(modelsDev, modelId);
      const override = overrideMap[modelId] || {};
      const quotaFraction = normalizeQuotaFraction(
        entry.quota_remaining ?? entry.quotaRemaining ?? entry.quota ?? entry.remainingFraction,
      );
      const toolCall = entry.tool_call ?? devMeta?.tool_call ?? true;
      const structuredOutput = entry.structured_output ?? devMeta?.structured_output ?? true;
      const contextWindow = Number(entry.context_window || entry.maxInputTokens || devMeta?.limit?.context || 128000);
      const maxOutput = Number(entry.max_output_tokens || devMeta?.limit?.output || 16384);
      const costInput = Number(entry.cost_input ?? devMeta?.cost?.input ?? NaN);
      const costOutput = Number(entry.cost_output ?? devMeta?.cost?.output ?? NaN);
      const reasoningCapable = Boolean(
        entry.reasoning ??
          override.reasoning ??
          devMeta?.reasoning ??
          (Array.isArray(entry.supported_efforts) && entry.supported_efforts.length > 1),
      );
      const modelRole = String(entry.model_role || override.family || "").toLowerCase();

      const efforts =
        Array.isArray(entry.supported_efforts) && entry.supported_efforts.length > 0
          ? entry.supported_efforts.map((e) => String(e).toLowerCase())
          : reasoningCapable
            ? ["low", "medium", "high", "xhigh"]
            : ["default"];

      const vendor = String(
        entry.vendor ||
          override.vendor ||
          devMeta?.vendor ||
          (modelId.includes("/") ? modelId.split("/")[0] : cleanHarness),
      ).toLowerCase();

      for (const effort of efforts) {
        const effortRank = EFFORT_RANK[effort] ?? 0.55;
        const cooldownFactor = this.stateStore.getAvailabilityFactor(cleanHarness, modelId, effort, nowMs);
        const liveAvail = (quotaFraction ?? 1.0) * cooldownFactor;
        const capabilityIndex = this.#computeCapabilityIndex({
          reasoningCapable,
          effortRank,
          costOutput,
          maxOutput,
          modelRole,
          overrideCapability: override.capability_index,
          entryCapability: entry.capability_index,
          deprecated: Boolean(entry.deprecated),
        });
        const priceIndex = this.#computePriceIndex({ costInput, costOutput, effortRank, modelRole });
        const latencyIndex = this.#computeLatencyIndex({ reasoningCapable, effortRank, priceIndex, modelRole });

        out.push({
          harness: cleanHarness,
          model: modelId,
          display_name: String(entry.displayName || entry.label || entry.display_name || modelId),
          runtime_target: String(override.placeholder || entry.runtime_target || modelId),
          effort,
          effort_rank: effortRank,
          vendor,
          tool_call: Boolean(toolCall),
          structured_output: Boolean(structuredOutput),
          reasoning_capable: reasoningCapable,
          context_window: contextWindow,
          max_output_tokens: maxOutput,
          quota_fraction: quotaFraction,
          live_availability: liveAvail,
          capability_index: capabilityIndex,
          price_index: priceIndex,
          latency_index: latencyIndex,
          deprecated: Boolean(entry.deprecated),
          model_role: modelRole || null,
          fallback_priority: Number(override.priority ?? entry.priority ?? 0),
        });
      }
    }
    return out;
  }

  #computeCapabilityIndex({
    reasoningCapable,
    effortRank,
    costOutput,
    maxOutput,
    modelRole,
    overrideCapability,
    entryCapability,
    deprecated,
  }) {
    if (Number.isFinite(Number(overrideCapability))) return Math.max(0, Math.min(1, Number(overrideCapability)));
    if (Number.isFinite(Number(entryCapability))) return Math.max(0, Math.min(1, Number(entryCapability)));

    let base = reasoningCapable ? 0.52 + 0.36 * effortRank : 0.42;
    if (modelRole === "pro" || modelRole === "strong") {
      base = Math.max(base, 0.78 + 0.2 * effortRank);
    } else if (modelRole === "flash" || modelRole === "fast") {
      base = reasoningCapable ? Math.min(0.84, 0.56 + 0.24 * effortRank) : 0.54;
    } else if (modelRole === "flash_lite" || modelRole === "light") {
      base = Math.min(base, 0.32);
    } else if (Number.isFinite(costOutput) && costOutput > 0) {
      const priceSignal = Math.max(0, Math.min(0.22, Math.log10(1 + costOutput) * 0.14));
      base = Math.min(0.98, base * 0.8 + priceSignal + (maxOutput >= 32768 ? 0.06 : 0));
    }
    if (deprecated) base *= 0.72;
    return Math.max(0.05, Math.min(1.0, Number(base.toFixed(4))));
  }

  #computePriceIndex({ costInput, costOutput, effortRank, modelRole }) {
    if (Number.isFinite(costOutput) && costOutput >= 0) {
      const blended = (Number.isFinite(costInput) ? costInput * 0.25 : 0) + costOutput;
      const norm = Math.min(1, Math.log10(1 + blended) / Math.log10(1 + 75));
      return Number(Math.min(1, norm * (0.75 + 0.25 * effortRank)).toFixed(4));
    }
    if (modelRole === "flash_lite" || modelRole === "light") return 0.08;
    if (modelRole.includes("flash") || modelRole === "fast") return 0.25 * (0.7 + 0.3 * effortRank);
    if (modelRole === "pro" || modelRole === "strong") return 0.82 * (0.8 + 0.2 * effortRank);
    return Number((0.25 + 0.55 * effortRank).toFixed(4));
  }

  #computeLatencyIndex({ reasoningCapable, effortRank, priceIndex, modelRole }) {
    if (modelRole === "flash_lite" || modelRole === "light") return 0.1;
    const reasonLoad = reasoningCapable ? effortRank * 0.65 : 0.15;
    return Number(Math.min(1, 0.6 * reasonLoad + 0.4 * priceIndex).toFixed(4));
  }

  #probeAntigravityEntries(antigravityCatalog) {
    if (!antigravityCatalog || !Array.isArray(antigravityCatalog.models)) return [];
    const roleGroups = antigravityCatalog.tiered_model_ids || {};
    const roleLookup = new Map();
    for (const [roleKey, ids] of Object.entries(roleGroups)) {
      if (!Array.isArray(ids)) continue;
      for (const id of ids) roleLookup.set(String(id), roleKey);
    }
    return antigravityCatalog.models.map((m) => {
      const mId = String(m.model_id || m.model || "");
      const mIdRole = roleLookup.get(mId) || roleLookup.get(String(m.model || ""));
      return {
        model: m.model || m.model_id,
        model_id: m.model_id || m.model,
        displayName: m.label || m.model,
        quota_remaining: m.quota_remaining,
        disabled: m.disabled,
        deprecated: m.deprecated,
        model_role: mIdRole || null,
        reasoning: mIdRole === "pro" || String(m.tag || "").toLowerCase().includes("think"),
        supported_efforts: m.supported_efforts || ["default"],
      };
    });
  }

  #probeCodexEntries(codexAppModels) {
    if (Array.isArray(codexAppModels) && codexAppModels.length > 0) {
      return codexAppModels.map((m) => ({
        model: m.model || m.id || m.slug,
        displayName: m.displayName || m.model || m.id,
        vendor: m.modelProvider || "openai",
        reasoning: Boolean(m.supportedReasoningEfforts?.length || m.supported_reasoning_levels?.length),
        supported_efforts: (m.supportedReasoningEfforts || m.supported_reasoning_levels || []).map((l) =>
          typeof l === "string" ? l : l.reasoningEffort || l.effort,
        ),
        context_window: m.contextWindow || m.context_window,
      }));
    }
    const codexHome = this.env.CODEX_HOME ? path.resolve(this.env.CODEX_HOME) : path.join(os.homedir(), ".codex");
    const cache = readJsonSafe(path.join(codexHome, "models_cache.json"));
    const list = Array.isArray(cache?.models) ? cache.models : [];
    if (list.length > 0) {
      return list.map((m) => ({
        model: m.slug || m.id,
        displayName: m.display_name || m.slug || m.id,
        vendor: "openai",
        reasoning: Array.isArray(m.supported_reasoning_levels) && m.supported_reasoning_levels.length > 0,
        supported_efforts: (m.supported_reasoning_levels || []).map((l) => l.effort || l),
        context_window: m.context_window,
      }));
    }
    const configToml = readTextSafe(path.join(codexHome, "config.toml")) || "";
    const configuredModel = configToml.match(/^\s*model\s*=\s*["']([^"']+)["']/m)?.[1];
    return configuredModel
      ? [{ model: configuredModel, vendor: "openai", reasoning: true, supported_efforts: ["low", "medium", "high", "xhigh"] }]
      : [];
  }

  #probeClaudeEntries() {
    const claudeDir = this.env.CLAUDE_CONFIG_DIR ? path.resolve(this.env.CLAUDE_CONFIG_DIR) : path.join(os.homedir(), ".claude");
    const settings = readJsonSafe(path.join(claudeDir, "settings.json")) || {};
    const candidates = new Set();
    for (const val of [
      this.env.ANTHROPIC_MODEL,
      this.env.ANTHROPIC_DEFAULT_OPUS_MODEL,
      this.env.ANTHROPIC_DEFAULT_SONNET_MODEL,
      this.env.ANTHROPIC_DEFAULT_HAIKU_MODEL,
      this.env.CLAUDE_CODE_SUBAGENT_MODEL,
      settings.model,
    ]) {
      if (typeof val === "string" && val.trim()) candidates.add(val.trim());
    }
    const roleByAlias = new Map();
    if (candidates.size === 0) {
      candidates.add("opus");
      candidates.add("sonnet");
      candidates.add("haiku");
      roleByAlias.set("opus", { model_role: "strong", cost_input: 5, cost_output: 25, priority: 30 });
      roleByAlias.set("sonnet", { model_role: "flash", cost_input: 3, cost_output: 15, priority: 20 });
      roleByAlias.set("haiku", { model_role: "light", cost_input: 1, cost_output: 5, priority: 10 });
    }
    return Array.from(candidates).map((id) => ({
      model: id,
      vendor: "anthropic",
      reasoning: true,
      supported_efforts: ["low", "medium", "high", "xhigh", "max"],
      ...(roleByAlias.get(id) || {}),
    }));
  }

  #probeOpenCodeEntries() {
    const ocBin = whichSync("opencode", this.env);
    if (!ocBin || this.env.FLOW_DISABLE_CLI_PROBES === "1") return [];
    try {
      const raw = execFileSync(ocBin, ["models", "--verbose"], {
        encoding: "utf8",
        timeout: 3500,
        stdio: ["ignore", "pipe", "ignore"],
      });
      const out = [];
      for (const line of raw.split("\n")) {
        const clean = line.trim();
        if (!clean || !clean.includes("/")) continue;
        const [provider, ...rest] = clean.split(/\s+/)[0].split("/");
        out.push({
          model: `${provider}/${rest.join("/")}`,
          vendor: provider,
          reasoning: clean.toLowerCase().includes("reasoning"),
          supported_efforts: ["low", "medium", "high", "max"],
        });
      }
      return out;
    } catch {
      return [];
    }
  }

  #probeCursorEntries() {
    const cursorBin = whichSync("cursor-agent", this.env);
    if (cursorBin && this.env.FLOW_DISABLE_CLI_PROBES !== "1") {
      try {
        const raw = execFileSync(cursorBin, ["--list-models"], {
          encoding: "utf8",
          timeout: 3500,
          stdio: ["ignore", "pipe", "ignore"],
        });
        const models = [];
        for (const line of raw.split("\n")) {
          const clean = line.trim();
          if (!clean || clean.startsWith("#")) continue;
          const id = clean.split(/\s+/)[0];
          if (id) models.push({ model: id, vendor: "cursor" });
        }
        if (models.length > 0) return models;
      } catch {
        // Fallback below.
      }
    }
    return [
      { model: "auto", vendor: "cursor", capability_index: 0.72 },
      { model: "fast", vendor: "cursor", model_role: "fast", capability_index: 0.5 },
    ];
  }

  #probeVsCodeEntries() {
    return Array.from(this.vscodeModelsById.values());
  }

  #compactModelsDevSnapshot(rawJson) {
    /** @type {Record<string, any>} */
    const compact = {};
    for (const [providerId, prov] of Object.entries(rawJson)) {
      if (!prov || typeof prov !== "object" || !prov.models || typeof prov.models !== "object") continue;
      for (const [mKey, m] of Object.entries(prov.models)) {
        if (!m || typeof m !== "object") continue;
        const fullKey = `${providerId}/${mKey}`;
        compact[fullKey] = {
          id: m.id || mKey,
          vendor: providerId,
          tool_call: m.tool_call,
          structured_output: m.structured_output,
          reasoning: m.reasoning,
          limit: m.limit || null,
          cost: m.cost || null,
          release_date: m.release_date || null,
        };
      }
    }
    return compact;
  }

  #flattenModelsDev(snapshot) {
    /** @type {Record<string, any>} */
    const flat = {};
    for (const [fullKey, item] of Object.entries(snapshot || {})) {
      if (!item || typeof item !== "object") continue;
      flat[fullKey] = item;
      const bare = fullKey.includes("/") ? fullKey.split("/").slice(1).join("/") : fullKey;
      if (!flat[bare]) flat[bare] = item;
    }
    return flat;
  }

  #lookupModelsDev(flat, modelId) {
    if (!flat) return null;
    if (flat[modelId]) return flat[modelId];
    const bare = String(modelId).includes("/") ? String(modelId).split("/").slice(1).join("/") : String(modelId);
    return flat[bare] || null;
  }
}
