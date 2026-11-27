/**
 * Multi-host runtime bridge for Flow Studio.
 *
 * Adapts API requests, agent prompt dispatch, context attachment, file opening, and live events across:
 *   1. VS Code / Cursor Webview (`acquireVsCodeApi()`)
 *   2. Google Antigravity MCP App (`window.__FLOW_MCP_APP__` + `@modelcontextprotocol/ext-apps`)
 *   3. Google Antigravity Sidecar (`window.sidecar` + `/preload.js`, Desktop App & Antigravity Web Hub)
 *   4. Standalone Loopback Server (`npx --yes --package github:cofin/flow flow-studio` HTTP + SSE)
 */
(function initFlowHostBridge() {
  const vscodeApi = typeof window.acquireVsCodeApi === "function" ? window.acquireVsCodeApi() : null;
  const mcpSdk = window.__FLOW_MCP_APP__ && window.__MCP_EXT_APPS__ ? window.__MCP_EXT_APPS__ : null;
  const isMcpApp = Boolean(mcpSdk && !vscodeApi && !window.__FLOW_STANDALONE__);
  const isSidecar = Boolean(window.sidecar && !vscodeApi && !isMcpApp && !window.__FLOW_STANDALONE__);
  const hostKind = vscodeApi ? "vscode" : isMcpApp ? "mcp-app" : isSidecar ? "antigravity" : "standalone";

  const READ_API_ROUTES = new Set([
    "/api/studio-context",
    "/api/bundle-snapshot",
    "/api/portfolio-snapshot",
    "/api/spec-document",
    "/api/spec-dag",
    "/api/spec-review",
    "/api/review-comments",
    "/api/spec-branches",
    "/api/remote-repo-specs",
    "/api/catalog-search",
    "/api/catalog-provenance",
    "/api/catalog-entry",
    "/api/catalog-drift",
    "/api/catalog-status",
    "/api/models-and-quota",
    "/api/review-plan",
    "/api/trajectories",
    "/api/activity",
    "/api/permissions",
    "/api/harnesses",
    "/api/harness-runs",
  ]);

  const urlParams = new URLSearchParams(window.location.search);
  const urlToken = urlParams.get("token") || "";
  let reqSeq = 1;
  /** @type {Map<number, { resolve: Function, reject: Function }>} */
  const pendingVsCode = new Map();
  /** @type {Set<(evt: any) => void>} */
  const listeners = new Set();
  /** @type {Set<(payload: any) => void>} */
  const toolResultListeners = new Set();
  /** @type {any} */
  let lastToolResult = null;
  /** @type {string[]} */
  let activeWorkspaceUris =
    typeof window.__FLOW_INITIAL_WORKSPACE__ === "string" && window.__FLOW_INITIAL_WORKSPACE__.trim()
      ? [window.__FLOW_INITIAL_WORKSPACE__.trim()]
      : [];

  const capabilities = {
    canSendMessage: Boolean(vscodeApi || isSidecar),
    canUpdateContext: false,
    canOpenFile: Boolean(vscodeApi || (isSidecar && typeof window.sidecar?.ui?.toggleAuxPane === "function")),
    canOpenExternal: !vscodeApi,
  };

  /** @type {any} */
  let mcpApp = null;
  /** @type {Promise<void>} */
  let mcpReadyPromise = Promise.resolve();
  const MAX_INFLIGHT_MCP_CALLS = 3;
  let inflightMcpCalls = 0;
  /** @type {Array<() => void>} */
  const mcpCallQueue = [];

  function runWithMcpSlot(fn) {
    return new Promise((resolve, reject) => {
      const execute = async () => {
        inflightMcpCalls += 1;
        try {
          resolve(await fn());
        } catch (err) {
          reject(err);
        } finally {
          inflightMcpCalls -= 1;
          const next = mcpCallQueue.shift();
          if (next) next();
        }
      };
      if (inflightMcpCalls < MAX_INFLIGHT_MCP_CALLS) {
        void execute();
      } else {
        mcpCallQueue.push(() => void execute());
      }
    });
  }

  function applyMcpHostContext(ctx) {
    if (!ctx || !mcpSdk) return;
    if (ctx.theme && typeof mcpSdk.applyDocumentTheme === "function") {
      mcpSdk.applyDocumentTheme(ctx.theme);
      document.documentElement.setAttribute("data-theme", ctx.theme === "dark" ? "dark" : "light");
    }
    if (ctx.styles?.variables && typeof mcpSdk.applyHostStyleVariables === "function") {
      mcpSdk.applyHostStyleVariables(ctx.styles.variables);
    }
  }

  if (isMcpApp) {
    mcpApp = new mcpSdk.App({ name: "Flow Studio", version: "0.34.0" }, {});
    mcpApp.ontoolinput = () => {};
    mcpApp.ontoolresult = (result) => {
      const payload = result?.structuredContent ?? null;
      lastToolResult = payload;
      if (payload?.workspace) {
        activeWorkspaceUris = [String(payload.workspace)];
      }
      for (const fn of toolResultListeners) {
        try {
          fn(payload);
        } catch {
          // Ignore listener failure.
        }
      }
    };
    mcpApp.onhostcontextchanged = (ctx) => {
      applyMcpHostContext(ctx);
      for (const fn of listeners) fn({ type: "theme.changed", context: ctx });
    };

    mcpReadyPromise = (async () => {
      try {
        await mcpApp.connect();
        const hostCaps = (typeof mcpApp.getHostCapabilities === "function" ? mcpApp.getHostCapabilities() : {}) || {};
        capabilities.canSendMessage = Boolean(hostCaps.message);
        capabilities.canUpdateContext = Boolean(hostCaps.updateModelContext);
        capabilities.canOpenFile = true;
        capabilities.canOpenExternal = Boolean(hostCaps.openLinks);
        applyMcpHostContext(typeof mcpApp.getHostContext === "function" ? mcpApp.getHostContext() : null);
      } catch {
        // Keep defaults if host connect fails in headless test harnesses.
      }
    })();
  }

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

  function isReadApiRequest(routePath, payload) {
    if (!READ_API_ROUTES.has(routePath)) return false;
    if (routePath === "/api/review-comments") {
      const action = String(payload?.action || "list").toLowerCase();
      return action === "list";
    }
    return true;
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
    !isMcpApp &&
    !isSidecar &&
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

  if (isSidecar && typeof window.sidecar?.onWorkspaceChange === "function") {
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

    if (isMcpApp && mcpApp) {
      await mcpReadyPromise;
      return runWithMcpSlot(async () => {
        const res = await mcpApp.callServerTool({
          name: "flow_studio_api",
          arguments: { route: routePath, payload: enrichedPayload },
        });
        if (res?.isError) {
          const errText =
            Array.isArray(res.content) && res.content[0]?.text
              ? res.content[0].text
              : `MCP tool call failed (${routePath})`;
          throw new Error(errText);
        }
        if (res && res.structuredContent !== undefined) {
          return res.structuredContent;
        }
        const rawText = Array.isArray(res?.content) ? res.content.find((c) => c?.text)?.text : "";
        if (rawText) {
          try {
            return JSON.parse(rawText);
          } catch {
            return { text: rawText };
          }
        }
        return {};
      });
    }

    if (isSidecar) {
      if (isReadApiRequest(routePath, enrichedPayload)) {
        const serialized = JSON.stringify(enrichedPayload);
        const encoded = encodeURIComponent(serialized);
        const getUrl = `${routePath}?payload=${encoded}`;
        if (getUrl.length < 7500) {
          const resp = await fetch(getUrl, { method: "GET" });
          const data = await resp.json().catch(() => ({}));
          if (!resp.ok) {
            throw new Error(data.error || `Request failed (${resp.status})`);
          }
          return data;
        }
      }

      /** @type {Record<string, string>} */
      const headers = { "Content-Type": "application/json" };
      const sidecarToken = window.sidecar?.token || window.sidecar?.uiToken || urlToken;
      if (sidecarToken) {
        headers["X-Sidecar-Token"] = sidecarToken;
      }
      const fetchFn =
        typeof window.sidecar?.fetch === "function" ? window.sidecar.fetch.bind(window.sidecar) : fetch;
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

    const resp = await fetch(routePath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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

    if (isMcpApp && mcpApp) {
      await mcpReadyPromise;
      if (capabilities.canSendMessage && typeof mcpApp.sendMessage === "function") {
        const meta = options.startNew
          ? { "com.google.antigravity/message": { target: "new" } }
          : undefined;
        await mcpApp.sendMessage({
          role: "user",
          content: [{ type: "text", text: message }],
          ...(meta ? { _meta: meta } : {}),
        });
        return { sent: true, mode: options.startNew ? "new-conversation" : "mcp-message" };
      }
      const res = await api("/api/start-workspace-conversation", {
        workspacePath: options.workspacePath,
        message,
        title: options.title || message.slice(0, 60),
      }).catch(() => ({ workspace_bound: false }));
      if (res?.workspace_bound && res?.conversation_id) {
        return { sent: true, mode: "workspace-cascade", conversationId: res.conversation_id };
      }
      await copyText(message);
      return {
        sent: false,
        copied: true,
        reason: "Copied command to clipboard (open Flow Studio in a conversation side panel to send directly).",
      };
    }

    if (isSidecar) {
      const matchesActiveChat =
        activeWorkspaceUris.length === 0 || isWorkspaceMatchingActiveChat(options.workspacePath);
      if (
        window.sidecar?.conversationId &&
        typeof window.sidecar?.agent?.sendMessage === "function" &&
        !options.startNew &&
        matchesActiveChat
      ) {
        try {
          await window.sidecar.agent.sendMessage(message, window.sidecar.conversationId);
          return { sent: true, mode: "active-conversation" };
        } catch {
          // Fall through to workspace conversation / clipboard fallback if token auth is unavailable.
        }
      }
      const res = await api("/api/start-workspace-conversation", {
        workspacePath: options.workspacePath,
        message,
        title: options.title || message.slice(0, 60),
      }).catch(() => ({ workspace_bound: false }));
      if (res?.workspace_bound && res?.conversation_id) {
        if (typeof window.sidecar?.ui?.toggleConversation === "function") {
          window.sidecar.ui.toggleConversation(res.conversation_id);
        }
        return { sent: true, mode: "workspace-cascade", conversationId: res.conversation_id };
      }
      await copyText(message);
      return {
        sent: false,
        copied: true,
        reason: res?.error || "Copied command to clipboard.",
      };
    }

    await copyText(message);
    return { sent: false, copied: true, mode: "clipboard" };
  }

  /**
   * Attach text context to the user's next message when supported by the MCP App host.
   *
   * @param {string} text
   */
  async function attachContext(text) {
    const clean = String(text || "").trim();
    if (!clean) return { attached: false };
    if (isMcpApp && mcpApp) {
      await mcpReadyPromise;
      if (capabilities.canUpdateContext && typeof mcpApp.updateModelContext === "function") {
        await mcpApp.updateModelContext({ content: [{ type: "text", text: clean }] });
        return { attached: true };
      }
    }
    await copyText(clean);
    return { attached: false, copied: true };
  }

  /**
   * Open a workspace file in the host editor or auxiliary pane.
   *
   * @param {string} workspacePath
   * @param {string} relPath
   * @param {number} [line]
   */
  async function openFile(workspacePath, relPath, line = 1) {
    const normalizedWs = String(workspacePath || "").replace(/\/+$/, "");
    const absPath = `${normalizedWs}/${String(relPath || "").replace(/^\/+/, "")}`;
    if (vscodeApi) {
      vscodeApi.postMessage({ type: "openFile", absPath, relPath, line });
      return true;
    }
    if (isMcpApp && mcpApp && typeof mcpSdk?.toggleAuxPaneFile === "function") {
      await mcpReadyPromise;
      try {
        const res = await mcpSdk.toggleAuxPaneFile(mcpApp, `file://${absPath}`);
        return !res?.isError;
      } catch {
        return false;
      }
    }
    if (isSidecar && typeof window.sidecar?.ui?.toggleAuxPane === "function") {
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
    if (isMcpApp) {
      return;
    }
    if (isSidecar && typeof window.sidecar?.ui?.toggleAuxPane === "function") {
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
   * Notify host (VS Code webview) that the Studio UI is mounted and ready for queued navigation messages.
   */
  function signalReady() {
    if (vscodeApi) {
      vscodeApi.postMessage({ type: "ready" });
    }
  }

  /**
   * Resolve initial workspace URIs from URL parameters, Antigravity sidecar, MCP App tool result,
   * or VS Code globals, using a bounded timeout so Sidebar views never hang before a chat opens.
   *
   * @param {number} [timeoutMs]
   * @returns {Promise<string[]>}
   */
  async function getInitialWorkspaceUris(timeoutMs = 350) {
    if (isMcpApp) {
      await mcpReadyPromise;
    }
    const explicitUri = urlParams.get("workspaceUri") || "";
    const explicitWs = urlParams.get("workspace") || "";
    if (explicitUri.trim()) {
      return [explicitUri.trim()];
    }
    if (explicitWs.trim()) {
      return [explicitWs.trim()];
    }
    if (isSidecar && typeof window.sidecar?.getWorkspaceUris === "function") {
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
  async function getInitialWorkspaceUri(timeoutMs = 350) {
    const uris = await getInitialWorkspaceUris(timeoutMs);
    return uris.length > 0 ? uris[0] : null;
  }

  window.flowHost = {
    kind: hostKind,
    isCompanionView:
      window.location.pathname === "/" &&
      urlParams.get("view") !== "dashboard" &&
      hostKind === "antigravity",
    capabilities,
    api,
    dispatchPrompt,
    attachContext,
    openFile,
    openFullStudio,
    openStudioPanel: openFullStudio,
    copyText,
    signalReady,
    onEvent(fn) {
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    onToolResult(fn) {
      toolResultListeners.add(fn);
      if (lastToolResult) {
        queueMicrotask(() => fn(lastToolResult));
      }
      return () => toolResultListeners.delete(fn);
    },
    getInitialWorkspaceUris,
    getInitialWorkspaceUri,
    getActiveWorkspaceUris() {
      return [...activeWorkspaceUris];
    },
    isWorkspaceMatchingActiveChat,
  };
})();
