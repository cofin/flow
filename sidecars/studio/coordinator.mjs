/**
 * Google Antigravity LanguageServerService ConnectRPC client for workspace-bound
 * conversation launch, model discovery, quota inspection, trajectory listing,
 * conversation forking, and worktree creation.
 */

import path from "node:path";
import { pathToFileURL } from "node:url";

import { uriToWorkspacePath } from "./snapshot.mjs";

const LS_SERVICE_PREFIX = "/exa.language_server_pb.LanguageServerService/";

export class AntigravityCoordinator {
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
   * Call a ConnectRPC method on Antigravity's LanguageServerService.
   *
   * @param {string} method
   * @param {Record<string, any>} body
   */
  async call(method, body = {}) {
    if (!this.baseUrl) {
      return { ok: false, error: "ANTIGRAVITY_LS_ADDRESS is not configured in this environment." };
    }
    const url = `${this.baseUrl}${LS_SERVICE_PREFIX}${method}`;
    /** @type {Record<string, string>} */
    const headers = {
      "Content-Type": "application/json",
      "Connect-Protocol-Version": "1",
    };
    if (this.csrfToken) {
      headers["x-codeium-csrf-token"] = this.csrfToken;
    }

    try {
      const resp = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
      });
      const text = await resp.text();
      if (!resp.ok) {
        return { ok: false, status: resp.status, error: text.slice(0, 400) || `HTTP ${resp.status}` };
      }
      const parsed = text ? JSON.parse(text) : {};
      return { ok: true, value: parsed };
    } catch (err) {
      return { ok: false, error: err instanceof Error ? err.message : String(err) };
    }
  }

  /**
   * Query available Antigravity models and optional quota summary.
   */
  async getModelsAndQuota() {
    if (!this.available) {
      return {
        connected: false,
        models: [],
        tieredModelIds: {},
        quota: null,
      };
    }
    const [modelsRes, quotaRes] = await Promise.all([
      this.call("GetAvailableModels", {}),
      this.call("RetrieveUserQuotaSummary", {}),
    ]);
    const rawModels = modelsRes.ok && modelsRes.value?.models ? modelsRes.value.models : {};
    const models = Object.entries(rawModels).map(([id, info]) => ({
      id,
      displayName: info?.displayName || info?.label || id,
      model: info?.model || id,
      disabled: Boolean(info?.disabled),
    }));
    return {
      connected: Boolean(modelsRes.ok),
      models,
      tieredModelIds: modelsRes.ok ? modelsRes.value?.tieredModelIds || {} : {},
      quota: quotaRes.ok ? quotaRes.value : null,
    };
  }

  /**
   * List recent Antigravity cascade trajectories optionally filtered by workspace URI.
   *
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
        ? item.workspaces.map((w) => w?.workspaceFolderAbsoluteUri || w).filter(Boolean)
        : [],
    }));
    const filtered = targetUri
      ? list.filter((t) => t.workspaceUris.length === 0 || t.workspaceUris.some((u) => String(u).startsWith(targetUri)))
      : list;
    return { connected: true, trajectories: filtered.slice(0, 25) };
  }

  /**
   * Discover the active conversation workspace and all open project/trajectory workspaces
   * from Antigravity's LanguageServerService.
   *
   * @param {{ conversationId?: string }} [options]
   */
  async discoverWorkspaces(options = {}) {
    if (!this.available) {
      return { activeWorkspace: null, workspaces: [] };
    }
    const conversationId = String(
      options.conversationId || this.env.ANTIGRAVITY_CONVERSATION_ID || ""
    ).trim();

    const [trajRes, listProjRes, getProjRes] = await Promise.all([
      this.call("GetAllCascadeTrajectories", {}),
      this.call("ListProjects", {}),
      this.call("GetProjects", {}),
    ]);

    /** @type {Set<string>} */
    const discovered = new Set();
    /** @type {string | null} */
    let activeWorkspace = null;

    if (trajRes.ok) {
      const rawMap = trajRes.value?.trajectorySummaries || trajRes.value?.trajectories || {};
      const entries = Object.entries(rawMap).map(([cascadeId, item]) => {
        const rawWs = Array.isArray(item?.workspaces)
          ? item.workspaces
              .map((w) =>
                uriToWorkspacePath(
                  w?.workspaceFolderAbsoluteUri || w?.workspaceFolderUri || w?.folderUri || w
                )
              )
              .filter(Boolean)
          : [];
        return {
          cascadeId,
          status: String(item?.status || ""),
          updatedAt: String(item?.lastModifiedTime || ""),
          workspaces: rawWs,
        };
      });

      if (conversationId) {
        const matched = entries.find(
          (e) => e.cascadeId === conversationId && e.workspaces.length > 0
        );
        if (matched) {
          activeWorkspace = matched.workspaces[0];
        }
      }

      const sorted = entries
        .filter((e) => e.workspaces.length > 0)
        .sort((a, b) => {
          const aRun = a.status.includes("RUNNING") ? 1 : 0;
          const bRun = b.status.includes("RUNNING") ? 1 : 0;
          if (aRun !== bRun) return bRun - aRun;
          return b.updatedAt.localeCompare(a.updatedAt);
        });

      if (!activeWorkspace && sorted.length > 0) {
        activeWorkspace = sorted[0].workspaces[0];
      }
      for (const entry of sorted) {
        for (const ws of entry.workspaces) {
          if (ws) discovered.add(ws);
        }
      }
    }

    const projectObjects = [];
    if (getProjRes.ok && Array.isArray(getProjRes.value?.projects)) {
      projectObjects.push(...getProjRes.value.projects);
    }
    if (
      listProjRes.ok &&
      Array.isArray(listProjRes.value?.ids) &&
      listProjRes.value.ids.length > 0
    ) {
      const readRes = await this.call("ReadProjects", { ids: listProjRes.value.ids });
      if (readRes.ok && Array.isArray(readRes.value?.projects)) {
        projectObjects.push(...readRes.value.projects);
      }
    }

    for (const proj of projectObjects) {
      for (const uri of extractProjectFolderUris(proj)) {
        const resolved = uriToWorkspacePath(uri);
        if (resolved) {
          if (!activeWorkspace) activeWorkspace = resolved;
          discovered.add(resolved);
        }
      }
    }

    return {
      activeWorkspace,
      workspaces: Array.from(discovered),
    };
  }

  /**
   * Start a new conversation explicitly bound to `workspacePath` and send `message`.
   *
   * @param {{ workspacePath: string, message: string, title?: string, preferredModel?: string }} params
   */
  async startWorkspaceConversation(params) {
    const workspace = path.resolve(params.workspacePath);
    const message = String(params.message || "").trim();
    if (!message) {
      throw new Error("Conversation message cannot be empty.");
    }
    if (!this.available) {
      return {
        conversation_id: null,
        workspace_bound: false,
        workspace,
        prompt_sent: false,
        error: "Antigravity LanguageServer ConnectRPC is not reachable outside an Antigravity host.",
      };
    }

    const fileUri = pathToFileURL(workspace).href;
    let matchedProjectId = null;
    const [projectsRes, listProjRes] = await Promise.all([
      this.call("GetProjects", {}),
      this.call("ListProjects", {}),
    ]);
    const candidates = [];
    if (projectsRes.ok && Array.isArray(projectsRes.value?.projects)) {
      candidates.push(...projectsRes.value.projects);
    }
    if (
      listProjRes.ok &&
      Array.isArray(listProjRes.value?.ids) &&
      listProjRes.value.ids.length > 0
    ) {
      const readRes = await this.call("ReadProjects", { ids: listProjRes.value.ids });
      if (readRes.ok && Array.isArray(readRes.value?.projects)) {
        candidates.push(...readRes.value.projects);
      }
    }
    for (const proj of candidates) {
      if (!proj?.id) continue;
      const uris = extractProjectFolderUris(proj);
      if (uris.some((u) => u === fileUri || uriToWorkspacePath(u) === workspace)) {
        matchedProjectId = proj.id;
        break;
      }
    }

    let planModel = params.preferredModel || null;
    if (!planModel) {
      const modelsRes = await this.call("GetAvailableModels", {});
      if (modelsRes.ok && modelsRes.value?.models) {
        const tiered = modelsRes.value.tieredModelIds || {};
        const candidates = [
          ...(Array.isArray(tiered.pro) ? tiered.pro : []),
          ...(Array.isArray(tiered.flash) ? tiered.flash : []),
        ];
        for (const mId of candidates) {
          const info = modelsRes.value.models[mId];
          if (info && !info.disabled && info.model) {
            planModel = info.model;
            break;
          }
        }
      }
    }

    const cascadePayload = {
      source: "CORTEX_TRAJECTORY_SOURCE_AGENT_API",
      trajectoryType: "CORTEX_TRAJECTORY_TYPE_CASCADE",
      customAgentSpec: {
        codingAgent: { googleMode: true },
        commandExecutionPolicy: "sandbox",
        enforcedWorkspaceValidation: false,
        ...(planModel ? { cascadeConfig: { plannerConfig: { planModel } } } : {}),
      },
      ...(matchedProjectId
        ? { projectEnvConfig: { projectId: matchedProjectId, defaultProjectEnvironment: {} } }
        : { workspaceUris: [fileUri] }),
    };

    const startRes = await this.call("StartCascade", cascadePayload);
    if (!startRes.ok || !startRes.value?.cascadeId) {
      return {
        conversation_id: null,
        workspace_bound: false,
        project_id: matchedProjectId,
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
    });

    return {
      conversation_id: cascadeId,
      workspace_bound: true,
      project_id: matchedProjectId,
      workspace,
      prompt_sent: Boolean(sendRes.ok),
    };
  }

  /**
   * Fork an existing Antigravity conversation trajectory.
   *
   * @param {string} cascadeId
   */
  async forkConversation(cascadeId) {
    return this.call("ForkConversation", { cascadeId });
  }

  /**
   * Stop an active cascade tree.
   *
   * @param {string} cascadeId
   */
  async stopConversation(cascadeId) {
    return this.call("ForceStopCascadeTree", { cascadeId });
  }
}

/**
 * Extract all folder URIs from an Antigravity project object (`GetProjects` or `ReadProjects`).
 *
 * @param {any} proj
 * @returns {string[]}
 */
function extractProjectFolderUris(proj) {
  if (!proj || typeof proj !== "object") return [];
  /** @type {string[]} */
  const uris = [];
  if (Array.isArray(proj.workspaceUris)) {
    for (const u of proj.workspaceUris) {
      if (typeof u === "string" && u.trim()) uris.push(u.trim());
    }
  }
  const resources = proj.projectResources?.resources;
  if (Array.isArray(resources)) {
    for (const r of resources) {
      if (typeof r?.folderUri === "string" && r.folderUri.trim()) {
        uris.push(r.folderUri.trim());
      }
    }
  }
  if (typeof proj.gitFolder?.folderUri === "string" && proj.gitFolder.folderUri.trim()) {
    uris.push(proj.gitFolder.folderUri.trim());
  }
  return uris;
}
