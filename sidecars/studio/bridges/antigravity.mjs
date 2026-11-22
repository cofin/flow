/**
 * Google Antigravity LanguageServerService ConnectRPC bridge.
 *
 * Handles workspace/worktree project binding (`ReadProjects` + `CreateProject`),
 * live model & quota inspection (`GetCascadeModelConfigData` + `GetAvailableModels`),
 * trajectory discovery, clean-room Frontier conversation delegation, and cancellation.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { readJsonSafe, StudioStateStore, uriToWorkspacePath, writeJsonAtomic } from "../core/fs-io.mjs";
import { DynamicModelCatalog } from "../models/inventory.mjs";

const LS_SERVICE_PREFIX = "/exa.language_server_pb.LanguageServerService/";

/**
 * Discovers live Google Antigravity Language Server daemons under daemon registry directories
 * when `ANTIGRAVITY_LS_ADDRESS` is not configured in the environment.
 */
export class LanguageServerDaemonLocator {
  static candidateRoots(env = process.env) {
    const home = env.HOME || env.USERPROFILE || os.homedir();
    const roots = [];
    const seen = new Set();
    const pushRoot = (dirPath) => {
      const clean = String(dirPath || "").trim();
      if (!clean || seen.has(clean)) return;
      seen.add(clean);
      roots.push(clean);
    };
    pushRoot(env.ANTIGRAVITY_APP_DATA_DIR);
    pushRoot(env.FLOW_APP_DATA_DIR);
    const geminiDir = path.join(home, ".gemini");
    if (fs.existsSync(geminiDir)) {
      try {
        for (const entry of fs.readdirSync(geminiDir, { withFileTypes: true })) {
          if (entry.isDirectory() || entry.isSymbolicLink()) pushRoot(path.join(geminiDir, entry.name));
        }
      } catch {
        // Ignore unreadable daemon directories inside restricted sandboxes.
      }
    }
    return roots;
  }

  static isDiscoveryDisabled(env = process.env) {
    if (String(env?.FLOW_DISABLE_DAEMON_DISCOVERY || "").trim() === "1") return true;
    return (
      Boolean(env) &&
      Object.prototype.hasOwnProperty.call(env, "ANTIGRAVITY_LS_ADDRESS") &&
      String(env.ANTIGRAVITY_LS_ADDRESS ?? "").trim() === ""
    );
  }

