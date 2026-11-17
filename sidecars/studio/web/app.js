/**
 * Flow Studio frontend (`Studio Home`, `Roadmap`, `Spec & Review` + DAG,
 * `Knowledge Catalog`, `Activity & Hooks` + Dynamic Models & Permissions).
 *
 * Uses safe DOM node creation (`createElement`, `createElementNS`, `textContent`).
 */
(function initFlowStudioApp() {
  const host = window.flowHost;
  const rootEl = document.getElementById("studio-root");
  const drawerEl = document.getElementById("new-spec-drawer");
  const attentionDrawerEl = document.getElementById("attention-drawer");
  const backdropEl = document.getElementById("drawer-backdrop");
  const toastRegion = document.getElementById("toast-region");

  const urlParams = new URLSearchParams(window.location.search);
  const forcedTheme = urlParams.get("theme");
  if (forcedTheme === "light" || forcedTheme === "dark") {
    document.documentElement.setAttribute("data-theme", forcedTheme);
  }

  function detectCssColorLuminance(cssColor) {
    const raw = String(cssColor || "").trim();
    if (!raw) return null;
    const probe = document.createElement("span");
    probe.style.color = raw;
    probe.style.display = "none";
    document.documentElement.appendChild(probe);
    const resolved = getComputedStyle(probe).color;
    probe.remove();
    const m = resolved.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
    if (!m) return null;
    return (0.2126 * Number(m[1]) + 0.7152 * Number(m[2]) + 0.0722 * Number(m[3])) / 255;
  }

  function syncHostTheme() {
    if (forcedTheme === "light" || forcedTheme === "dark") {
      document.documentElement.setAttribute("data-theme", forcedTheme);
      return;
    }
    const bodyClasses = document.body?.classList;
    if (bodyClasses) {
      if (bodyClasses.contains("vscode-dark") || bodyClasses.contains("vscode-high-contrast")) {
        document.documentElement.setAttribute("data-theme", "dark");
        return;
      }
      if (bodyClasses.contains("vscode-light") || bodyClasses.contains("vscode-high-contrast-light")) {
        document.documentElement.setAttribute("data-theme", "light");
        return;
      }
    }
    const hostBg =
      getComputedStyle(document.documentElement).getPropertyValue("--background").trim() ||
      getComputedStyle(document.documentElement).getPropertyValue("--flow-bg").trim();
    const lum = detectCssColorLuminance(hostBg);
    if (lum !== null) {
      document.documentElement.setAttribute("data-theme", lum < 0.45 ? "dark" : "light");
    }
  }

  syncHostTheme();
  window.addEventListener("message", (event) => {
    if (event.data?.type === "theme-change") queueMicrotask(syncHostTheme);
  });
  if (typeof MutationObserver === "function" && document.body) {
    new MutationObserver(syncHostTheme).observe(document.body, {
      attributes: true,
      attributeFilter: ["class", "data-vscode-theme-kind"],
    });
  }

  const state = {
    tab: urlParams.get("tab") || "roadmap",
    specSubView: "document",
    workspacePath: "",
    workspaces: [],
    pinnedWorkspaces: [],
    activeWorkspacePaths: [],
    snapshot: null,
    lastSnapshotEtag: null,
    portfolio: null,
    selectedDocRelPath: null,
    currentDoc: null,
    specDag: null,
    specReviewSummary: null,
    activeCommentLine: null,
    activeCommentKind: "feedback",
    revisePrompt: "",
    catalogQuery: "",
    catalogMode: "hybrid",
    catalogHits: [],
    catalogStatus: null,
    driftReport: null,
    harnesses: [],
    writerGuard: null,
    harnessRuns: [],
    selectedHarness: "host",
    executionMode: "direct-workspace",
    modelsQuota: null,
    activitySnapshot: null,
    permissionsReport: null,
    shellMounted: false,
    slots: { topbar: null, tabs: null, main: null },
  };

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "className") node.className = v;
      else if (k.startsWith("on") && typeof v === "function") {
        node.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (v === true) {
        node.setAttribute(k, "");
      } else {
        node.setAttribute(k, String(v));
      }
    }
    for (const child of children) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
    return node;
  }

  function svgEl(tag, attrs = {}, ...children) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v === null || v === undefined || v === false) continue;
      node.setAttribute(k, String(v));
    }
    for (const child of children) {
      if (child === null || child === undefined) continue;
      node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
    }
    return node;
  }

  function showToast(message) {
    if (!toastRegion) return;
    const item = el("div", { className: "toast" }, message);
    toastRegion.appendChild(item);
    setTimeout(() => item.remove(), 4200);
  }

  function closeDrawers() {
    backdropEl?.classList.add("hidden");
    drawerEl?.classList.add("hidden");
    attentionDrawerEl?.classList.add("hidden");
  }

  function buildContextRequestPayload(urisOrPaths = []) {
    const payload = {};
    const primary = urisOrPaths[0] || "";
    if (primary) {
      if (String(primary).startsWith("file:")) payload.workspaceUri = primary;
      else payload.workspacePath = primary;
    }
    if (urisOrPaths.length > 0) payload.activeWorkspaceUris = urisOrPaths;
    return payload;
  }

  function activeSpecFlowId() {
    if (state.currentDoc?.flowId) return state.currentDoc.flowId;
    if (state.selectedDocRelPath) {
      const m = String(state.selectedDocRelPath).match(/specs\/([^/]+)/);
      if (m) return m[1];
    }
    return state.snapshot?.activeFlowId || state.snapshot?.specs?.[0]?.flowId || null;
  }

  async function bootstrap() {
    try {
      const initialUris =
        typeof host.getInitialWorkspaceUris === "function"
          ? await host.getInitialWorkspaceUris()
          : [await host.getInitialWorkspaceUri()].filter(Boolean);
      const ctx = await host.api("/api/studio-context", buildContextRequestPayload(initialUris));
      state.workspacePath = ctx.defaultWorkspace;
      state.workspaces = ctx.workspaces || [ctx.defaultWorkspace];
      state.pinnedWorkspaces = ctx.pinnedWorkspaces || [];
      state.activeWorkspacePaths = ctx.activeWorkspaces || [ctx.defaultWorkspace];
      state.harnesses = ctx.harnesses || [];
      await refreshSnapshot({ force: true });
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to load Studio context");
      render();
    }
  }

  async function refreshSnapshot(options = {}) {
    if (!state.workspacePath) return;
    const snap = await host.api("/api/bundle-snapshot", {
      workspacePath: state.workspacePath,
      registerWorkspace: true,
    });
    const etagChanged = snap.contentEtag && snap.contentEtag !== state.lastSnapshotEtag;
    state.snapshot = snap;
    state.lastSnapshotEtag = snap.contentEtag || null;
    if (state.workspacePath && !state.workspaces.includes(state.workspacePath)) {
      state.workspaces = [state.workspacePath, ...state.workspaces];
    }
    if (!state.selectedDocRelPath && snap.specs.length > 0) {
      state.selectedDocRelPath = snap.specs[0].relPath;
    }
    if (options.force || etagChanged) {
      if (state.tab === "home") await refreshPortfolio();
      else if (state.tab === "review" && state.selectedDocRelPath) await loadDocument(state.selectedDocRelPath);
      else if (state.tab === "catalog") await refreshCatalog();
      else if (state.tab === "activity") await refreshActivity();
      try {
        state.activitySnapshot = await host.api("/api/activity", { workspacePath: state.workspacePath });
      } catch {
        // Non-fatal background activity check.
      }
      render();
    }
  }

  async function refreshPortfolio() {
    try {
      state.portfolio = await host.api("/api/portfolio-snapshot", {});
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to load workspace portfolio");
    }
  }

  async function loadDocument(relPath) {
    state.selectedDocRelPath = relPath;
    state.currentDoc = await host.api("/api/spec-document", {
      workspacePath: state.workspacePath,
      relPath,
    });
    const flowId = activeSpecFlowId();
    const [commentRes, dagRes, reviewRes] = await Promise.all([
      host.api("/api/review-comments", {
        action: "list",
        workspacePath: state.workspacePath,
        relPath,
        flowId,
      }),
      flowId
        ? host.api("/api/spec-dag", { workspacePath: state.workspacePath, flowId }).catch(() => null)
        : Promise.resolve(null),
      flowId
        ? host.api("/api/spec-review", { workspacePath: state.workspacePath, flowId }).catch(() => null)
        : Promise.resolve(null),
    ]);
    state.revisePrompt = commentRes.revisePrompt || "";
    state.specDag = dagRes;
    state.specReviewSummary = reviewRes;
  }

  async function refreshCatalog() {
    const statusRes = await host.api("/api/catalog-status", { workspacePath: state.workspacePath });
    state.catalogStatus = statusRes.status;
    if (state.catalogQuery.trim()) {
      const res = await host.api("/api/catalog-search", {
        workspacePath: state.workspacePath,
        query: state.catalogQuery,
        mode: state.catalogMode,
        planes: state.catalogMode === "federated" ? ["local", "siblings"] : undefined,
      });
      state.catalogHits = res.hits || [];
      state.catalogStatus = res.status || state.catalogStatus;
    } else {
      state.catalogHits = (state.snapshot?.knowledge || []).map((k) => ({
        entry_id: k.entryId,
        concept_id: k.conceptId,
        concept_type: k.type,
        title: k.title,
        description: k.description,
        trust_tier: k.status === "stable" ? "verified" : "draft",
        truth_block: k.truthBlock,
        rel_path: k.relPath,
      }));
    }
  }

  async function refreshActivity() {
    const [hRes, mRes, aRes, pRes] = await Promise.all([
      host.api("/api/harnesses", { workspacePath: state.workspacePath }),
      host.api("/api/models-and-quota", { workspacePath: state.workspacePath }),
      host.api("/api/activity", { workspacePath: state.workspacePath }),
      host.api("/api/permissions", { workspacePath: state.workspacePath }),
    ]);
    state.harnesses = hRes.harnesses || [];
    state.writerGuard = hRes.writerGuard || null;
    state.harnessRuns = hRes.runs || [];
    state.modelsQuota = mRes;
    state.activitySnapshot = aRes;
    state.permissionsReport = pRes;
  }

  async function runFlowAction(commandText, title = "Flow Action") {
    const res = await host.dispatchPrompt({
      workspacePath: state.workspacePath,
      message: commandText,
      title,
      targetHarness: state.selectedHarness,
      executionMode: state.executionMode,
    });
    if (res.sent) {
      showToast(`Dispatched (${res.mode}): ${commandText}`);
      if (res.mode === "cross-harness") {
        state.tab = "activity";
        await refreshActivity();
        render();
      }
    } else if (res.copied) {
      showToast(res.reason || `Copied to clipboard: ${commandText}`);
    }
  }

  function ensureShellMounted() {
    if (!rootEl) return;
    if (host.isCompanionView) {
      state.shellMounted = false;
      return;
    }
    if (!state.shellMounted || !rootEl.querySelector("#slot-main")) {
      rootEl.textContent = "";
      rootEl.className = "studio-shell";
      state.slots.topbar = el("div", { id: "slot-topbar", className: "slot-host" });
      state.slots.tabs = el("div", { id: "slot-tabs", className: "slot-host" });
      state.slots.main = el("div", { id: "slot-main", className: "slot-host" });
      rootEl.append(state.slots.topbar, state.slots.tabs, state.slots.main);
      state.shellMounted = true;
    }
  }

  function render() {
    if (!rootEl) return;
    if (host.isCompanionView) {
      state.shellMounted = false;
      rootEl.textContent = "";
      rootEl.className = "studio-shell companion-mode";
      rootEl.appendChild(renderCompanionView());
      return;
    }

    ensureShellMounted();
    const activeFocusId = document.activeElement?.id || null;
    state.slots.topbar.textContent = "";
    state.slots.topbar.appendChild(renderTopBar());
    state.slots.tabs.textContent = "";
    state.slots.tabs.appendChild(renderTabsBar());
    state.slots.main.textContent = "";

    if (state.tab === "home") state.slots.main.appendChild(renderHomeView());
    else if (state.tab === "roadmap") state.slots.main.appendChild(renderRoadmapView());
    else if (state.tab === "review") state.slots.main.appendChild(renderSpecReviewView());
    else if (state.tab === "catalog") state.slots.main.appendChild(renderCatalogView());
    else if (state.tab === "activity") state.slots.main.appendChild(renderActivityView());

    if (activeFocusId) {
      const target = document.getElementById(activeFocusId);
      if (target && typeof target.focus === "function") target.focus();
    }
  }

  function buildWorkspaceSelectElement() {
    const activeSet = new Set(state.activeWorkspacePaths || []);
    return el(
      "select",
      {
        className: "select-input",
        "aria-label": "Active workspace",
        onChange: async (e) => {
          state.workspacePath = e.target.value;
          state.selectedDocRelPath = null;
          state.currentDoc = null;
          state.specDag = null;
          await refreshSnapshot({ force: true });
        },
      },
      ...state.workspaces.map((ws) => {
        const base = ws.split("/").pop() || ws;
        const label = activeSet.has(ws) ? `${base} (active)` : base;
        return el("option", { value: ws, selected: ws === state.workspacePath }, label);
      })
    );
  }

  function renderTopBar() {
    const snap = state.snapshot;
    const wsSelect = buildWorkspaceSelectElement();
    const attention = state.activitySnapshot?.attention || [];

    const pyBadge = snap?.python
      ? el(
          "span",
          { className: "pill", title: `Runner: ${snap.python.runPrefix.join(" ")}` },
          `${snap.python.manager}${snap.python.entrypoints.length ? ` · ${snap.python.entrypoints.length} cli` : ""}`
        )
      : null;

    const attentionBtn =
      attention.length > 0
        ? el(
            "button",
            {
              className: "attention-pill",
              title: "Open agent & spec attention queue",
              onClick: () => openAttentionDrawer(),
            },
            `${attention.length} need${attention.length === 1 ? "s" : ""} you`
          )
        : null;

    const isPinned = (state.pinnedWorkspaces || []).includes(state.workspacePath);
    const logoSrc = window.__FLOW_LOGO_URI__ || "/logo.svg";

    return el(
      "header",
      { className: "topbar" },
      el(
        "div",
        { className: "brand-row" },
        el("img", { src: logoSrc, className: "brand-logo", alt: "Flow" }),
        el(
          "div",
          {},
          el(
            "div",
            { className: "brand-title" },
            el("span", {}, "Flow"),
            el("span", { className: "brand-badge" }, "Studio")
          ),
          el("div", { className: "subtle-meta" }, snap?.workspaceRoot || "Multi-Harness Spec & OKF Workspace")
        )
      ),
      el(
        "div",
        { className: "topbar-controls" },
        attentionBtn,
        pyBadge,
        wsSelect,
        el(
          "button",
          {
            className: `btn btn-quiet`,
            title: isPinned ? "Unpin workspace" : "Pin workspace",
            onClick: async () => {
              const res = await host.api("/api/pin-workspace", {
                workspacePath: state.workspacePath,
                pinned: !isPinned,
              });
              state.pinnedWorkspaces = res.pinnedWorkspaces || [];
              render();
            },
          },
          isPinned ? "★ Pinned" : "☆ Pin"
        ),
        el("button", { className: "btn btn-quiet", onClick: () => refreshSnapshot({ force: true }) }, "Refresh"),
        el("button", { className: "btn btn-primary", onClick: () => openNewSpecDrawer() }, "+ New Spec")
      )
    );
  }

  function renderTabsBar() {
    const tabs = [
      { id: "home", label: "Studio Home" },
      { id: "roadmap", label: "Roadmap" },
      { id: "review", label: "Spec & Review" },
      { id: "catalog", label: "Knowledge Catalog" },
      { id: "activity", label: "Activity & Hooks" },
    ];
    return el(
      "nav",
      { className: "tabs-bar", role: "tablist" },
      ...tabs.map((t) =>
        el(
          "button",
          {
            className: `tab-btn ${state.tab === t.id ? "active" : ""}`,
            role: "tab",
            onClick: async () => {
              state.tab = t.id;
              if (t.id === "home") await refreshPortfolio();
              else if (t.id === "review" && state.selectedDocRelPath) await loadDocument(state.selectedDocRelPath);
              else if (t.id === "catalog") await refreshCatalog();
              else if (t.id === "activity") await refreshActivity();
              render();
            },
          },
          t.label
        )
      )
    );
  }

  function renderHomeView() {
    const pinnedSet = new Set(state.pinnedWorkspaces || []);
    const workspaces = state.portfolio?.workspaces || [];

    const omnibarInput = el("input", {
      id: "studio-omnibar-input",
      type: "text",
      className: "text-input",
      placeholder: "Omnibar: type `/flow:spec ...`, `/flow:research ...`, or a spec slug...",
      onKeydown: async (e) => {
        if (e.key !== "Enter") return;
        const text = e.target.value.trim();
        if (!text) return;
        if (text.startsWith("/")) {
          await runFlowAction(text, "Omnibar Action");
          e.target.value = "";
        } else {
          state.catalogQuery = text;
          state.tab = "catalog";
          await refreshCatalog();
          render();
        }
      },
    });

    const pinBar = el(
      "div",
      { className: "pin-bar" },
      el("span", { className: "field-label" }, "Pinned & Known Workspaces:"),
      ...state.workspaces.map((ws) => {
        const name = ws.split("/").pop() || ws;
        const pinned = pinnedSet.has(ws);
        return el(
          "span",
          {
            className: `pin-chip ${ws === state.workspacePath ? "active" : ""}`,
            onClick: async () => {
              state.workspacePath = ws;
              state.selectedDocRelPath = null;
              await refreshSnapshot({ force: true });
            },
          },
          el("span", {}, name),
          el(
            "button",
            {
              className: `pin-toggle ${pinned ? "pinned" : ""}`,
              title: pinned ? "Unpin workspace" : "Pin workspace",
              onClick: async (ev) => {
                ev.stopPropagation();
                const res = await host.api("/api/pin-workspace", { workspacePath: ws, pinned: !pinned });
                state.pinnedWorkspaces = res.pinnedWorkspaces || [];
                render();
              },
            },
            pinned ? "★" : "☆"
          )
        );
      })
    );

    const grid = el("div", { className: "home-grid" });
    for (const wsSnap of workspaces) {
      const wsName = wsSnap.workspaceRoot.split("/").pop() || wsSnap.workspaceRoot;
      const specCount = wsSnap.specs?.length || 0;
      const kbCount = wsSnap.knowledge?.length || 0;
      grid.appendChild(
        el(
          "section",
          { className: "card" },
          el(
            "div",
            { className: "card-header" },
            el(
              "div",
              {},
              el("h3", { className: "card-title" }, wsName),
              el("div", { className: "subtle-meta mono" }, wsSnap.workspaceRoot)
            ),
            el(
              "button",
              {
                className: "btn",
                onClick: async () => {
                  state.workspacePath = wsSnap.workspaceRoot;
                  state.tab = "roadmap";
                  state.selectedDocRelPath = null;
                  await refreshSnapshot({ force: true });
                },
              },
              "Open"
            )
          ),
          el("p", { className: "card-desc" }, `${specCount} specs · ${kbCount} OKF notes · ${wsSnap.bundleInitialized ? "OKF v0.2 ready" : "Not initialized"}`)
        )
      );
    }

    return el(
      "div",
      {},
      el(
        "section",
        { className: "card" },
        el("h3", { className: "card-title" }, "Workspace Portfolio & Omnibar"),
        el("p", { className: "card-desc" }, "Switch pinned repositories, jump straight to active specifications, or dispatch Flow commands."),
        el("div", { className: "search-bar", style: "margin-top:12px" }, omnibarInput),
        pinBar
      ),
      grid
    );
  }

  function renderQuickPlanCard(compact = false) {
    const snap = state.snapshot;
    const planInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "Describe a feature or initiative to spec in this workspace...",
      onKeydown: async (e) => {
        if (e.key === "Enter") {
          const goal = e.target.value.trim();
          const cmd = goal ? `/flow:spec ${goal}` : "/flow:spec";
          await runFlowAction(cmd, goal ? `Spec: ${goal.slice(0, 48)}` : "Spec Feature");
          e.target.value = "";
        }
      },
    });

    return el(
      "section",
      { className: "card", style: compact ? "margin-top:14px;padding:14px 16px" : "" },
      el(
        "div",
        { className: "card-header" },
        el(
          "div",
          {},
          el("h3", { className: "card-title" }, "Spec in Selected Workspace"),
          el("p", { className: "card-desc" }, `Target workspace: ${snap?.workspaceRoot || state.workspacePath || "active workspace"}`)
        ),
        !snap?.bundleInitialized
          ? el("button", { className: "btn", onClick: () => runFlowAction("/flow:setup", "Initialize Flow") }, "Run /flow:setup")
          : null
      ),
      el(
        "div",
        { className: "search-bar", style: "margin-top:12px;margin-bottom:0" },
        planInput,
        el(
          "button",
          {
            className: "btn btn-primary",
            onClick: async () => {
              const goal = planInput.value.trim();
              const cmd = goal ? `/flow:spec ${goal}` : "/flow:spec";
              await runFlowAction(cmd, goal ? `Spec: ${goal.slice(0, 48)}` : "Spec Feature");
              planInput.value = "";
            },
          },
          "Spec Feature (/flow:spec)"
        ),
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              const goal = planInput.value.trim();
              const cmd = goal ? `/flow:prd ${goal}` : "/flow:prd";
              await runFlowAction(cmd, goal ? `PRD: ${goal.slice(0, 48)}` : "Plan Master PRD");
              planInput.value = "";
            },
          },
          "Master PRD (/flow:prd)"
        ),
        el("button", { className: "btn", onClick: () => openNewSpecDrawer(planInput.value.trim()) }, "+ Scaffold Draft")
      )
    );
  }

  function renderCompanionView() {
    const snap = state.snapshot;
    const activeSpec = snap?.specs?.find((s) => s.flowId === snap.activeFlowId) || snap?.specs?.[0] || null;
    const attentionCount = state.activitySnapshot?.attention?.length || 0;
    const logoSrc = window.__FLOW_LOGO_URI__ || "/logo.svg";

    const header = el(
      "div",
      { className: "topbar", style: "padding-bottom:12px;margin-bottom:14px" },
      el(
        "div",
        { className: "brand-row" },
        el("img", { src: logoSrc, className: "brand-logo", alt: "Flow" }),
        el(
          "div",
          {},
          el("div", { className: "brand-title" }, el("span", {}, "Flow"), el("span", { className: "brand-badge" }, "Companion")),
          el("div", { className: "subtle-meta" }, snap?.workspaceRoot?.split("/").pop() || "Workspace")
        )
      ),
      el(
        "div",
        { style: "display:flex;gap:6px;align-items:center" },
        attentionCount > 0
          ? el("button", { className: "attention-pill", onClick: () => openAttentionDrawer() }, `${attentionCount} needs you`)
          : null,
        el("button", { className: "btn", onClick: () => host.openStudioPanel() }, "Open Full Studio")
      )
    );

    const container = el("div", {}, header, renderQuickPlanCard(true));
    if (!activeSpec) {
      container.appendChild(
        el(
          "div",
          { className: "card" },
          el("h3", { className: "card-title" }, "No Active Specifications"),
          el("p", { className: "card-desc" }, "Scaffold a specification or feature above.")
        )
      );
      return container;
    }

    const pct = activeSpec.totalTasks > 0 ? Math.round((activeSpec.completedTasks / activeSpec.totalTasks) * 100) : 0;
    container.appendChild(
      el(
        "div",
        { className: "card" },
        el(
          "div",
          { className: "card-header" },
          el(
            "div",
            {},
            el("h3", { className: "card-title" }, el("span", { className: `status-dot ${activeSpec.state}` }), activeSpec.title),
            el("div", { className: "subtle-meta" }, `${activeSpec.completedTasks} / ${activeSpec.totalTasks} tasks verified (${pct}%)`)
          ),
          activeSpec.recommendedAction
            ? el(
                "button",
                {
                  className: "btn btn-primary",
                  onClick: () => runFlowAction(activeSpec.recommendedAction.command, activeSpec.recommendedAction.label),
                },
                activeSpec.recommendedAction.label
              )
            : null
        ),
        el("div", { className: "progress-row" }, el("div", { className: "progress-track" }, el("div", { className: `progress-fill ${pct === 100 ? "done" : ""}`, style: `width:${pct}%` })))
      )
    );

    for (const item of (snap?.knowledge || []).filter((k) => k.truthBlock).slice(0, 3)) {
      container.appendChild(
        el(
          "div",
          { className: "card" },
          el("div", { className: "subtle-meta" }, `Invariant · ${item.conceptId}`),
          el("div", { className: "truth-callout" }, item.truthBlock)
        )
      );
    }
    return container;
  }

  function renderRoadmapView() {
    const snap = state.snapshot;
    if (!snap) return el("div", { className: "subtle-meta" }, "Loading workspace...");
    const wrap = el("div", {}, renderQuickPlanCard(false));

    if (snap.specs.length === 0) {
      wrap.appendChild(
        el(
          "div",
          { className: "card" },
          el("h2", { className: "card-title" }, "Ready for Spec-Driven Development"),
          el(
            "p",
            { className: "card-desc" },
            snap.bundleInitialized
              ? "No specifications exist yet in .agents/bundles/specs/. Draft a Feature Spec or Master PRD to get started."
              : "Initialize OKF v0.2 bundles with /flow:setup or scaffold your first specification directly."
          ),
          el(
            "div",
            { style: "margin-top:16px;display:flex;gap:10px" },
            el("button", { className: "btn btn-primary", onClick: () => openNewSpecDrawer() }, "+ New Spec"),
            !snap.bundleInitialized
              ? el("button", { className: "btn", onClick: () => runFlowAction("/flow:setup", "Initialize Flow") }, "Run /flow:setup")
              : null
          )
        )
      );
      return wrap;
    }

    for (const spec of snap.specs) {
      const pct = spec.totalTasks > 0 ? Math.round((spec.completedTasks / spec.totalTasks) * 100) : 0;
      const card = el(
        "section",
        { className: "card" },
        el(
          "div",
          { className: "card-header" },
          el(
            "div",
            {},
            el("h3", { className: "card-title" }, el("span", { className: `status-dot ${spec.state}` }), spec.title),
            el("p", { className: "card-desc" }, spec.description || spec.flowId)
          ),
          el(
            "div",
            { style: "display:flex;gap:8px;align-items:center" },
            spec.unresolvedComments > 0 ? el("span", { className: "pill pill-warn" }, `${spec.unresolvedComments} review notes`) : null,
            el(
              "button",
              {
                className: "btn",
                onClick: async () => {
                  state.tab = "review";
                  state.specSubView = "dag";
                  await loadDocument(spec.relPath);
                  render();
                },
              },
              "Flow Tasks"
            ),
            el(
              "button",
              {
                className: "btn",
                onClick: async () => {
                  state.tab = "review";
                  state.specSubView = "document";
                  await loadDocument(spec.relPath);
                  render();
                },
              },
              "Read Spec"
            ),
            spec.recommendedAction
              ? el(
                  "button",
                  {
                    className: "btn btn-primary",
                    onClick: () => runFlowAction(spec.recommendedAction.command, spec.recommendedAction.label),
                  },
                  spec.recommendedAction.label
                )
              : null
          )
        ),
        el(
          "div",
          { className: "progress-row" },
          el("div", { className: "progress-track" }, el("div", { className: `progress-fill ${pct === 100 ? "done" : ""}`, style: `width:${pct}%` })),
          el("span", { className: "subtle-meta" }, `${spec.completedTasks} of ${spec.totalTasks} tasks complete`)
        )
      );

      if (spec.chapters && spec.chapters.length > 0) {
        const chList = el("div", { className: "chapter-list" });
        for (const ch of spec.chapters) {
          chList.appendChild(
            el(
              "div",
              { className: "chapter-row" },
              el(
                "div",
                {},
                el("span", { className: `status-dot ${ch.state}` }),
                el("strong", { style: "font-weight:500" }, ch.title),
                el("span", { className: "subtle-meta", style: "margin-left:10px" }, `${ch.completedTasks}/${ch.totalTasks}`)
              ),
              el(
                "div",
                { style: "display:flex;gap:6px" },
                ch.relPath
                  ? el(
                      "button",
                      {
                        className: "btn btn-quiet",
                        onClick: async () => {
                          state.tab = "review";
                          state.specSubView = "document";
                          await loadDocument(ch.relPath);
                          render();
                        },
                      },
                      "Inspect"
                    )
                  : null,
                ch.state !== "completed"
                  ? el(
                      "button",
                      {
                        className: "btn",
                        onClick: () => runFlowAction(`/flow:implement ${spec.flowId} ${ch.chapterId}`, `Implement ${ch.chapterId}`),
                      },
                      "Implement Chapter"
                    )
                  : el("span", { className: "pill pill-ok" }, "Verified")
              )
            )
          );
        }
        card.appendChild(chList);
      }
      wrap.appendChild(card);
    }
    return wrap;
  }

  function renderDagView() {
    const dag = state.specDag;
    if (!dag || !Array.isArray(dag.nodes) || dag.nodes.length === 0) {
      return el("div", { className: "card subtle-meta" }, "No task dependency nodes found for this specification.");
    }

    const colWidth = 190;
    const rowHeight = 76;
    const padX = 24;
    const padY = 24;
    const maxLevel = Math.max(0, ...dag.nodes.map((n) => n.level || 0));
    const levelBuckets = new Map();
    for (const node of dag.nodes) {
      const lvl = node.level || 0;
      if (!levelBuckets.has(lvl)) levelBuckets.set(lvl, []);
      levelBuckets.get(lvl).push(node);
    }
    const maxRows = Math.max(1, ...Array.from(levelBuckets.values()).map((a) => a.length));
    const svgWidth = Math.max(600, (maxLevel + 1) * colWidth + padX * 2);
    const svgHeight = Math.max(220, maxRows * rowHeight + padY * 2);

    const pos = new Map();
    for (const [lvl, items] of levelBuckets.entries()) {
      items.forEach((n, idx) => {
        pos.set(n.id, { x: padX + lvl * colWidth, y: padY + idx * rowHeight });
      });
    }

    const svg = svgEl("svg", {
      class: "dag-svg",
      viewBox: `0 0 ${svgWidth} ${svgHeight}`,
      width: svgWidth,
      height: svgHeight,
    });

    for (const edge of dag.edges || []) {
      const from = pos.get(edge.from);
      const to = pos.get(edge.to);
      if (!from || !to) continue;
      svg.appendChild(
        svgEl("path", {
          d: `M ${from.x + 150} ${from.y + 24} C ${from.x + 170} ${from.y + 24}, ${to.x - 20} ${to.y + 24}, ${to.x} ${to.y + 24}`,
          fill: "none",
          stroke: "var(--flow-line)",
          "stroke-width": "2",
        })
      );
    }

    for (const n of dag.nodes) {
      const p = pos.get(n.id);
      if (!p) continue;
      const g = svgEl("g", { transform: `translate(${p.x}, ${p.y})` });
      const stroke = n.state === "completed" ? "var(--flow-ok)" : n.state === "in_progress" ? "var(--flow-warn)" : "var(--flow-line)";
      g.appendChild(
        svgEl("rect", {
          width: "150",
          height: "48",
          rx: "8",
          fill: "var(--flow-surface-subtle)",
          stroke,
          "stroke-width": "1.6",
        })
      );
      g.appendChild(
        svgEl("text", { x: "10", y: "19", fill: "var(--flow-fg)", "font-size": "12", "font-weight": "600" }, n.shortId || n.id)
      );
      g.appendChild(
        svgEl(
          "text",
          { x: "10", y: "36", fill: "var(--flow-muted-fg)", "font-size": "10.5" },
          String(n.title || n.state).slice(0, 22)
        )
      );
      svg.appendChild(g);
    }

    const lanes = el("div", { className: "task-steps" });
    for (const step of dag.steps || []) {
      const lane = el(
        "div",
        { className: "task-step" },
        el("strong", {}, `Step ${step.step_index}`),
        el("div", { className: "subtle-meta" }, `${step.tasks.length} tasks on separate files`)
      );
      for (const t of step.tasks || []) {
        lane.appendChild(
          el(
            "div",
            { className: "task-card" },
            el("div", {}, el("strong", {}, `${t.task_id}: `), el("span", {}, t.title || t.task_id)),
            el("div", { className: "subtle-meta mono" }, `${(t.files || []).length} files · est ${t.estimated_loc} LOC`)
          )
        );
      }
      lanes.appendChild(lane);
    }

    return el(
      "div",
      {},
      el(
        "div",
        { className: "card" },
        el("h3", { className: "card-title" }, `Flow Tasks (${dag.nodes.length})`),
        el(
          "p",
          { className: "card-desc" },
          `Inline fast-path eligible: ${dag.inline_fast_path_eligible ? "yes" : "no"} · Total steps: ${(dag.steps || []).length}`
        ),
        el("div", { className: "dag-viewport", style: "margin-top:12px" }, svg),
        lanes
      )
    );
  }

  function renderSpecReviewView() {
    const snap = state.snapshot;
    const allDocs = [];
    for (const s of snap?.specs || []) {
      allDocs.push({ label: `Spec · ${s.title}`, relPath: s.relPath });
      for (const ch of s.chapters || []) {
        if (ch.relPath) allDocs.push({ label: `  ↳ ${ch.chapterId}`, relPath: ch.relPath });
      }
    }
    for (const k of snap?.knowledge || []) {
      allDocs.push({ label: `${k.type} · ${k.title}`, relPath: k.relPath });
    }

    const docPicker = el(
      "select",
      {
        className: "select-input",
        style: "min-width:260px",
        onChange: async (e) => {
          await loadDocument(e.target.value);
          render();
        },
      },
      ...allDocs.map((d) => el("option", { value: d.relPath, selected: d.relPath === state.selectedDocRelPath }, d.label))
    );

    const subViewToggle = el(
      "div",
      { className: "segmented" },
      ...[
        { id: "document", label: "Spec" },
        { id: "dag", label: "Flow Tasks" },
      ].map((v) =>
        el(
          "button",
          {
            className: state.specSubView === v.id ? "active" : "",
            onClick: () => {
              state.specSubView = v.id;
              render();
            },
          },
          v.label
        )
      )
    );

    const openComments = (state.currentDoc?.comments || []).filter((c) => !c.resolved && c.state !== "resolved");
    const reviewSummaryBadge = state.specReviewSummary
      ? el(
          "span",
          { className: `pill ${state.specReviewSummary.status === "open" ? "pill-warn" : "pill-ok"}` },
          `${state.specReviewSummary.authors?.length || 0} reviewers · ${state.specReviewSummary.open_count || 0} open`
        )
      : null;

    const toolbar = el(
      "div",
      { className: "search-bar" },
      docPicker,
      subViewToggle,
      reviewSummaryBadge,
      state.selectedDocRelPath
        ? el("button", { className: "btn", onClick: () => host.openFile(state.workspacePath, state.selectedDocRelPath, 1) }, "Open in Editor")
        : null,
      openComments.length > 0
        ? el("button", { className: "btn btn-primary", onClick: () => runFlowAction(state.revisePrompt, "Revise Specification") }, `Dispatch /flow:revise (${openComments.length})`)
        : el("span", { className: "subtle-meta" }, "Click any line number to attach feedback.")
    );

    if (state.specSubView === "dag") {
      return el("div", {}, toolbar, renderDagView());
    }

    if (!state.currentDoc) {
      return el("div", {}, toolbar, el("div", { className: "subtle-meta" }, "Select a document to review."));
    }

    const outline = el(
      "aside",
      { className: "outline-nav" },
      el("div", { className: "field-label", style: "padding:4px 9px" }, "Outline"),
      ...(state.currentDoc.headings || []).map((h) =>
        el(
          "button",
          {
            className: "outline-item",
            style: `padding-left:${Math.min(h.level * 8, 28)}px`,
            onClick: () => {
              const row = document.getElementById(`spec-line-${h.line}`);
              if (row) row.scrollIntoView({ behavior: "smooth", block: "center" });
            },
          },
          h.text
        )
      )
    );

    const linesBox = el("div", { className: "code-lines" });
    const commentsByLine = new Map();
    for (const c of state.currentDoc.comments || []) {
      if (c.resolved || c.state === "resolved") continue;
      const arr = commentsByLine.get(c.endLine) || [];
      arr.push(c);
      commentsByLine.set(c.endLine, arr);
    }

    for (const ln of state.currentDoc.lines) {
      linesBox.appendChild(
        el(
          "div",
          { className: "code-line", id: `spec-line-${ln.lineNumber}` },
          el(
            "span",
            {
              className: "line-num",
              title: "Add inline review feedback",
              onClick: () => {
                state.activeCommentLine = ln.lineNumber;
                render();
              },
            },
            String(ln.lineNumber)
          ),
          el("span", { className: "line-text" }, ln.text || " ")
        )
      );

      for (const c of commentsByLine.get(ln.lineNumber) || []) {
        const upvotes = Array.isArray(c.upvotes) ? c.upvotes.length : 0;
        const kindLabel = c.commentKind || c.kind || "feedback";
        linesBox.appendChild(
          el(
            "div",
            { className: "inline-comment-box" },
            el(
              "div",
              { style: "display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;gap:8px;flex-wrap:wrap" },
              el(
                "div",
                { style: "display:flex;gap:6px;align-items:center" },
                el("strong", { style: "font-size:12px" }, `Line ${c.startLine}`),
                el("span", { className: `comment-chip ${kindLabel === "blocker" ? "blocker" : ""}` }, kindLabel),
                c.authorName ? el("span", { className: "subtle-meta" }, c.authorName) : null
              ),
              el(
                "div",
                { style: "display:flex;gap:6px;align-items:center" },
                el(
                  "button",
                  {
                    className: "btn btn-quiet",
                    style: "padding:2px 8px;font-size:12px",
                    onClick: async () => {
                      await host.api("/api/review-comments", {
                        action: "update",
                        workspacePath: state.workspacePath,
                        relPath: state.selectedDocRelPath,
                        commentId: c.id,
                        toggleUpvote: true,
                      });
                      await loadDocument(state.selectedDocRelPath);
                      render();
                    },
                  },
                  `▲ ${upvotes}`
                ),
                el(
                  "button",
                  {
                    className: "btn btn-quiet",
                    style: "padding:2px 8px;font-size:12px",
                    onClick: async () => {
                      await host.api("/api/review-comments", {
                        action: "resolve",
                        workspacePath: state.workspacePath,
                        relPath: state.selectedDocRelPath,
                        commentId: c.id,
                      });
                      await loadDocument(state.selectedDocRelPath);
                      render();
                    },
                  },
                  "Resolve"
                )
              )
            ),
            el("div", {}, c.body)
          )
        );
      }

      if (state.activeCommentLine === ln.lineNumber) {
        const kindSel = el(
          "select",
          {
            className: "select-input",
            onChange: (e) => {
              state.activeCommentKind = e.target.value;
            },
          },
          ...["feedback", "question", "suggestion", "blocker"].map((k) =>
            el("option", { value: k, selected: state.activeCommentKind === k }, k)
          )
        );
        const inputEl = el("textarea", {
          className: "textarea-input",
          rows: 2,
          placeholder: "Describe requested spec refinement...",
          style: "width:100%;margin:8px 0",
        });
        linesBox.appendChild(
          el(
            "div",
            { className: "inline-comment-box" },
            el("div", { style: "display:flex;gap:8px;align-items:center" }, el("span", { className: "field-label" }, "Kind:"), kindSel),
            inputEl,
            el(
              "div",
              { style: "display:flex;gap:8px;justify-content:flex-end" },
              el("button", { className: "btn btn-quiet", onClick: () => { state.activeCommentLine = null; render(); } }, "Cancel"),
              el(
                "button",
                {
                  className: "btn btn-primary",
                  onClick: async () => {
                    const body = inputEl.value.trim();
                    if (!body) return;
                    await host.api("/api/review-comments", {
                      action: "add",
                      workspacePath: state.workspacePath,
                      relPath: state.selectedDocRelPath,
                      startLine: ln.lineNumber,
                      endLine: ln.lineNumber,
                      quote: ln.text,
                      commentKind: kindSel.value,
                      body,
                    });
                    state.activeCommentLine = null;
                    await loadDocument(state.selectedDocRelPath);
                    await refreshSnapshot({ force: true });
                  },
                },
                "Save Feedback"
              )
            )
          )
        );
      }
    }

    return el("div", {}, toolbar, el("div", { className: "reader-layout" }, outline, linesBox));
  }

  function renderCatalogView() {
    const queryInput = el("input", {
      type: "search",
      className: "text-input",
      placeholder: "Search OKF concepts, truth blocks, specs, or sibling repositories (press / to focus)...",
      value: state.catalogQuery,
      onKeydown: async (e) => {
        if (e.key === "Enter") {
          state.catalogQuery = e.target.value;
          await refreshCatalog();
          render();
        }
      },
    });

    const modeSegmented = el(
      "div",
      { className: "segmented" },
      ...[
        { id: "hybrid", label: "Hybrid" },
        { id: "bm25", label: "BM25" },
        { id: "semantic", label: "Semantic" },
        { id: "federated", label: "Federated" },
      ].map((m) =>
        el(
          "button",
          {
            className: state.catalogMode === m.id ? "active" : "",
            onClick: async () => {
              state.catalogMode = m.id;
              await refreshCatalog();
              render();
            },
          },
          m.label
        )
      )
    );

    const searchRow = el(
      "div",
      { className: "search-bar" },
      queryInput,
      modeSegmented,
      el(
        "button",
        {
          className: "btn btn-primary",
          onClick: async () => {
            state.catalogQuery = queryInput.value;
            await refreshCatalog();
            render();
          },
        },
        "Search"
      ),
      el(
        "button",
        {
          className: "btn",
          onClick: async () => {
            await host.api("/api/catalog-index", { workspacePath: state.workspacePath });
            await refreshCatalog();
            showToast("Synchronized knowledge catalog index from Markdown bundles.");
            render();
          },
        },
        "Re-index Catalog"
      ),
      el(
        "button",
        {
          className: "btn btn-quiet",
          onClick: async () => {
            const d = await host.api("/api/catalog-drift", { workspacePath: state.workspacePath });
            state.driftReport = d.report;
            render();
          },
        },
        "Check Citation Drift"
      )
    );

    const statusLine = state.catalogStatus
      ? el(
          "div",
          { className: "subtle-meta", style: "margin-bottom:14px" },
          `Knowledge Catalog · ${state.catalogStatus.entry_count ?? 0} entries · Mode: ${state.catalogMode}`
        )
      : null;

    const resultsWrap = el("div", {});
    if (state.driftReport) {
      const brokenCount = (state.driftReport.broken_links?.length || 0) + (state.driftReport.missing_sources?.length || 0);
      resultsWrap.appendChild(
        el(
          "div",
          { className: "card" },
          el("h3", { className: "card-title" }, brokenCount === 0 ? "Zero citation or link drift detected" : `${brokenCount} citation / link drift issues`),
          ...[...(state.driftReport.broken_links || []), ...(state.driftReport.missing_sources || [])].map((issue) =>
            el("div", { className: "subtle-meta mono", style: "margin-top:6px" }, `${issue.rel_path} → ${issue.target} (${issue.issue_kind})`)
          )
        )
      );
    }

    for (const hit of state.catalogHits) {
      resultsWrap.appendChild(
        el(
          "article",
          { className: "card" },
          el(
            "div",
            { className: "card-header" },
            el(
              "div",
              {},
              el("h3", { className: "card-title" }, hit.title),
              el(
                "div",
                { className: "subtle-meta" },
                `${hit.concept_type} · ${hit.concept_id}${hit.plane ? ` · ${hit.plane}:${hit.workspace || ""}` : ""}`
              )
            ),
            el(
              "div",
              { style: "display:flex;gap:8px;align-items:center" },
              el("span", { className: `pill ${hit.trust_tier === "verified" ? "pill-ok" : ""}` }, hit.trust_tier || "draft"),
              hit.rel_path
                ? el(
                    "button",
                    {
                      className: "btn btn-quiet",
                      onClick: async () => {
                        state.tab = "review";
                        state.specSubView = "document";
                        await loadDocument(hit.rel_path);
                        render();
                      },
                    },
                    "Open"
                  )
                : null
            )
          ),
          hit.description ? el("p", { className: "card-desc" }, hit.description) : null,
          hit.truth_block ? el("div", { className: "truth-callout" }, hit.truth_block) : null
        )
      );
    }

    return el("div", {}, searchRow, statusLine, resultsWrap);
  }

  function renderModelsStratumCard() {
    const mq = state.modelsQuota;
    if (!mq || !mq.dynamicByHarness) {
      return el("section", { className: "card" }, el("h3", { className: "card-title" }, "Model Routing"), el("p", { className: "card-desc" }, "Loading live model catalog across harnesses..."));
    }

    const grid = el("div", { className: "model-stratum-grid" });
    for (const [hid, entry] of Object.entries(mq.dynamicByHarness)) {
      const rec = entry.recommendations || {};
      grid.appendChild(
        el(
          "div",
          { className: "stratum-card" },
          el(
            "div",
            { style: "display:flex;justify-content:space-between;align-items:center;margin-bottom:6px" },
            el("strong", {}, hid),
            el("span", { className: "subtle-meta" }, `${entry.candidateCount || 0} live models`)
          ),
          ...[
            { label: "Strongest model", val: rec.strong },
            { label: "Standard worker", val: rec.standard },
            { label: "Light helper", val: rec.light },
          ].map((row) =>
            el(
              "div",
              { className: "stratum-row" },
              el("span", { className: "subtle-meta" }, row.label),
              el(
                "span",
                { className: "mono" },
                row.val ? `${row.val.model || row.val.id} (${row.val.effort || "medium"})` : "unavailable"
              )
            )
          )
        )
      );
    }

    return el(
      "section",
      { className: "card" },
      el("h3", { className: "card-title" }, `Model Routing (${mq.decisionProvider || "builtin"})`),
      el("p", { className: "card-desc" }, "Continuous (model, effort) routing across installed harnesses with fallback to the strongest available model."),
      grid
    );
  }

  function renderPermissionsCard() {
    const report = state.permissionsReport;
    if (!report) return null;

    const missing = report.missingRecommended || [];
    const card = el(
      "section",
      { className: "card" },
      el(
        "div",
        { className: "card-header" },
        el(
          "div",
          {},
          el("h3", { className: "card-title" }, "Workspace Smart Allowlist"),
          el("p", { className: "card-desc" }, `Status: ${report.summary?.status || "ready"} · ${missing.length} recommended entries missing`)
        ),
        missing.length > 0
          ? el(
              "button",
              {
                className: "btn btn-primary",
                onClick: async () => {
                  await host.api("/api/permissions", {
                    action: "apply",
                    workspacePath: state.workspacePath,
                    allowGrants: missing.map((m) => m.pattern || m),
                    enableHook: true,
                  });
                  state.permissionsReport = await host.api("/api/permissions", { workspacePath: state.workspacePath });
                  showToast("Applied workspace smart allowlist.");
                  render();
                },
              },
              `Apply ${missing.length} Recommended`
            )
          : el("span", { className: "pill pill-ok" }, "Configured")
      )
    );
    if (missing.length > 0) {
      const list = el("div", { style: "display:flex;flex-direction:column;gap:8px;margin-top:10px" });
      for (const item of missing.slice(0, 6)) {
        list.appendChild(
          el(
            "div",
            { className: "perm-row" },
            el("span", { className: "mono" }, item.pattern || String(item)),
            item.reason ? el("span", { className: "subtle-meta" }, item.reason) : null
          )
        );
      }
      card.appendChild(list);
    }
    return card;
  }

  function renderActivityView() {
    const installedHarnesses = state.harnesses.filter((h) => h.installed);
    const harnessPicker = el(
      "select",
      {
        className: "select-input",
        value: state.selectedHarness,
        onChange: (e) => {
          state.selectedHarness = e.target.value;
          render();
        },
      },
      el("option", { value: "host", selected: state.selectedHarness === "host" }, "Active Host Agent"),
      ...installedHarnesses.map((h) => el("option", { value: h.id, selected: state.selectedHarness === h.id }, `${h.label} (${h.binary})`))
    );

    const modeToggle = el(
      "div",
      { className: "segmented" },
      ...[
        { id: "direct-workspace", label: "Direct Write" },
        { id: "worktree-isolated", label: "Isolated Worktree" },
        { id: "read-only", label: "Read-Only" },
      ].map((m) =>
        el(
          "button",
          {
            className: state.executionMode === m.id ? "active" : "",
            onClick: () => {
              state.executionMode = m.id;
              render();
            },
          },
          m.label
        )
      )
    );

    const promptInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "e.g. /flow:review idempotent-webhooks or /flow:implement ...",
    });

    const bridgeCard = el(
      "section",
      { className: "card" },
      el("h3", { className: "card-title" }, "Run in another harness"),
      el("p", { className: "card-desc" }, "Dispatch tasks or run planning and spec validation on the strongest available harness with worktree isolation."),
      state.writerGuard?.activeWriter
        ? el("div", { className: "truth-callout", style: "border-left-color:var(--flow-warn)" }, `Advisory: ${state.writerGuard.reason} Consider Isolated Worktree or Read-Only if running concurrently.`)
        : null,
      el("div", { className: "search-bar", style: "margin-top:14px" }, harnessPicker, modeToggle),
      el(
        "div",
        { className: "search-bar", style: "margin-bottom:0" },
        promptInput,
        el(
          "button",
          {
            className: "btn btn-primary",
            onClick: async () => {
              const text = promptInput.value.trim();
              if (!text) return;
              await runFlowAction(text, "Cross-Harness Dispatch");
              promptInput.value = "";
            },
          },
          "Dispatch"
        ),
        el(
          "button",
          {
            className: "btn",
            title: "Run prompt on the strongest model for planning or spec validation",
            onClick: async () => {
              const text = promptInput.value.trim();
              if (!text) return;
              const res = await host.api("/api/harness-delegate", {
                workspacePath: state.workspacePath,
                harness: state.selectedHarness === "host" ? null : state.selectedHarness,
                taskKind: "semantic_validation",
                prompt: text,
              });
              showToast(`Dispatched via ${res.harness || "strong"} (${res.model || "auto"})`);
              promptInput.value = "";
              await refreshActivity();
              render();
            },
          },
          "Run on strongest model"
        )
      )
    );

    const pyInfo = state.snapshot?.python;
    const pyCard = el(
      "section",
      { className: "card" },
      el("h3", { className: "card-title" }, "Detected Python Environment & Entrypoints"),
      el("p", { className: "card-desc" }, pyInfo ? `Manager: ${pyInfo.manager} (${pyInfo.reason}) · Run prefix: ${pyInfo.runPrefix.join(" ")}` : "No Python project metadata detected."),
      pyInfo && pyInfo.entrypoints.length > 0
        ? el(
            "div",
            { style: "margin-top:12px;display:flex;gap:8px;flex-wrap:wrap" },
            ...pyInfo.entrypoints.map((ep) =>
              el(
                "button",
                {
                  className: "btn",
                  onClick: async () => {
                    const out = await host.api("/api/run-entrypoint", {
                      workspacePath: state.workspacePath,
                      entrypoint: ep,
                      args: ["--help"],
                    });
                    showToast(`${ep} --help exited with code ${out.exitCode}`);
                  },
                },
                `${pyInfo.runPrefix.join(" ")} ${ep} --help`
              )
            )
          )
        : null
    );

    const runsCard = el(
      "section",
      { className: "card" },
      el("h3", { className: "card-title" }, "Recent Cross-Harness Runs & Hook Telemetry"),
      state.harnessRuns.length === 0
        ? el("p", { className: "card-desc" }, "No external harness runs dispatched in this session yet.")
        : el(
            "div",
            { className: "chapter-list" },
            ...state.harnessRuns.map((r) =>
              el(
                "div",
                { className: "chapter-row" },
                el("div", {}, el("strong", {}, `${r.label} · ${r.executionMode}`), el("div", { className: "subtle-meta mono" }, r.prompt)),
                el("span", { className: `pill ${r.status === "completed" ? "pill-ok" : ""}` }, r.status)
              )
            )
          )
    );

    return el(
      "div",
      {},
      bridgeCard,
      renderModelsStratumCard(),
      renderPermissionsCard(),
      el("div", { className: "grid-two" }, pyCard, runsCard)
    );
  }

  function openAttentionDrawer() {
    if (!attentionDrawerEl || !backdropEl) return;
    attentionDrawerEl.textContent = "";
    backdropEl.classList.remove("hidden");
    attentionDrawerEl.classList.remove("hidden");

    const attention = state.activitySnapshot?.attention || [];
    attentionDrawerEl.appendChild(
      el(
        "div",
        { className: "card-header" },
        el("h3", { className: "card-title" }, `Attention Queue (${attention.length})`),
        el("button", { className: "btn btn-quiet", onClick: closeDrawers }, "Close")
      )
    );

    if (attention.length === 0) {
      attentionDrawerEl.appendChild(el("p", { className: "card-desc" }, "No blocked leases, stale reviews, or stalled sessions right now."));
      return;
    }

    for (const item of attention) {
      attentionDrawerEl.appendChild(
        el(
          "div",
          { className: `attention-item ${item.severity === "critical" ? "critical" : ""}` },
          el("strong", {}, item.title || item.kind),
          el("div", { className: "subtle-meta" }, item.detail || item.reason || ""),
          item.relPath
            ? el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "margin-top:6px",
                  onClick: async () => {
                    closeDrawers();
                    state.tab = "review";
                    await loadDocument(item.relPath);
                    render();
                  },
                },
                "Inspect"
              )
            : null
        )
      );
    }
  }

  function openNewSpecDrawer(initialGoal = "") {
    if (!drawerEl || !backdropEl) return;
    drawerEl.textContent = "";
    backdropEl.classList.remove("hidden");
    drawerEl.classList.remove("hidden");

    const kindSelect = el(
      "select",
      { className: "select-input" },
      el("option", { value: "Spec" }, "Feature Specification (/flow:spec)"),
      el("option", { value: "PRD" }, "Master PRD (/flow:prd)")
    );
    const slugInput = el("input", { type: "text", className: "text-input", placeholder: "Optional (auto-derived from title if left blank)" });
    const titleInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "Human-readable title",
      value: initialGoal,
      onInput: (e) => {
        const autoSlug = String(e.target.value || "")
          .trim()
          .toLowerCase()
          .replace(/[^a-z0-9-]+/g, "-")
          .replace(/^-+|-+$/g, "")
          .slice(0, 48);
        slugInput.placeholder = autoSlug ? `Auto: ${autoSlug}` : "Optional (auto-derived from title if left blank)";
      },
    });
    const problemInput = el("textarea", {
      className: "textarea-input",
      rows: 4,
      placeholder: "Problem framing, constraints, and target user outcomes...",
    });
    const chaptersCheck = el("input", { type: "checkbox", checked: true });

    drawerEl.append(
      el("div", { className: "card-header" }, el("h3", { className: "card-title" }, "New OKF Specification"), el("button", { className: "btn btn-quiet", onClick: closeDrawers }, "Close")),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Artifact Kind"), kindSelect),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Title"), titleInput),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Flow ID Slug (Optional)"), slugInput),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Problem Statement"), problemInput),
      el("label", { style: "display:flex;align-items:center;gap:8px;font-size:13px" }, chaptersCheck, el("span", {}, "Initialize chapter structure (`ch01-*`)")),
      el(
        "div",
        { style: "display:flex;gap:8px;flex-wrap:wrap;margin-top:8px" },
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              try {
                const created = await host.api("/api/create-spec", {
                  workspacePath: state.workspacePath,
                  kind: kindSelect.value,
                  flowId: slugInput.value,
                  title: titleInput.value,
                  problem: problemInput.value,
                  hasChapters: chaptersCheck.checked,
                });
                closeDrawers();
                showToast(`Created ${created.relPath}`);
                await refreshSnapshot({ force: true });
              } catch (err) {
                showToast(err instanceof Error ? err.message : String(err));
              }
            },
          },
          "Create Draft Only"
        ),
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              const summary = [titleInput.value.trim(), problemInput.value.trim()].filter(Boolean).join(" — ");
              const baseCmd = kindSelect.value === "PRD" ? "/flow:prd" : "/flow:spec";
              const cmd = summary ? `${baseCmd} ${summary}` : baseCmd;
              closeDrawers();
              await runFlowAction(cmd, `Spec in ${state.workspacePath.split("/").pop() || "Workspace"}`);
            },
          },
          "Spec Directly with Agent"
        ),
        el(
          "button",
          {
            className: "btn btn-primary",
            onClick: async () => {
              try {
                const created = await host.api("/api/create-spec", {
                  workspacePath: state.workspacePath,
                  kind: kindSelect.value,
                  flowId: slugInput.value,
                  title: titleInput.value,
                  problem: problemInput.value,
                  hasChapters: chaptersCheck.checked,
                });
                closeDrawers();
                await refreshSnapshot({ force: true });
                await runFlowAction(created.dispatchCommand, `Spec ${created.flowId}`);
              } catch (err) {
                showToast(err instanceof Error ? err.message : String(err));
              }
            },
          },
          "Create & Co-Spec with Agent"
        )
      )
    );
  }

  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
      if (state.tab === "catalog") {
        const input = rootEl?.querySelector("input[type='search']");
        if (input) {
          e.preventDefault();
          input.focus();
        }
      } else if (state.tab === "home") {
        const omni = document.getElementById("studio-omnibar-input");
        if (omni) {
          e.preventDefault();
          omni.focus();
        }
      }
    } else if (e.key === "Escape") {
      closeDrawers();
    }
  });

  backdropEl?.addEventListener("click", closeDrawers);

  host.onEvent(async (evt) => {
    if (evt?.type === "workspace.changed") {
      const uris = Array.isArray(evt.uris) && evt.uris.length > 0 ? evt.uris : evt.workspacePath ? [evt.workspacePath] : [];
      const ctx = await host.api("/api/studio-context", buildContextRequestPayload(uris));
      state.workspaces = ctx.workspaces || state.workspaces;
      state.pinnedWorkspaces = ctx.pinnedWorkspaces || state.pinnedWorkspaces;
      state.activeWorkspacePaths = ctx.activeWorkspaces || [ctx.defaultWorkspace];
      if (ctx.defaultWorkspace && ctx.defaultWorkspace !== state.workspacePath) {
        state.workspacePath = ctx.defaultWorkspace;
        state.selectedDocRelPath = null;
        state.currentDoc = null;
      }
      await refreshSnapshot({ force: true });
    } else if (evt?.type === "bundle.changed" || evt?.type === "spec.created") {
      if (evt.workspacePath && evt.workspacePath !== state.workspacePath && !state.workspaces.includes(evt.workspacePath)) {
        state.workspaces = [evt.workspacePath, ...state.workspaces];
      }
      await refreshSnapshot();
    } else if (evt?.type === "harness.completed") {
      if (state.tab === "activity") {
        await refreshActivity();
        render();
      }
    }
  });

  bootstrap();
})();
