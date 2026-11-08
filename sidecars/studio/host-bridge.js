/**
 * Multi-host runtime bridge for Flow Studio.
 *
 * Adapts API requests, agent prompt dispatch, file opening, and live events across:
 *   1. Google Antigravity Sidecar (`window.sidecar` + `/preload.js`)
 *   2. VS Code / Cursor Webview (`acquireVsCodeApi()`)
 *   3. Standalone Loopback Server (`npx --yes --package github:cofin/flow flow-studio` HTTP + SSE)
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
  /** @type {string[]} */
  let activeWorkspaceUris =
    typeof window.__FLOW_INITIAL_WORKSPACE__ === "string" && window.__FLOW_INITIAL_WORKSPACE__.trim()
      ? [window.__FLOW_INITIAL_WORKSPACE__.trim()]
      : [];

  /**
   * Normalize a `file://` URI or filesystem path for comparison.
   *
   * @param {string | null | undefined} uriOrPath
   */
  function normalizeWorkspaceRef(uriOrPath) {
    const raw = String(uriOrPath || "").trim();
    if (!raw) return "";
    let cleaned = raw;
    if (cleaned.startsWith("file://")) {
      try {
        cleaned = decodeURIComponent(new URL(cleaned).pathname);
      } catch {
        cleaned = decodeURIComponent(cleaned.replace(/^file:\/\//i, ""));
      }
    }
    cleaned = cleaned
      .replace(/\\/g, "/")
      .replace(/^\/+([A-Za-z]:\/)/, "$1")
      .replace(/\/+$/, "");
    if (/^[A-Za-z]:\//.test(cleaned)) {
      cleaned = cleaned[0].toLowerCase() + cleaned.slice(1);
    }
    return cleaned;
  }

  /**
   * Return true if `workspacePath` matches one of the host's currently active workspace URIs.
   *
   * @param {string | null | undefined} workspacePath
   */
  function isWorkspaceMatchingActiveChat(workspacePath) {
    const target = normalizeWorkspaceRef(workspacePath);
    if (!target || activeWorkspaceUris.length === 0) return false;
    return activeWorkspaceUris.some((u) => {
      const candidate = normalizeWorkspaceRef(u);
      return Boolean(candidate) && (candidate === target || target.startsWith(`${candidate}/`));
    });
  }

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
        if (msg.event?.type === "workspace.changed") {
          if (Array.isArray(msg.event.uris) && msg.event.uris.length > 0) {
            activeWorkspaceUris = msg.event.uris.filter(Boolean).map(String);
          } else if (
            typeof msg.event.workspacePath === "string" &&
            msg.event.workspacePath.trim()
          ) {
            activeWorkspaceUris = [msg.event.workspacePath.trim()];
          }
        }
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
      if (Array.isArray(uris)) {
        activeWorkspaceUris = uris.filter(Boolean).map(String);
      }
      for (const fn of listeners) {
        fn({ type: "workspace.changed", uris: activeWorkspaceUris });
      }
    });
  }

  /**
   * Call a Studio backend JSON route.
   *
   * @param {string} routePath
   * @param {Record<string, any>} [payload]
   */
  async function api(routePath, payload = {}) {
    const enrichedPayload = { ...payload };
    const convId =
      enrichedPayload.conversationId ||
      window.sidecar?.conversationId ||
      urlParams.get("conversationId") ||
      "";
    if (convId && !enrichedPayload.conversationId) {
      enrichedPayload.conversationId = convId;
    }
    if (activeWorkspaceUris.length > 0 && !enrichedPayload.activeWorkspaceUris) {
      enrichedPayload.activeWorkspaceUris = activeWorkspaceUris;
    }

    if (vscodeApi) {
      return new Promise((resolve, reject) => {
        const id = reqSeq++;
        pendingVsCode.set(id, { resolve, reject });
        vscodeApi.postMessage({ type: "apiRequest", id, routePath, payload: enrichedPayload });
      });
    }

    /** @type {Record<string, string>} */
    const headers = { "Content-Type": "application/json" };
    const sidecarToken = window.sidecar?.token || window.sidecar?.uiToken || urlToken;
    if (sidecarToken) {
      headers["X-Sidecar-Token"] = sidecarToken;
    }

    const fetchFn =
      isAntigravity && typeof window.sidecar?.fetch === "function"
        ? window.sidecar.fetch.bind(window.sidecar)
        : fetch;

    const resp = await fetchFn(routePath, {
      method: "POST",
      headers,
      body: JSON.stringify(enrichedPayload),
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
   *   executionMode?: string,
   *   startNew?: boolean
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
      const matchesActiveChat =
        activeWorkspaceUris.length === 0 || isWorkspaceMatchingActiveChat(options.workspacePath);
      if (
        window.sidecar?.conversationId &&
        typeof window.sidecar?.agent?.sendMessage === "function" &&
        !options.startNew &&
        matchesActiveChat
      ) {
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
      if (
        window.sidecar?.conversationId &&
        typeof window.sidecar?.agent?.sendMessage === "function" &&
        matchesActiveChat
      ) {
        await window.sidecar.agent.sendMessage(message, window.sidecar.conversationId);
        return { sent: true, mode: "active-conversation" };
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

  /**
   * Open the full Studio dashboard view, preserving the selected workspace.
   *
   * @param {string} [workspacePath]
   */
  function openFullStudio(workspacePath) {
    const wsQuery =
      typeof workspacePath === "string" && workspacePath.trim()
        ? `?workspace=${encodeURIComponent(workspacePath.trim())}`
        : "";
    if (isAntigravity && typeof window.sidecar?.ui?.toggleAuxPane === "function") {
      window.sidecar.ui.toggleAuxPane({
        tabType: "sidecarView",
        uri: `sidecar://flow/studio/dashboard${wsQuery}`,
      });
      return;
    }
    window.location.href = `/dashboard${wsQuery}`;
  }

  /**
   * @param {string} text
   */
  async function copyText(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    }
  }

  /**
   * Resolve initial workspace URIs from URL parameters, Antigravity `window.sidecar.getWorkspaceUris()`,
   * or VS Code injected globals, using a bounded timeout so Sidebar views never hang before a chat opens.
   *
   * @param {number} [timeoutMs]
   * @returns {Promise<string[]>}
   */
  async function getInitialWorkspaceUris(timeoutMs = 450) {
    const explicitUri = urlParams.get("workspaceUri") || "";
    const explicitWs = urlParams.get("workspace") || "";
    if (explicitUri.trim()) {
      return [explicitUri.trim()];
    }
    if (explicitWs.trim()) {
      return [explicitWs.trim()];
    }
    if (isAntigravity && typeof window.sidecar?.getWorkspaceUris === "function") {
      try {
        const result = await Promise.race([
          Promise.resolve(window.sidecar.getWorkspaceUris()),
          new Promise((resolve) => setTimeout(() => resolve(null), timeoutMs)),
        ]);
        if (Array.isArray(result) && result.length > 0) {
          activeWorkspaceUris = result.filter(Boolean).map(String);
          return activeWorkspaceUris;
        }
      } catch {
        // Ignore host workspace lookup failure and fall back to backend context.
      }
    }
    if (activeWorkspaceUris.length > 0) {
      return activeWorkspaceUris;
    }
    return [];
  }

  /**
   * Resolve the primary initial workspace URI or path.
   *
   * @param {number} [timeoutMs]
   * @returns {Promise<string | null>}
   */
  async function getInitialWorkspaceUri(timeoutMs = 450) {
    const uris = await getInitialWorkspaceUris(timeoutMs);
    return uris.length > 0 ? uris[0] : null;
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
    getInitialWorkspaceUris,
    getInitialWorkspaceUri,
    getActiveWorkspaceUris() {
      return [...activeWorkspaceUris];
    },
    isWorkspaceMatchingActiveChat,
  };
})();