  static readCandidates(env = process.env) {
    if (LanguageServerDaemonLocator.isDiscoveryDisabled(env)) return [];
    const candidates = [];
    const seenFiles = new Set();
    for (const root of LanguageServerDaemonLocator.candidateRoots(env)) {
      const daemonDir = path.join(root, "daemon");
      if (!fs.existsSync(daemonDir)) continue;
      let files = [];
      try {
        files = fs.readdirSync(daemonDir).filter((name) => name.endsWith(".json")).sort();
      } catch {
        continue;
      }
      for (const fileName of files) {
        const filePath = path.join(daemonDir, fileName);
        if (seenFiles.has(filePath)) continue;
        seenFiles.add(filePath);
        try {
          const stat = fs.statSync(filePath);
          const raw = JSON.parse(fs.readFileSync(filePath, "utf8"));
          if (!raw || typeof raw !== "object" || Array.isArray(raw)) continue;
          const token = String(raw.csrfToken ?? raw.csrf_token ?? "").trim();
          const pidRaw = Number(raw.pid ?? raw.processId ?? 0);
          const pid = Number.isFinite(pidRaw) && pidRaw > 0 ? pidRaw : null;
          let address = typeof raw.address === "string" && raw.address.trim() ? raw.address.trim() : "";
          if (!address) {
            const portRaw = Number(raw.httpPort ?? raw.port ?? raw.httpsPort ?? 0);
            if (Number.isFinite(portRaw) && portRaw > 0) {
              const scheme = raw.httpPort || !raw.httpsPort ? "http" : "https";
              address = `${scheme}://127.0.0.1:${portRaw}`;
            }
          }
          if (!address || !token) continue;
          if (!/^https?:\/\//i.test(address)) address = `http://${address}`;
          if (pid !== null) {
            try {
              process.kill(pid, 0);
            } catch (err) {
              if (err && err.code === "ESRCH") continue;
            }
          }
          const priority = fileName.startsWith("ls_") ? 2 : fileName.startsWith("hub_") ? 1 : 0;
          candidates.push({ address: address.replace(/\/+$/, ""), token, pid, sourceFile: filePath, priority, mtimeMs: stat.mtimeMs || 0 });
        } catch {
          // Ignore malformed or concurrently rotated daemon files.
        }
      }
    }
    return candidates.sort((a, b) => b.priority - a.priority || b.mtimeMs - a.mtimeMs);
  }

  static async discover({ env = process.env, fetchImpl = globalThis.fetch, probe = true, timeoutMs = 400 } = {}) {
    const explicitAddress = String(env.ANTIGRAVITY_LS_ADDRESS || "").trim();
    const explicitToken = String(env.ANTIGRAVITY_CSRF_TOKEN || "").trim();
    if (explicitAddress) {
      const normalized = /^https?:\/\//i.test(explicitAddress) ? explicitAddress : `http://${explicitAddress}`;
      return { address: normalized.replace(/\/+$/, ""), token: explicitToken, source: "env" };
    }
    if (LanguageServerDaemonLocator.isDiscoveryDisabled(env)) return null;
    const candidates = LanguageServerDaemonLocator.readCandidates(env);
    if (candidates.length === 0) return null;
    if (!probe || typeof fetchImpl !== "function") return { ...candidates[0], source: "daemon_file" };
    for (const candidate of candidates) {
      try {
        const res = await fetchImpl(`${candidate.address}${LS_SERVICE_PREFIX}ListProjects`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Connect-Protocol-Version": "1", "x-codeium-csrf-token": candidate.token },
          body: "{}",
          signal: AbortSignal.timeout(timeoutMs),
        });
        if (res.status < 500) return { ...candidate, source: "daemon_probe" };
      } catch {
        // Try next daemon entry.
      }
    }
    return null;
  }
}

/**
 * Extract all folder URIs from an Antigravity project object including worktree environments.
 *
 * @param {any} proj
 * @returns {{ defaultUris: string[], environments: Array<{ id: string, uris: string[] }> }}
 */
export function extractProjectResources(proj) {
  /** @type {string[]} */
  const defaultUris = [];
  const pushUnique = (target, raw) => {
    if (typeof raw !== "string" || !raw.trim()) return;
    const clean = raw.trim();
    if (!target.includes(clean)) target.push(clean);
  };
  const pushResource = (target, res) => {
    if (!res || typeof res !== "object") return;
    pushUnique(target, res.folderUri);
    pushUnique(target, res.gitFolder?.folderUri);
  };

  if (Array.isArray(proj?.workspaceUris)) {
    for (const u of proj.workspaceUris) pushUnique(defaultUris, u);
  }
  if (Array.isArray(proj?.projectResources?.resources)) {
    for (const res of proj.projectResources.resources) pushResource(defaultUris, res);
  }
  pushUnique(defaultUris, proj?.gitFolder?.folderUri);

  /** @type {Array<{ id: string, uris: string[] }>} */
  const environments = [];
  const envList = Array.isArray(proj?.environments)
    ? proj.environments
    : Array.isArray(proj?.environments?.environments)
      ? proj.environments.environments
      : [];
  for (const envItem of envList) {
    if (!envItem || typeof envItem !== "object" || !envItem.id) continue;
    const uris = [];
    if (Array.isArray(envItem.resources?.resources)) {
      for (const res of envItem.resources.resources) pushResource(uris, res);
    }
    if (uris.length > 0) environments.push({ id: String(envItem.id), uris });
  }
  return { defaultUris, environments };
}

export class AntigravityBridge {
  /**
   * @param {NodeJS.ProcessEnv} [env]
   */
  constructor(env = process.env) {
    this.env = env;
    this._daemonCache = { at: 0, value: null };
  }

  get baseUrl() {
    const raw = this.env.ANTIGRAVITY_LS_ADDRESS || "";
    if (raw) return raw.startsWith("http") ? raw.replace(/\/+$/, "") : `http://${raw.replace(/\/+$/, "")}`;
    return this._daemonCache.value?.address || null;
  }

  get csrfToken() {
    return this.env.ANTIGRAVITY_CSRF_TOKEN || this._daemonCache.value?.token || "";
  }

