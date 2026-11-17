/**
 * Google Antigravity LanguageServerService ConnectRPC bridge.
 *
 * Handles workspace/worktree project binding (`ReadProjects` + `CreateProject`),
 * live model & quota inspection (`GetCascadeModelConfigData` + `GetAvailableModels`),
 * trajectory discovery, clean-room Frontier conversation delegation, and cancellation.
 */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { uriToWorkspacePath } from "../core/fs-io.mjs";
import { DynamicModelCatalog } from "../models/inventory.mjs";

const LS_SERVICE_PREFIX = "/exa.language_server_pb.LanguageServerService/";

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
  }

  get baseUrl() {
    const raw = this.env.ANTIGRAVITY_LS_ADDRESS || "";
    if (!raw) return null;
    return raw.startsWith("http") ? raw.replace(/\/+$/, "") : `http://${raw.replace(/\/+$/, "")}`;
  }

  get csrfToken() {
    return this.env.ANTIGRAVITY_CSRF_TOKEN || "";
  }

  get available() {
    return Boolean(this.baseUrl);
  }

  /**
   * Call a LanguageServerService ConnectRPC method.
   *
   * @param {string} method
   * @param {Record<string, any>} [body]
   */
  async call(method, body = {}) {
    if (!this.baseUrl) {
      return { ok: false, error: "ANTIGRAVITY_LS_ADDRESS is not configured in this environment." };
    }
    const headers = {
      "Content-Type": "application/json",
      "Connect-Protocol-Version": "1",
      ...(this.csrfToken ? { "x-codeium-csrf-token": this.csrfToken } : {}),
    };
    try {
      const resp = await fetch(`${this.baseUrl}${LS_SERVICE_PREFIX}${method}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      const text = await resp.text();
      if (!resp.ok) {
        return { ok: false, status: resp.status, error: text.slice(0, 400) || `HTTP ${resp.status}` };
      }
      return { ok: true, value: text ? JSON.parse(text) : {} };
    } catch (err) {
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
        if (!prev.quota_remaining && entry.quota_remaining !== null) prev.quota_remaining = entry.quota_remaining;
        if (entry.deprecated) prev.deprecated = true;
        return;
      }
      modelsByEnum.set(entry.model, entry);
    };

    for (const c of Array.isArray(cfgPayload?.clientModelConfigs) ? cfgPayload.clientModelConfigs : []) {
      const mEnum = String(c?.modelOrAlias?.model || "").trim();
      if (!mEnum) continue;
      const frac = c?.quotaInfo?.remainingFraction;
      pushModel({
        id: c?.modelId || c?.modelOrAlias?.alias || mEnum,
        model_id: c?.modelId || c?.modelOrAlias?.alias || mEnum,
        model: mEnum,
        displayName: c?.label || mEnum,
        label: c?.label || mEnum,
        tag: c?.tagTitle || "",
        disabled: Boolean(c?.disabled),
        deprecated: deprecatedSet.has(String(c?.modelId || "")),
        quota_remaining: Number.isFinite(Number(frac)) ? Number(frac) : null,
      });
    }

    for (const [mId, info] of Object.entries(rawModels)) {
      if (!info || typeof info !== "object") continue;
      const mEnum = String(info.model || mId).trim();
      const frac = info?.quotaInfo?.remainingFraction;
      pushModel({
        id: mId,
        model_id: mId,
        model: mEnum,
        displayName: info.displayName || info.label || mId,
        label: info.displayName || info.label || mId,
        tag: info.tagTitle || "",
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
