/**
 * Multi-host runtime bridge for Flow Studio.
 *
 * Adapts API requests, agent prompt dispatch, file opening, and live events across:
 *   1. Google Antigravity Sidecar (`window.sidecar` + `/preload.js`)
 *   2. VS Code / Cursor Webview (`acquireVsCodeApi()`)
 *   3. Standalone Loopback Server (`npx flow-studio` HTTP + SSE)
 */
(function initFlowHostBridge() {
  const vscodeApi = typeof window.acquireVsCodeApi === "function" ? window.acquireVsCodeApi() : null;
  const isAntigravity = Boolean(window.sidecar && !window.__FLOW_STANDALONE__ && !vscodeApi);
  const hostKind = vscodeApi ? "vscode" : isAntigravity ? "antigravity" : "standalone";

  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get("token") || "";
  let reqSeq = 1;
  /** @type {Map<number, { resolve: Function, reject: Function }>} */
  const pendingVsCode = new Map();
  /** @type {Set<(evt: any) => void>} */
  const listeners = new Set();

  if (vscodeApi) {
    window.addEventListener("message", (event) => {
      const msg = event.data;
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "apiResponse" && pendingVsCode.has(msg.id)) {
        const entry = pendingVsCode.get(msg.id);
        pendingVsCode.delete(msg.id);
        if (msg.error) entry.reject(new Error(msg.error));
        else entry.resolve(msg.result);
        return;
      }
      if (msg.type === "studioEvent") {
        for (const fn of listeners) fn(msg.event);
      }
    });
  } else if (
    !isAntigravity &&
    urlParams.get("sse") !== "0" &&
    typeof window.EventSource === "function"
  ) {
    try {
      const es = new EventSource("/api/events");
      es.onmessage = (evt) => {
        try {
          const parsed = JSON.parse(evt.data);
          for (const fn of listeners) fn(parsed);
        } catch {
          // Ignore malformed SSE frames.
        }
      };
    } catch {
      // EventSource is optional in headless tests.
    }
  }

  if (isAntigravity && typeof window.sidecar?.onWorkspaceChange === "function") {
    window.sidecar.onWorkspaceChange((uris) => {
      for (const fn of listeners) fn({ type: "workspace.changed", uris });
    });
  }

  /**
   * Call a Studio backend JSON route.
   *
   * @param {string} routePath
   * @param {Record<string, any>} [payload]
   */
  async function api(routePath, payload = {}) {
    if (vscodeApi) {
      return new Promise((resolve, reject) => {
        const id = reqSeq++;
        pendingVsCode.set(id, { resolve, reject });
        vscodeApi.postMessage({ type: "apiRequest", id, routePath, payload });
      });
    }

    /** @type {Record<string, string>} */
    const headers = { "Content-Type": "application/json" };
    const sidecarToken = window.sidecar?.token || window.sidecar?.uiToken || urlToken;
    if (sidecarToken) {
      headers["X-Sidecar-Token"] = sidecarToken;
    }

    const resp = await fetch(routePath, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.error || `Request failed (${resp.status})`);
    }
    return data;
  }

  /**
   * Dispatch a Flow slash command or prompt to the active host or selected harness.
   *
   * @param {{
   *   workspacePath: string,
   *   message: string,
   *   title?: string,
   *   targetHarness?: string,
   *   executionMode?: string
   * }} options
   */
  async function dispatchPrompt(options) {
    const message = String(options.message || "").trim();
    if (!message) return { sent: false, reason: "Empty command" };

    if (options.targetHarness && options.targetHarness !== "host") {
      const run = await api("/api/harness-dispatch", {
        workspacePath: options.workspacePath,
        harness: options.targetHarness,
        executionMode: options.executionMode || "direct-workspace",
        prompt: message,
      });
      return { sent: true, mode: "cross-harness", run };
    }

    if (vscodeApi) {
      vscodeApi.postMessage({
        type: "dispatchPrompt",
        workspacePath: options.workspacePath,
        message,
        title: options.title || "Flow",
        executionMode: options.executionMode || "direct-workspace",
      });
      return { sent: true, mode: "vscode" };
    }

    if (isAntigravity) {
      if (window.sidecar?.conversationId && window.sidecar?.agent?.sendMessage && !options.startNew) {
        await window.sidecar.agent.sendMessage(message, window.sidecar.conversationId);
        return { sent: true, mode: "active-conversation" };
      }
      const res = await api("/api/start-workspace-conversation", {
        workspacePath: options.workspacePath,
        message,
        title: options.title || message.slice(0, 60),
      });
      if (res.workspace_bound && res.conversation_id) {
        if (typeof window.sidecar?.ui?.toggleConversation === "function") {
          window.sidecar.ui.toggleConversation(res.conversation_id);
        }
        return { sent: true, mode: "workspace-cascade", conversationId: res.conversation_id };
      }
      await copyText(message);
      return {
        sent: false,
        copied: true,
        reason: res.error || "Copied command to clipboard (LanguageServer workspace binding unavailable).",
      };
    }

    await copyText(message);
    return { sent: false, copied: true, mode: "clipboard" };
  }

  /**
   * Open a workspace file in the host editor or auxiliary pane.
   *
   * @param {string} workspacePath
   * @param {string} relPath
   * @param {number} [line]
   */
  function openFile(workspacePath, relPath, line = 1) {
    const normalizedWs = String(workspacePath || "").replace(/\/+$/, "");
    const absPath = `${normalizedWs}/${String(relPath || "").replace(/^\/+/, "")}`;
    if (vscodeApi) {
      vscodeApi.postMessage({ type: "openFile", absPath, relPath, line });
      return true;
    }
    if (isAntigravity && typeof window.sidecar?.ui?.toggleAuxPane === "function") {
      window.sidecar.ui.toggleAuxPane({
        tabType: "fileView",
        uri: `file://${absPath}`,
      });
      return true;
    }
    return false;
  }

  function openFullStudio() {
    if (isAntigravity && typeof window.sidecar?.ui?.toggleAuxPane === "function") {
      window.sidecar.ui.toggleAuxPane({
        tabType: "sidecarView",
        uri: "sidecar://flow/studio/dashboard",
      });
      return;
    }
    window.location.href = "/dashboard";
  }

  /**
   * @param {string} text
   */
  async function copyText(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    }
  }

  window.flowHost = {
    kind: hostKind,
    isCompanionView:
      window.location.pathname === "/" &&
      urlParams.get("view") !== "dashboard" &&
      hostKind === "antigravity",
    api,
    dispatchPrompt,
    openFile,
    openFullStudio,
    copyText,
    onEvent(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    getInitialWorkspaceUri() {
      if (isAntigravity && typeof window.sidecar?.getWorkspaceUris === "function") {
        const uris = window.sidecar.getWorkspaceUris();
        if (Array.isArray(uris) && uris.length > 0) return uris[0];
      }
      return null;
    },
  };
})();