  get available() {
    return Boolean(this.env.ANTIGRAVITY_LS_ADDRESS || this._daemonCache.value || LanguageServerDaemonLocator.readCandidates(this.env).length > 0);
  }

  async resolveConnection({ refresh = false } = {}) {
    if (this.env.ANTIGRAVITY_LS_ADDRESS) {
      const raw = String(this.env.ANTIGRAVITY_LS_ADDRESS).trim();
      const address = (raw.startsWith("http") ? raw : `http://${raw}`).replace(/\/+$/, "");
      return { address, token: this.env.ANTIGRAVITY_CSRF_TOKEN || "", source: "env" };
    }
    const now = Date.now();
    if (!refresh && this._daemonCache.at > 0 && now - this._daemonCache.at < 10_000) {
      return this._daemonCache.value;
    }
    const discovered = await LanguageServerDaemonLocator.discover({ env: this.env });
    this._daemonCache = { at: Date.now(), value: discovered };
    return discovered;
  }

  /**
   * Call a LanguageServerService ConnectRPC method.
   *
   * @param {string} method
   * @param {Record<string, any>} [body]
   */
  async call(method, body = {}) {
    const conn = await this.resolveConnection();
    if (!conn?.address) {
      return { ok: false, error: "Antigravity LanguageServer is not running or configured." };
    }
    const headers = {
      "Content-Type": "application/json",
      "Connect-Protocol-Version": "1",
      ...(conn.token ? { "x-codeium-csrf-token": conn.token } : {}),
    };
    try {
      const resp = await fetch(`${conn.address}${LS_SERVICE_PREFIX}${method}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      const text = await resp.text();
      if (!resp.ok) {
        if (conn.source !== "env") this._daemonCache.at = 0;
        return { ok: false, status: resp.status, error: text.slice(0, 400) || `HTTP ${resp.status}` };
      }
      return { ok: true, value: text ? JSON.parse(text) : {} };
    } catch (err) {
      if (conn.source !== "env") this._daemonCache.at = 0;
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  }

  /**
   * Query live Antigravity model configs, quota summary, and normalized capability vectors.
   */
  async getModelsAndQuota() {
    if (!this.available) {
      return { connected: false, models: [], tieredModelIds: {}, defaultOverrideModel: "", quota: null, normalized: [] };
    }
    const [cfgRes, modelsRes, quotaRes] = await Promise.all([
      this.call("GetCascadeModelConfigData", {}),
      this.call("GetAvailableModels", {}),
      this.call("RetrieveUserQuotaSummary", {}),
    ]);
    const cfgPayload = cfgRes.ok ? cfgRes.value : {};
    const modelsPayload = modelsRes.ok ? modelsRes.value : {};
    const rawModels = modelsPayload?.models && typeof modelsPayload.models === "object" ? modelsPayload.models : {};
    const deprecatedRaw = modelsPayload?.deprecatedModelIds;
    const deprecatedSet = new Set(
      Array.isArray(deprecatedRaw)
        ? deprecatedRaw.map(String)
        : deprecatedRaw && typeof deprecatedRaw === "object"
          ? Object.keys(deprecatedRaw)
          : [],
    );

    const modelsByEnum = new Map();
    const pushModel = (entry) => {
      if (!entry.model) return;
      const prev = modelsByEnum.get(entry.model);
      if (prev) {
        if (prev.quota_remaining === null && entry.quota_remaining !== null) prev.quota_remaining = entry.quota_remaining;
        if (entry.deprecated) prev.deprecated = true;
        if (entry.is_custom) prev.is_custom = true;
        if (!prev.tag && entry.tag) prev.tag = entry.tag;
        return;
      }
      modelsByEnum.set(entry.model, { ...entry, is_custom: Boolean(entry.is_custom) });
    };

    const isUtilityModel = (mId, mEnum, info) => {
      const fields = [mId, mEnum, info?.displayName, info?.label].map((v) => String(v || "").trim()).filter(Boolean);
      return fields.some((value) => /^(?:tab_|lsp-slot)/i.test(value) || /[-_]compaction\b|[-_]image\b/i.test(value));
    };
    const isCustomEntry = (obj) => obj?.isCustom === true || obj?.custom === true;

    const clientConfigs = Array.isArray(cfgPayload?.clientModelConfigs) ? cfgPayload.clientModelConfigs : [];
    for (const c of clientConfigs) {
      const mEnum = String(c?.modelOrAlias?.model || c?.modelOrAlias?.alias || "").trim();
      if (!mEnum) continue;
      const frac = c?.quotaInfo?.remainingFraction;
      pushModel({
        id: c?.modelId || c?.modelOrAlias?.alias || mEnum,
        model_id: c?.modelId || c?.modelOrAlias?.alias || mEnum,
        model: mEnum,
        displayName: c?.label || mEnum,
        label: c?.label || mEnum,
        tag: c?.tagTitle || "",
        is_custom: isCustomEntry(c),
        disabled: Boolean(c?.disabled),
        deprecated: deprecatedSet.has(String(c?.modelId || "")),
        quota_remaining: Number.isFinite(Number(frac)) ? Number(frac) : null,
      });
    }

    const hasPickerConfigs = clientConfigs.length > 0;
    for (const [mId, info] of Object.entries(rawModels)) {
      if (!info || typeof info !== "object") continue;
      const mEnum = String(info.model || mId).trim();
      const isCustom = isCustomEntry(info);
      if (hasPickerConfigs && !isCustom) continue;
      if (deprecatedSet.has(mId) || info.disabled === true || (!isCustom && isUtilityModel(mId, mEnum, info))) {
        continue;
      }
      const frac = info?.quotaInfo?.remainingFraction;
      pushModel({
        id: mId,
        model_id: mId,
        model: mEnum,
        displayName: info.displayName || info.label || mId,
        label: info.displayName || info.label || mId,
        tag: info.tagTitle || "",
        is_custom: isCustom,
        disabled: Boolean(info.disabled),
        deprecated: deprecatedSet.has(mId),
        quota_remaining: Number.isFinite(Number(frac)) ? Number(frac) : null,
      });
    }

    const models = Array.from(modelsByEnum.values());
    const tiered = modelsPayload?.tieredModelIds || {};
    const catalog = new DynamicModelCatalog({ env: this.env });
    const normalized = catalog.normalizeCandidates("agy", models.map((m) => {
      let role = null;
      if (Array.isArray(tiered.pro) && tiered.pro.includes(m.model_id)) role = "pro";
      else if (Array.isArray(tiered.flash) && tiered.flash.includes(m.model_id)) role = "flash";
      else if (Array.isArray(tiered.flashLite) && tiered.flashLite.includes(m.model_id)) role = "flash_lite";
      return { ...m, model_role: role };
    }));

    return {
      connected: Boolean(modelsRes.ok || cfgRes.ok),
      defaultOverrideModel: String(cfgPayload?.defaultOverrideModelConfig?.modelOrAlias?.model || ""),
      models,
      tieredModelIds: tiered,
      quota: quotaRes.ok ? quotaRes.value : null,
      normalized,
    };
  }

  /**
   * @param {string} [workspacePath]
   */
  async listTrajectories(workspacePath) {
    if (!this.available) return { connected: false, trajectories: [] };
    const res = await this.call("GetAllCascadeTrajectories", {});
    if (!res.ok) return { connected: false, trajectories: [], error: res.error };

    const targetUri = workspacePath ? pathToFileURL(path.resolve(workspacePath)).href : null;
    const rawMap = res.value?.trajectorySummaries || res.value?.trajectories || {};
    const list = Object.entries(rawMap).map(([cascadeId, item]) => ({
      cascadeId,
      title: item?.summary || item?.annotations?.title || cascadeId.slice(0, 8),
      status: item?.status || "IDLE",
      updatedAt: item?.lastModifiedTime || null,
      workspaceUris: Array.isArray(item?.workspaces)
        ? item.workspaces.map((w) => w?.workspaceFolderAbsoluteUri || w?.workspaceFolderUri || w).filter(Boolean)
        : [],
    }));
    const filtered = targetUri
      ? list.filter((t) => t.workspaceUris.length === 0 || t.workspaceUris.some((u) => String(u).startsWith(targetUri)))
      : list;
    return { connected: true, trajectories: filtered.slice(0, 25) };
  }

  /**
   * Discover open workspaces from trajectories and projects (including worktree environments).
   *
   * @param {{ conversationId?: string }} [options]
   */
  async discoverWorkspaces(options = {}) {
    if (!this.available) return { activeWorkspace: null, workspaces: [] };
    const conversationId = String(options.conversationId || this.env.ANTIGRAVITY_CONVERSATION_ID || "").trim();
    const [trajRes, listProjRes, getProjRes] = await Promise.all([
      this.call("GetAllCascadeTrajectories", {}),
      this.call("ListProjects", {}),
      this.call("GetProjects", {}),
    ]);

    const discovered = new Set();
    let activeWorkspace = null;

    if (trajRes.ok) {
      const rawMap = trajRes.value?.trajectorySummaries || trajRes.value?.trajectories || {};
      const entries = Object.entries(rawMap).map(([cascadeId, item]) => ({
        cascadeId,
        status: String(item?.status || ""),
        updatedAt: String(item?.lastModifiedTime || ""),
        workspaces: Array.isArray(item?.workspaces)
          ? item.workspaces
              .map((w) => uriToWorkspacePath(w?.workspaceFolderAbsoluteUri || w?.workspaceFolderUri || w?.folderUri || w))
              .filter(Boolean)
          : [],
      }));
      if (conversationId) {
        const hit = entries.find((e) => e.cascadeId === conversationId && e.workspaces.length > 0);
        if (hit) activeWorkspace = hit.workspaces[0];
      }
      const sorted = entries
        .filter((e) => e.workspaces.length > 0)
        .sort((a, b) => (b.status.includes("RUNNING") ? 1 : 0) - (a.status.includes("RUNNING") ? 1 : 0) || b.updatedAt.localeCompare(a.updatedAt));
      if (!activeWorkspace && sorted.length > 0) activeWorkspace = sorted[0].workspaces[0];
      for (const e of sorted) for (const ws of e.workspaces) if (ws) discovered.add(ws);
    }

    const projects = await this.#collectProjects(getProjRes, listProjRes);
    for (const proj of projects) {
      const res = extractProjectResources(proj);
      for (const uri of [...res.defaultUris, ...res.environments.flatMap((e) => e.uris)]) {
        const p = uriToWorkspacePath(uri);
        if (p) {
          if (!activeWorkspace) activeWorkspace = p;
          discovered.add(p);
        }
      }
    }

    return { activeWorkspace, workspaces: Array.from(discovered) };
  }

  /**
   * Resolve or auto-create a workspace project and launch a bound conversation.
   *
   * @param {{ workspacePath: string, message: string, title?: string, preferredModel?: string }} params
   */
  async startWorkspaceConversation(params) {
    const workspace = path.resolve(params.workspacePath);
    const message = String(params.message || "").trim();
    if (!message) throw new Error("Conversation message cannot be empty.");
    if (!this.available) {
      return {
        conversation_id: null,
        workspace_bound: false,
        workspace,
        prompt_sent: false,
        error: "Antigravity LanguageServer ConnectRPC is not configured.",
      };
    }

    const fileUri = pathToFileURL(workspace).href;
    const projectBinding = await this.#resolveOrCreateProject(workspace, fileUri);
    let planModel = params.preferredModel || null;
    if (!planModel) {
      const mRes = await this.getModelsAndQuota();
      const firstHealthy = mRes.models.find((m) => !m.disabled && !m.deprecated && m.model);
      planModel = firstHealthy?.model || null;
    }

    const startRes = await this.call("StartCascade", {
      source: "CORTEX_TRAJECTORY_SOURCE_CASCADE_CLIENT",
      trajectoryType: "CORTEX_TRAJECTORY_TYPE_CASCADE",
      customAgentSpec: {
        codingAgent: { googleMode: true },
        commandExecutionPolicy: "sandbox",
        enforcedWorkspaceValidation: false,
        ...(planModel ? { cascadeConfig: { plannerConfig: { planModel, requestedModel: { model: planModel } } } } : {}),
      },
      ...(projectBinding ? { projectEnvConfig: projectBinding } : { workspaceUris: [fileUri] }),
    });

    if (!startRes.ok || !startRes.value?.cascadeId) {
      return {
        conversation_id: null,
        workspace_bound: false,
        project_id: projectBinding?.projectId || null,
        workspace,
        prompt_sent: false,
        error: startRes.error || "StartCascade returned no cascadeId.",
      };
    }

    const cascadeId = startRes.value.cascadeId;
    if (params.title && String(params.title).trim()) {
      await this.call("UpdateConversationAnnotations", {
        cascadeIds: [cascadeId],
        annotations: { title: String(params.title).trim() },
        mergeAnnotations: true,
      });
    }

    const sendRes = await this.call("SendUserCascadeMessage", {
      cascadeId,
      items: [{ text: message }],
      blocking: false,
      ...(planModel ? { cascadeConfig: { plannerConfig: { requestedModel: { model: planModel } } } } : {}),
    });

    return {
      conversation_id: cascadeId,
      workspace_bound: true,
      project_id: projectBinding?.projectId || null,
      workspace,
      prompt_sent: Boolean(sendRes.ok),
    };
  }

  async forkConversation(cascadeId) {
    return this.call("ForkConversation", { cascadeId });
  }

  async stopConversation(cascadeId) {
    return this.call("ForceStopCascadeTree", { cascadeId });
  }

  /**
   * List active/recent conversations filtered optionally by workspace or status (`flow agent list`).
   *
   * @param {{ workspace?: string | null, status?: string, includeSubagents?: boolean, limit?: number }} [options]
   */
  async listConversations({ workspace = null, status = "all", includeSubagents = false, limit = 30 } = {}) {
    const res = await this.call("GetAllCascadeTrajectories", { excludeSubtrajectories: !includeSubagents });
    if (!res.ok) return { ok: false, ls_connected: false, conversations: [], error: res.error };
    const rawMap = res.value?.trajectorySummaries || res.value?.trajectory_summaries || {};
    const targetLower = workspace ? path.resolve(workspace).toLowerCase() : null;
    const statusFilter = ["running", "idle", "all"].includes(String(status || "").toLowerCase()) ? String(status).toLowerCase() : "all";
    const items = [];
    for (const [convId, raw] of Object.entries(rawMap)) {
      const wsList = Array.isArray(raw?.workspaces)
        ? raw.workspaces.map((w) => uriToWorkspacePath(w?.workspaceFolderAbsoluteUri || w?.workspaceFolderUri || w?.folderUri || w)).filter(Boolean)
        : [];
      if (targetLower && !wsList.some((w) => w.toLowerCase() === targetLower || w.toLowerCase().startsWith(`${targetLower}/`))) {
        continue;
      }
      const rawStatus = String(raw?.status || "").toUpperCase();
      const runStatus = rawStatus.includes("RUNNING") ? "running" : "idle";
      if (statusFilter === "running" && runStatus !== "running") continue;
      if (statusFilter === "idle" && runStatus !== "idle") continue;
      items.push({
        conversation_id: convId,
        title: raw?.summary || raw?.annotations?.title || convId.slice(0, 8),
        status: runStatus,
        raw_status: raw?.status || null,
        workspaces: wsList,
        killed: Boolean(raw?.killed),
        last_modified_at: raw?.lastModifiedTime || null,
      });
    }
    items.sort((a, b) => String(b.last_modified_at || "").localeCompare(String(a.last_modified_at || "")));
    return { ok: true, ls_connected: true, total: items.length, conversations: items.slice(0, Math.max(1, limit)) };
  }

  /**
   * Inspect one conversation's trajectory summary and recent RPC steps (`flow agent inspect`).
   *
   * @param {string} conversationId
   * @param {{ steps?: number }} [options]
   */
  async inspectConversation(conversationId, { steps = 8 } = {}) {
    const convId = String(conversationId || "").trim();
    if (!convId || /[/\\]|\.\./.test(convId)) throw new Error(`Invalid conversation ID: ${conversationId}`);
    const [trajRes, stepsRes] = await Promise.all([
      this.call("GetAllCascadeTrajectories", { excludeSubtrajectories: false }),
      this.call("GetCascadeTrajectorySteps", { cascadeId: convId }),
    ]);
    const rawMap = trajRes.ok ? trajRes.value?.trajectorySummaries || trajRes.value?.trajectory_summaries || {} : {};
    const summary = rawMap[convId] || null;
    const rpcSteps = stepsRes.ok && Array.isArray(stepsRes.value?.steps) ? stepsRes.value.steps : [];
    return {
      ok: Boolean(trajRes.ok || summary),
      ls_connected: Boolean(trajRes.ok),
      conversation_id: convId,
      found: Boolean(summary),
      summary: summary ? { title: summary.summary || summary.annotations?.title || null, status: summary.status || null } : null,
      steps: rpcSteps.slice(-Math.max(1, steps)).map((s, idx) => ({
        step_index: typeof s?.stepIndex === "number" ? s.stepIndex : idx,
        type: s?.type || null,
        status: s?.status || null,
      })),
    };
  }

  /**
   * Send a follow-up message to an existing conversation (`flow agent send`).
   *
   * @param {{ conversationId: string, prompt: string, blocking?: boolean }} params
   */
  async sendMessage({ conversationId, prompt, blocking = false } = {}) {
    const convId = String(conversationId || "").trim();
    if (!convId || /[/\\]|\.\./.test(convId)) throw new Error(`Invalid conversation ID: ${conversationId}`);
    if (!String(prompt || "").trim()) throw new Error("prompt must be non-empty.");
    const sendRes = await this.call("SendUserCascadeMessage", {
      cascadeId: convId,
      items: [{ text: String(prompt) }],
      blocking: Boolean(blocking),
    });
    return {
      ok: Boolean(sendRes.ok),
      conversation_id: convId,
      prompt_sent: Boolean(sendRes.ok),
      ...(sendRes.ok ? {} : { error: sendRes.error || "SendUserCascadeMessage failed" }),
    };
  }

  /**
   * Detect whether a sidecar `baseUrl` points to a non-loopback host exposing an
   * unproxied loopback `webPort` directly.
   *
   * @param {string} baseUrl
   * @param {number | string} webPort
   * @returns {boolean}
   */
  static isUnproxiedRemoteSidecarUrl(baseUrl, webPort) {
    const portNum = Number(webPort);
    if (!baseUrl || !Number.isInteger(portNum) || portNum <= 0 || portNum > 65535) {
      return false;
    }
    let parsed;
    try {
      parsed = new URL(String(baseUrl).trim());
    } catch {
      return false;
    }
    const host = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, "");
    if (!host || host === "localhost" || host === "127.0.0.1" || host === "::1") {
      return false;
    }
    if (parsed.port && Number.parseInt(parsed.port, 10) === portNum) {
      return true;
    }
    const firstLabel = host.split(".")[0] || "";
    const encodedMatch = firstLabel.match(/^b(?:[0-9a-f]{8}|[0-9a-f]{32})([0-9a-f]{4})[0-9a-f]{18}$/i);
    if (encodedMatch) {
      return Number.parseInt(encodedMatch[1], 16) === portNum;
    }
    return false;
  }

  /**
   * Verify whether the registered sidecar `baseUrl` requires a bounded cold-start reload.
   *
   * @param {{ stateDir?: string | null, nowMs?: number, maxAttempts?: number, windowMs?: number }} [options]
   * @returns {Promise<{ ok: boolean, unproxied: boolean, shouldRestart: boolean, attempts: number }>}
   */
  async verifyGatewayBinding({ stateDir = null, nowMs = Date.now(), maxAttempts = 2, windowMs = 600_000 } = {}) {
    const webPort = Number.parseInt(String(this.env.ANTIGRAVITY_SIDECAR_WEB_PORT || ""), 10);
    if (!Number.isInteger(webPort) || webPort <= 0) {
      return { ok: true, unproxied: false, shouldRestart: false, attempts: 0 };
    }
    const execDirRaw =
      typeof this.env.ANTIGRAVITY_EXECUTABLE_DATA_DIR === "string"
        ? this.env.ANTIGRAVITY_EXECUTABLE_DATA_DIR.trim()
        : "";
    const resolvedStateDir = stateDir
      ? path.resolve(stateDir)
      : execDirRaw
        ? path.resolve(execDirRaw)
        : StudioStateStore.resolveConfigDir(this.env);
    const stateFile = path.join(resolvedStateDir, "gateway-recheck.json");

    const res = await this.call("GetSidecars", {});
    const sidecars = res?.ok && Array.isArray(res.value?.sidecars) ? res.value.sidecars : null;
    if (!sidecars) {
      return { ok: true, unproxied: false, shouldRestart: false, attempts: 0 };
    }
    const entry =
      sidecars.find((s) => Number(s?.webPort ?? s?.web_port ?? 0) === webPort) ||
      sidecars.find((s) => String(s?.sidecarId ?? s?.id ?? "").endsWith("/studio"));
    if (!entry) {
      return { ok: true, unproxied: false, shouldRestart: false, attempts: 0 };
    }

    const baseUrl = String(entry.baseUrl ?? entry.base_url ?? "");
    const unproxied = AntigravityBridge.isUnproxiedRemoteSidecarUrl(baseUrl, webPort);
    const prev = readJsonSafe(stateFile);

    if (!unproxied) {
      if (prev && Number(prev.attempts || 0) > 0) {
        try {
          writeJsonAtomic(stateFile, { attempts: 0, windowStartMs: nowMs, updatedAtMs: nowMs });
        } catch {
          // Ignore read-only data directory cleanup errors.
        }
      }
      return { ok: true, unproxied: false, shouldRestart: false, attempts: 0 };
    }

    const prevStart = Number(prev?.windowStartMs || 0);
    const inWindow = prevStart > 0 && nowMs - prevStart < windowMs;
    const prevAttempts = inWindow ? Number(prev?.attempts || 0) : 0;
    if (prevAttempts >= maxAttempts) {
      return { ok: false, unproxied: true, shouldRestart: false, attempts: prevAttempts };
    }

    const nextAttempts = prevAttempts + 1;
    const windowStartMs = inWindow ? prevStart : nowMs;
    try {
      fs.mkdirSync(resolvedStateDir, { recursive: true });
      writeJsonAtomic(stateFile, {
        attempts: nextAttempts,
        windowStartMs,
        updatedAtMs: nowMs,
      });
    } catch {
      // Allow a clean single recovery exit even when the state path is read-only.
    }
    return { ok: false, unproxied: true, shouldRestart: true, attempts: nextAttempts };
  }

  async #collectProjects(getProjRes, listProjRes) {
    const out = [];
    if (getProjRes.ok && Array.isArray(getProjRes.value?.projects)) out.push(...getProjRes.value.projects);
    const ids = listProjRes.ok
      ? Array.isArray(listProjRes.value?.ids)
        ? listProjRes.value.ids
        : Array.isArray(listProjRes.value?.projectIds)
          ? listProjRes.value.projectIds
          : []
      : [];
    const filteredIds = ids.filter((id) => id && id !== "outside-of-project");
    if (filteredIds.length > 0) {
      const readRes = await this.call("ReadProjects", { ids: filteredIds });
      if (readRes.ok && Array.isArray(readRes.value?.projects)) out.push(...readRes.value.projects);
    }
    return out;
  }

  async #resolveOrCreateProject(workspace, fileUri) {
    const [getRes, listRes] = await Promise.all([this.call("GetProjects", {}), this.call("ListProjects", {})]);
    const projects = await this.#collectProjects(getRes, listRes);
    for (const proj of projects) {
      if (!proj?.id || proj.id === "outside-of-project" || proj.archived) continue;
      const res = extractProjectResources(proj);
      if (res.defaultUris.some((u) => u === fileUri || uriToWorkspacePath(u) === workspace)) {
        return { projectId: proj.id, defaultProjectEnvironment: {} };
      }
      const envHit = res.environments.find((env) => env.uris.some((u) => u === fileUri || uriToWorkspacePath(u) === workspace));
      if (envHit) {
        return { projectId: proj.id, environmentId: envHit.id };
      }
    }
    if (!fs.existsSync(workspace)) return null;
    const projectId = crypto.randomUUID();
    const isGit = fs.existsSync(path.join(workspace, ".git"));
    const createRes = await this.call("CreateProject", {
      project: {
        id: projectId,
        name: path.basename(workspace) || "Workspace",
        projectResources: { resources: [isGit ? { gitFolder: { folderUri: fileUri } } : { folderUri: fileUri }] },
        isWorkspaceOnly: false,
      },
    });
    return createRes.ok ? { projectId, defaultProjectEnvironment: {} } : null;
  }
}

export { AntigravityBridge as AntigravityCoordinator };
