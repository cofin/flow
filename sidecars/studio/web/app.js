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
  const commentModalEl = document.getElementById("comment-modal");
  const lightboxEl = document.getElementById("media-lightbox");
  const backdropEl = document.getElementById("drawer-backdrop");
  const toastRegion = document.getElementById("toast-region");
  /** @type {HTMLElement | null} */
  let floatGutterEl = null;

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
  window.addEventListener("message", async (event) => {
    if (event.data?.type === "theme-change") queueMicrotask(syncHostTheme);
    if (event.data?.type === "navigateHome") {
      state.tab = "home";
      await refreshPortfolio();
      render();
    }
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
    remoteRepo: "",
    workspaces: [],
    pinnedWorkspaces: [],
    activeWorkspacePaths: [],
    snapshot: null,
    lastSnapshotEtag: null,
    lastLiveEtag: null,
    portfolio: null,
    branchFilter: "current",
    selectedDocRelPath: null,
    selectedDocGitRef: null,
    currentDoc: null,
    specDag: null,
    specReviewSummary: null,
    activeCommentLine: null,
    activeCommentRange: null,
    activeCommentKind: "feedback",
    commentFilter: "all",
    editingCommentId: null,
    replyingCommentId: null,
    revisePrompt: "",
    setupAudit: null,
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
    commentModalEl?.classList.add("hidden");
    lightboxEl?.classList.add("hidden");
    if (floatGutterEl) floatGutterEl.classList.add("hidden");
  }

  function hasOpenDetailsIn(container) {
    if (!container) return false;
    return Boolean(container.querySelector("details.action-menu[open]"));
  }

  function isOverlayOpen() {
    return (
      (commentModalEl && !commentModalEl.classList.contains("hidden")) ||
      (lightboxEl && !lightboxEl.classList.contains("hidden")) ||
      (drawerEl && !drawerEl.classList.contains("hidden")) ||
      (attentionDrawerEl && !attentionDrawerEl.classList.contains("hidden"))
    );
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
    if (!state.workspacePath && !state.remoteRepo) return;
    const snap = await host.api("/api/bundle-snapshot", {
      ...(state.workspacePath ? { workspacePath: state.workspacePath } : {}),
      ...(state.remoteRepo ? { remoteRepo: state.remoteRepo } : {}),
      registerWorkspace: Boolean(state.workspacePath && !state.remoteRepo),
    });
    const etagChanged = snap.contentEtag && snap.contentEtag !== state.lastSnapshotEtag;
    const liveChanged = snap.liveEtag !== undefined && snap.liveEtag !== state.lastLiveEtag;
    state.snapshot = snap;
    state.lastSnapshotEtag = snap.contentEtag || null;
    state.lastLiveEtag = snap.liveEtag || null;
    if (state.workspacePath && !state.workspaces.includes(state.workspacePath)) {
      state.workspaces = [state.workspacePath, ...state.workspaces];
    }
    if (!state.selectedDocRelPath && snap.specs.length > 0) {
      state.selectedDocRelPath = snap.specs[0].relPath;
      state.selectedDocGitRef = snap.specs[0].gitRef || null;
    }
    if (options.force || etagChanged || liveChanged) {
      if (state.tab === "home" && (options.force || etagChanged)) await refreshPortfolio();
      else if (state.tab === "review" && state.selectedDocRelPath && (options.force || etagChanged)) {
        await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
      } else if (state.tab === "catalog" && (options.force || etagChanged)) await refreshCatalog();
      else if (state.tab === "activity" && (options.force || etagChanged)) await refreshActivity();
      try {
        if (state.workspacePath && !state.remoteRepo) {
          state.activitySnapshot = await host.api("/api/activity", { workspacePath: state.workspacePath });
        }
      } catch {
        // Non-fatal background activity check.
      }
      if (!isOverlayOpen() && !hasOpenDetailsIn(rootEl)) {
        render();
      }
    }
  }

  async function refreshPortfolio() {
    try {
      state.portfolio = await host.api("/api/portfolio-snapshot", {});
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to load workspace portfolio");
    }
  }

  async function loadDocument(relPath, gitRef = state.selectedDocGitRef) {
    state.selectedDocRelPath = relPath;
    state.selectedDocGitRef = gitRef || null;
    state.currentDoc = await host.api("/api/spec-document", {
      workspacePath: state.workspacePath,
      relPath,
      ...(gitRef ? { gitRef } : {}),
      ...(state.remoteRepo ? { repoLocator: state.remoteRepo } : {}),
    });
    const flowId = activeSpecFlowId();
    const [commentRes, dagRes, reviewRes] = await Promise.all([
      host.api("/api/review-comments", {
        action: "list",
        workspacePath: state.workspacePath,
        relPath,
        flowId,
        ...(state.remoteRepo ? { repoLocator: state.remoteRepo } : {}),
      }),
      flowId
        ? host
            .api("/api/spec-dag", {
              workspacePath: state.workspacePath,
              flowId,
              ...(gitRef ? { gitRef } : {}),
              ...(state.remoteRepo ? { repoLocator: state.remoteRepo } : {}),
            })
            .catch(() => null)
        : Promise.resolve(null),
      flowId
        ? host
            .api("/api/spec-review", {
              workspacePath: state.workspacePath,
              flowId,
              ...(gitRef ? { gitRef } : {}),
              ...(state.remoteRepo ? { repoLocator: state.remoteRepo } : {}),
            })
            .catch(() => null)
        : Promise.resolve(null),
    ]);
    if (Array.isArray(commentRes.comments) && state.currentDoc) {
      state.currentDoc.comments = commentRes.comments;
    }
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
        el(
          "button",
          {
            className: `home-nav-btn ${state.tab === "home" ? "active" : ""}`,
            title: "Studio Home",
            onClick: async () => {
              state.tab = "home";
              await refreshPortfolio();
              render();
            },
          },
          "⌂ Home"
        ),
        el("img", { src: logoSrc, className: "brand-logo", alt: "Flow" }),
        el(
          "div",
          {},
          el(
            "div",
            { className: "brand-title" },
            el("span", {}, "Flow"),
            el("span", { className: "brand-badge" }, "Studio"),
            state.remoteRepo ? el("span", { className: "pill pill-warn" }, `Remote: ${state.remoteRepo}`) : null,
            snap?.currentBranch ? el("span", { className: "pill mono" }, snap.currentBranch) : null
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
        el(
          "button",
          {
            className: "btn btn-quiet",
            title: "Sync checklists, stale claims, and branch tracking",
            onClick: async () => {
              try {
                const syncRes = await host.api("/api/sync", { workspacePath: state.workspacePath });
                const changed = (syncRes.specs || []).reduce((acc, s) => acc + (s.updated_files?.length || 0), 0);
                showToast(changed > 0 ? `Synced ${changed} spec file(s).` : "All spec checklists already in sync.");
                await refreshSnapshot({ force: true });
              } catch (err) {
                showToast(err instanceof Error ? err.message : "Sync failed");
              }
            },
          },
          "Sync"
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

    const remoteRepoInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "Open Remote Repo (e.g. owner/repo or https://github.com/owner/repo)...",
      value: state.remoteRepo || "",
    });

    const remoteCard = el(
      "section",
      { className: "card" },
      el(
        "div",
        { className: "card-header" },
        el(
          "div",
          {},
          el("h3", { className: "card-title" }, "Remote Repository Specs & Workspace Bundle Setup"),
          el("p", { className: "card-desc" }, "Read specs from any remote repository or audit & migrate the active workspace bundle.")
        )
      ),
      el(
        "div",
        { className: "search-bar", style: "margin-top:12px" },
        remoteRepoInput,
        el(
          "button",
          {
            className: "btn btn-primary",
            onClick: async () => {
              const target = remoteRepoInput.value.trim();
              if (!target) {
                state.remoteRepo = "";
                await refreshSnapshot({ force: true });
                return;
              }
              try {
                state.remoteRepo = target;
                state.tab = "roadmap";
                await refreshSnapshot({ force: true });
                showToast(`Loaded remote specs from ${target}`);
              } catch (err) {
                state.remoteRepo = "";
                showToast(err instanceof Error ? err.message : "Failed to load remote repository");
              }
            },
          },
          "Open Remote Repo"
        ),
        state.remoteRepo
          ? el(
              "button",
              {
                className: "btn btn-quiet",
                onClick: async () => {
                  state.remoteRepo = "";
                  await refreshSnapshot({ force: true });
                },
              },
              "Return to Local"
            )
          : null,
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              try {
                const audit = await host.api("/api/workspace-setup", {
                  workspacePath: state.workspacePath,
                  action: "audit",
                });
                state.setupAudit = audit;
                render();
              } catch (err) {
                showToast(err instanceof Error ? err.message : "Bundle audit failed");
              }
            },
          },
          "Audit Bundle Setup"
        ),
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              try {
                const res = await host.api("/api/workspace-setup", {
                  workspacePath: state.workspacePath,
                  action: "apply",
                  migrateSpecs: true,
                });
                state.setupAudit = res.audit || null;
                showToast(`Aligned bundle (${(res.actions || []).length} update(s)).`);
                await refreshSnapshot({ force: true });
              } catch (err) {
                showToast(err instanceof Error ? err.message : "Bundle migration failed");
              }
            },
          },
          "Align & Migrate Bundle"
        )
      ),
      state.setupAudit
        ? el(
            "div",
            { className: "truth-callout" },
            `Bundle: ${state.setupAudit.bundle_root} · Policy: ${state.setupAudit.ignore_policy} · Legacy paths: ${(state.setupAudit.legacy_paths || []).length} · Unaligned specs: ${(state.setupAudit.unaligned_specs || []).length}`
          )
        : null
    );

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
      remoteCard,
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

  function renderNowStrip(snap) {
    const live = snap?.live || {};
    const entries = Object.entries(live);
    const items = [];
    for (const [flowId, info] of entries) {
      if ((info.activeCount || 0) > 0 || (info.active_tasks || []).length > 0 || info.run_phase) {
        const phaseTxt = info.run_phase?.phase ? `phase=${info.run_phase.phase}` : "";
        const tasksTxt = (info.active_tasks || []).map((t) => t.task_id).join(", ");
        const leasesTxt = info.activeCount ? `${info.activeCount} worker${info.activeCount === 1 ? "" : "s"}` : "";
        const meta = [leasesTxt, phaseTxt, tasksTxt].filter(Boolean).join(" · ");
        items.push(el("span", { className: "pill pill-warn" }, `${flowId}${meta ? `: ${meta}` : ""}`));
      }
    }
    if (items.length === 0) return null;
    return el(
      "div",
      { className: "now-strip" },
      el("strong", {}, "Now"),
      el("div", { className: "now-strip-items" }, ...items)
    );
  }

  function renderRoadmapView() {
    const snap = state.snapshot;
    if (!snap) return el("div", { className: "subtle-meta" }, "Loading workspace...");
    const wrap = el("div", {});
    const nowStrip = renderNowStrip(snap);
    if (nowStrip) wrap.appendChild(nowStrip);
    wrap.appendChild(renderQuickPlanCard(false));

    const otherSpecs = Array.isArray(snap.otherBranchSpecs) ? snap.otherBranchSpecs : [];
    const branchBar = el(
      "div",
      { className: "search-bar", style: "margin-bottom:14px" },
      el(
        "div",
        { className: "segmented" },
        ...[
          { id: "current", label: `Current branch (${snap.specs.length})` },
          { id: "all", label: `All branches (${snap.specs.length + otherSpecs.length})` },
        ].map((opt) =>
          el(
            "button",
            {
              className: state.branchFilter === opt.id ? "active" : "",
              onClick: () => {
                state.branchFilter = opt.id;
                render();
              },
            },
            opt.label
          )
        )
      ),
      snap.currentBranch
        ? el("span", { className: "subtle-meta mono" }, `Branch: ${snap.currentBranch}`)
        : null
    );
    wrap.appendChild(branchBar);

    const visibleSpecs = state.branchFilter === "all" ? [...snap.specs, ...otherSpecs] : snap.specs;

    if (visibleSpecs.length === 0) {
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

    for (const spec of visibleSpecs) {
      const flowId = spec.flowId || spec.flow_id;
      const pct = spec.totalTasks > 0 ? Math.round((spec.completedTasks / spec.totalTasks) * 100) : 0;
      const isRemoteBranchSpec = spec.onCurrentBranch === false || spec.on_current_branch === false;
      const branchBadge = spec.branchName || spec.branch_name || spec.gitRef || spec.git_ref;
      const prNum = spec.prNumber || spec.pr_number;
      const specActionsMenu = el(
        "details",
        { className: "action-menu" },
        el("summary", { className: "btn btn-quiet" }, "⋯ Branch"),
        el(
          "div",
          { className: "action-menu-list" },
          !isRemoteBranchSpec && !state.remoteRepo
            ? el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "justify-content:flex-start",
                  onClick: async () => {
                    try {
                      const prRes = await host.api("/api/spec-pr", {
                        workspacePath: state.workspacePath,
                        flowId,
                        push: true,
                      });
                      showToast(prRes.pr_url ? `Opened Spec PR: ${prRes.pr_url}` : `Committed spec on branch ${prRes.branch || flowId}`);
                      await refreshSnapshot({ force: true });
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Failed to publish Spec PR");
                    }
                  },
                },
                "Publish Spec PR"
              )
            : null,
          !isRemoteBranchSpec && !state.remoteRepo
            ? el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "justify-content:flex-start",
                  onClick: async () => {
                    try {
                      const shareRes = await host.api("/api/spec-share-branch", {
                        workspacePath: state.workspacePath,
                        flowId,
                        push: false,
                      });
                      showToast(`Updated ${shareRes.branch || "flow-specs"} branch (${shareRes.synced_files?.length || 0} files)`);
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Failed to share on flow-specs");
                    }
                  },
                },
                "Share on flow-specs"
              )
            : null,
          isRemoteBranchSpec && !state.remoteRepo
            ? el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "justify-content:flex-start",
                  onClick: async () => {
                    try {
                      const pullRes = await host.api("/api/spec-pull", {
                        workspacePath: state.workspacePath,
                        flowId,
                        fromRef: spec.gitRef || spec.git_ref || branchBadge,
                      });
                      showToast(`Pulled ${flowId} (${pullRes.copied_files?.length || 0} files)`);
                      await refreshSnapshot({ force: true });
                    } catch (err) {
                      showToast(err instanceof Error ? err.message : "Pull spec failed");
                    }
                  },
                },
                "Pull Spec"
              )
            : null,
          spec.worktreePath || spec.worktree_path
            ? el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "justify-content:flex-start",
                  onClick: async () => {
                    state.workspacePath = spec.worktreePath || spec.worktree_path;
                    await refreshSnapshot({ force: true });
                  },
                },
                "Open Worktree"
              )
            : null
        )
      );

      const card = el(
        "section",
        { className: "card" },
        el(
          "div",
          { className: "card-header" },
          el(
            "div",
            {},
            el(
              "h3",
              { className: "card-title" },
              el("span", { className: `status-dot ${spec.state}` }),
              spec.title || flowId,
              branchBadge ? el("span", { className: "pill mono", style: "margin-left:8px" }, branchBadge) : null,
              prNum ? el("span", { className: "pill pill-ok", style: "margin-left:6px" }, `PR #${prNum}`) : null
            ),
            el("p", { className: "card-desc" }, spec.description || flowId)
          ),
          el(
            "div",
            { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" },
            spec.unresolvedComments > 0 ? el("span", { className: "pill pill-warn" }, `${spec.unresolvedComments} review notes`) : null,
            el(
              "button",
              {
                className: "btn",
                onClick: async () => {
                  state.tab = "review";
                  state.specSubView = "dag";
                  await loadDocument(spec.relPath, spec.gitRef || spec.git_ref || null);
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
                  await loadDocument(spec.relPath, spec.gitRef || spec.git_ref || null);
                  render();
                },
              },
              "Read Spec"
            ),
            specActionsMenu,
            !isRemoteBranchSpec && spec.recommendedAction
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

  function renderExternalSourcePill(src) {
    if (!src) return null;
    if (typeof src === "string") {
      const clean = src.trim();
      return clean ? el("span", { className: "pill" }, clean) : null;
    }
    if (typeof src !== "object" || Array.isArray(src)) return null;
    const label = String(src.label || src.kind || "External").trim();
    const title = String(src.title || src.fileId || "").trim();
    const text = title && title !== label ? `${label}: ${title}` : label;
    const rawUrl = typeof src.url === "string" ? src.url.trim() : "";
    if (/^https?:\/\//i.test(rawUrl)) {
      return el(
        "a",
        {
          className: "pill pill-link",
          href: rawUrl,
          target: "_blank",
          rel: "noopener noreferrer",
          title: rawUrl,
        },
        text
      );
    }
    return el("span", { className: "pill" }, text);
  }

  function renderDagView({ compactHeader = false } = {}) {
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

    const headerNodes = compactHeader
      ? [
          el(
            "div",
            { className: "dag-view-header-compact" },
            el("span", { className: "pill" }, `${dag.nodes.length} tasks · ${(dag.steps || []).length} steps`)
          ),
        ]
      : [
          el("h3", { className: "card-title" }, `Flow Tasks (${dag.nodes.length})`),
          el(
            "p",
            { className: "card-desc" },
            `Inline fast-path eligible: ${dag.inline_fast_path_eligible ? "yes" : "no"} · Total steps: ${(dag.steps || []).length}`
          ),
        ];

    return el(
      "div",
      {},
      el(
        "div",
        { className: "card" },
        ...headerNodes,
        el("div", { className: "dag-viewport", style: "margin-top:12px" }, svg),
        lanes
      )
    );
  }

  function commentUpvoteCount(c) {
    if (typeof c.upvoteCount === "number") return c.upvoteCount;
    if (Array.isArray(c.upvoterEmails)) return c.upvoterEmails.length;
    if (Array.isArray(c.upvotes)) return c.upvotes.length;
    return 0;
  }

  function isCommentResolved(c) {
    return Boolean(c.resolved || c.state === "resolved" || c.state === "addressed");
  }

  function openMediaLightbox({ src, mimeType = "", title = "" }) {
    if (!lightboxEl || !backdropEl) return;
    lightboxEl.textContent = "";
    lightboxEl.classList.remove("hidden");
    const isVideo = String(mimeType).startsWith("video/") || /\.(mp4|webm|mov)$/i.test(src || "");
    const mediaEl = isVideo
      ? el("video", { src, controls: true, autoplay: true })
      : el("img", { src, alt: title || "Media preview" });
    lightboxEl.append(
      mediaEl,
      title ? el("div", { className: "subtle-meta", style: "color:#fff" }, title) : null,
      el("button", { className: "btn", onClick: () => lightboxEl.classList.add("hidden") }, "Close Preview")
    );
    lightboxEl.onclick = (ev) => {
      if (ev.target === lightboxEl) lightboxEl.classList.add("hidden");
    };
  }

  function resolveRelativeAssetPath(baseRelPath, assetTarget) {
    const raw = String(assetTarget || "").trim();
    if (!raw || /^(https?:|data:|blob:)/i.test(raw)) return null;
    if (raw.startsWith("/")) return raw.slice(1);
    const dirParts = String(baseRelPath || "").split("/").slice(0, -1);
    for (const seg of raw.split("/")) {
      if (!seg || seg === ".") continue;
      if (seg === "..") dirParts.pop();
      else dirParts.push(seg);
    }
    return dirParts.join("/");
  }

  function appendInlineMarkdownNodes(parent, text, { baseRelPath, onOpenMedia }) {
    const src = String(text || "");
    const tokenRe = /(!?\[[^\]]*\]\([^)\s]+(?:\s+"[^"]*")?\)|`[^`\n]+`|\*\*[^*]+\*\*|~~[^~]+~~|\*[^*\n]+\*|\[\^[A-Za-z0-9_-]+\])/g;
    let lastIdx = 0;
    let match;
    while ((match = tokenRe.exec(src)) !== null) {
      if (match.index > lastIdx) {
        parent.appendChild(document.createTextNode(src.slice(lastIdx, match.index)));
      }
      const tok = match[0];
      if (tok.startsWith("![")) {
        const mImg = tok.match(/^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$/);
        if (mImg) {
          const [, alt, href] = mImg;
          const relAsset = resolveRelativeAssetPath(baseRelPath, href);
          if (relAsset && !state.remoteRepo) {
            const imgNode = el("img", { className: "md-media-thumb", alt: alt || relAsset });
            host
              .api("/api/workspace-asset", { workspacePath: state.workspacePath, relPath: relAsset })
              .then((res) => {
                if (!res?.dataBase64) return;
                if (String(res.mimeType || "").startsWith("video/")) {
                  const vid = el("video", {
                    className: "md-media-thumb",
                    controls: true,
                    src: `data:${res.mimeType};base64,${res.dataBase64}`,
                  });
                  vid.addEventListener("dblclick", () => onOpenMedia({ src: vid.src, mimeType: res.mimeType, title: alt || relAsset }));
                  imgNode.replaceWith(vid);
                } else {
                  imgNode.src = `data:${res.mimeType || "image/png"};base64,${res.dataBase64}`;
                  imgNode.addEventListener("click", () => onOpenMedia({ src: imgNode.src, mimeType: res.mimeType, title: alt || relAsset }));
                }
              })
              .catch(() => {
                imgNode.replaceWith(el("span", { className: "pill" }, `[media unavailable: ${relAsset}]`));
              });
            parent.appendChild(imgNode);
          } else {
            parent.appendChild(el("span", { className: "pill" }, `Image: ${alt || href}`));
          }
        }
      } else if (tok.startsWith("[^")) {
        const fnId = tok.slice(2, -1);
        const sup = el("sup", {}, el("a", { href: `#fn-${fnId}`, className: "mono" }, `[${fnId}]`));
        parent.appendChild(sup);
      } else if (tok.startsWith("[")) {
        const mLink = tok.match(/^\[([^\]]+)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$/);
        if (mLink) {
          const [, label, href] = mLink;
          if (/^https?:\/\//i.test(href)) {
            parent.appendChild(el("a", { href, target: "_blank", rel: "noopener noreferrer" }, label));
          } else {
            const targetRel = resolveRelativeAssetPath(baseRelPath, href.split("#")[0]);
            parent.appendChild(
              el(
                "button",
                {
                  className: "btn btn-quiet",
                  style: "padding:0 4px;font-size:inherit;display:inline",
                  title: targetRel || href,
                  onClick: async () => {
                    if (targetRel && targetRel.endsWith(".md")) {
                      await loadDocument(targetRel);
                      render();
                    }
                  },
                },
                label
              )
            );
          }
        }
      } else if (tok.startsWith("`")) {
        parent.appendChild(el("code", {}, tok.slice(1, -1)));
      } else if (tok.startsWith("**")) {
        const strong = el("strong", {});
        appendInlineMarkdownNodes(strong, tok.slice(2, -2), { baseRelPath, onOpenMedia });
        parent.appendChild(strong);
      } else if (tok.startsWith("~~")) {
        const del = el("del", {});
        appendInlineMarkdownNodes(del, tok.slice(2, -2), { baseRelPath, onOpenMedia });
        parent.appendChild(del);
      } else if (tok.startsWith("*")) {
        const em = el("em", {});
        appendInlineMarkdownNodes(em, tok.slice(1, -1), { baseRelPath, onOpenMedia });
        parent.appendChild(em);
      }
      lastIdx = match.index + tok.length;
    }
    if (lastIdx < src.length) {
      parent.appendChild(document.createTextNode(src.slice(lastIdx)));
    }
  }

  function renderMarkdownDom(markdownText, { comments = [], bodyStartLine = 1, baseRelPath = "", onOpenCommentModal, onOpenMedia }) {
    const rawLines = String(markdownText || "").split(/\r?\n/);
    const openByLine = new Map();
    for (const c of comments) {
      if (isCommentResolved(c)) continue;
      const lineNum = Number(c.startLine || 1);
      const arr = openByLine.get(lineNum) || [];
      arr.push(c);
      openByLine.set(lineNum, arr);
    }

    function commentsInRange(startL, endL) {
      const matched = [];
      for (const c of comments) {
        const s = Number(c.startLine || 1);
        const e = Number(c.endLine || s);
        if (s <= endL && e >= startL) matched.push(c);
      }
      return matched;
    }

    function wrapBlock(contentNode, startL, endL, quoteText) {
      const blockComments = commentsInRange(startL, endL);
      const openCount = blockComments.filter((c) => !isCommentResolved(c)).length;
      const gutterBtn = el(
        "button",
        {
          className: `md-block-gutter ${openCount > 0 ? "has-notes" : ""}`,
          title: `Lines ${startL}–${endL} (${blockComments.length} notes)`,
          onClick: (ev) => {
            ev.stopPropagation();
            onOpenCommentModal({ startLine: startL, endLine: endL, quote: quoteText });
          },
        },
        openCount > 0 ? String(openCount) : "+"
      );
      return el(
        "div",
        {
          className: "md-block",
          "data-start-line": String(startL),
          "data-end-line": String(endL),
        },
        gutterBtn,
        contentNode
      );
    }

    const container = el("div", { className: "md-reader" });
    let i = 0;
    while (i < rawLines.length) {
      const line = rawLines[i];
      if (!line.trim()) {
        i += 1;
        continue;
      }
      const blockStart = bodyStartLine + i;

      const fenceMatch = line.match(/^\s*(```|~~~)(.*)$/);
      if (fenceMatch) {
        const fence = fenceMatch[1];
        const lang = fenceMatch[2].trim();
        const codeLines = [];
        let j = i + 1;
        while (j < rawLines.length && !new RegExp(`^\\s*${fence}`).test(rawLines[j])) {
          codeLines.push(rawLines[j]);
          j += 1;
        }
        const blockEnd = bodyStartLine + Math.min(j, rawLines.length - 1);
        const codeText = codeLines.join("\n");
        const preEl = el("pre", {}, el("code", { className: lang ? `language-${lang}` : "" }, codeText));
        const wrapper = lang === "mermaid"
          ? el("div", {}, el("div", { className: "subtle-meta", style: "margin-bottom:4px" }, "Diagram (`mermaid`)"), preEl)
          : preEl;
        container.appendChild(wrapBlock(wrapper, blockStart, blockEnd, codeText.slice(0, 140)));
        i = j + 1;
        continue;
      }

      const hMatch = line.match(/^(#{1,4})\s+(.+?)\s*$/);
      if (hMatch) {
        const level = hMatch[1].length;
        const hEl = el(`h${level}`, { id: `sec-line-${blockStart}` });
        appendInlineMarkdownNodes(hEl, hMatch[2], { baseRelPath, onOpenMedia });
        container.appendChild(wrapBlock(hEl, blockStart, blockStart, hMatch[2]));
        i += 1;
        continue;
      }

      if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
        container.appendChild(wrapBlock(el("hr", {}), blockStart, blockStart, line));
        i += 1;
        continue;
      }

      if (/^\|.*\|/.test(line.trim()) && i + 1 < rawLines.length && /^\s*\|?[\s:-]+\|/.test(rawLines[i + 1])) {
        const splitRow = (row) =>
          row
            .trim()
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map((cell) => cell.trim());
        const headers = splitRow(line);
        let j = i + 2;
        const rows = [];
        while (j < rawLines.length && /^\|/.test(rawLines[j].trim())) {
          rows.push(splitRow(rawLines[j]));
          j += 1;
        }
        const thead = el("thead", {}, el("tr", {}, ...headers.map((h) => el("th", {}, h))));
        const tbody = el("tbody", {});
        for (const row of rows) {
          const tr = el("tr", {});
          for (let c = 0; c < headers.length; c += 1) {
            const td = el("td", {});
            appendInlineMarkdownNodes(td, row[c] || "", { baseRelPath, onOpenMedia });
            tr.appendChild(td);
          }
          tbody.appendChild(tr);
        }
        const tbl = el("div", { className: "md-table-wrap" }, el("table", { className: "md-table" }, thead, tbody));
        container.appendChild(wrapBlock(tbl, blockStart, bodyStartLine + j - 1, headers.join(" | ")));
        i = j;
        continue;
      }

      if (/^\s*>/.test(line)) {
        const qLines = [];
        let j = i;
        while (j < rawLines.length && /^\s*>/.test(rawLines[j])) {
          qLines.push(rawLines[j].replace(/^\s*>\s?/, ""));
          j += 1;
        }
        const firstLine = qLines[0] || "";
        const calloutMatch = firstLine.match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/i);
        const kindCls = calloutMatch ? calloutMatch[1].toLowerCase() : "";
        const calloutEl = el("div", { className: `md-callout ${kindCls}` });
        if (calloutMatch) {
          calloutEl.appendChild(el("strong", {}, `${calloutMatch[1]} `));
          const bodyLines = [calloutMatch[2], ...qLines.slice(1)].filter(Boolean);
          appendInlineMarkdownNodes(calloutEl, bodyLines.join("\n"), { baseRelPath, onOpenMedia });
        } else {
          appendInlineMarkdownNodes(calloutEl, qLines.join("\n"), { baseRelPath, onOpenMedia });
        }
        container.appendChild(wrapBlock(calloutEl, blockStart, bodyStartLine + j - 1, qLines[0] || ""));
        i = j;
        continue;
      }

      if (/^\s*(?:[-*+]|\d+\.)\s+/.test(line)) {
        const ordered = /^\s*\d+\./.test(line);
        const listEl = el(ordered ? "ol" : "ul", { style: "margin:4px 0;padding-left:20px" });
        let j = i;
        while (j < rawLines.length && /^\s*(?:[-*+]|\d+\.)\s+/.test(rawLines[j])) {
          const itemText = rawLines[j].replace(/^\s*(?:[-*+]|\d+\.)\s+/, "");
          const taskMatch = itemText.match(/^\[([ xX~!>-])\]\s*(.*)$/);
          const li = el("li", { style: "margin:3px 0" });
          if (taskMatch) {
            const mark = taskMatch[1].toLowerCase();
            li.appendChild(el("span", { className: "mono", style: "margin-right:6px" }, `[${mark}]`));
            appendInlineMarkdownNodes(li, taskMatch[2], { baseRelPath, onOpenMedia });
          } else {
            appendInlineMarkdownNodes(li, itemText, { baseRelPath, onOpenMedia });
          }
          listEl.appendChild(li);
          j += 1;
        }
        container.appendChild(wrapBlock(listEl, blockStart, bodyStartLine + j - 1, rawLines[i]));
        i = j;
        continue;
      }

      const fnDef = line.match(/^\[\^([A-Za-z0-9_-]+)\]:\s*(.+)$/);
      if (fnDef) {
        const p = el("div", { className: "subtle-meta mono", id: `fn-${fnDef[1]}` });
        appendInlineMarkdownNodes(p, `[^${fnDef[1]}]: ${fnDef[2]}`, { baseRelPath, onOpenMedia });
        container.appendChild(wrapBlock(p, blockStart, blockStart, fnDef[0]));
        i += 1;
        continue;
      }

      const pLines = [];
      let j = i;
      while (
        j < rawLines.length &&
        rawLines[j].trim() &&
        !/^(#{1,4}\s|```|~~~|\s*>|\s*(?:[-*+]|\d+\.)\s|\s*([-*_])\1{2,}\s*$|\[\^)/.test(rawLines[j]) &&
        !/^\|.*\|/.test(rawLines[j].trim())
      ) {
        pLines.push(rawLines[j]);
        j += 1;
      }
      const pEl = el("p", { style: "margin:2px 0" });
      appendInlineMarkdownNodes(pEl, pLines.join(" "), { baseRelPath, onOpenMedia });
      container.appendChild(wrapBlock(pEl, blockStart, bodyStartLine + j - 1, pLines[0] || ""));
      i = j;
    }
    return container;
  }

  function ensureFloatGutter() {
    if (!floatGutterEl) {
      floatGutterEl = el("button", { className: "md-float-gutter hidden", type: "button" }, "+ Add comment");
      document.body.appendChild(floatGutterEl);
    }
    return floatGutterEl;
  }

  function attachFloatSelectionGutter(readerEl, onOpenModal) {
    const gutter = ensureFloatGutter();
    gutter.classList.add("hidden");
    readerEl.addEventListener("mouseup", () => {
      const sel = window.getSelection();
      const text = sel ? sel.toString().trim() : "";
      if (!text || sel.rangeCount === 0) {
        gutter.classList.add("hidden");
        return;
      }
      const range = sel.getRangeAt(0);
      const startEl = range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement;
      const endEl = range.endContainer.nodeType === 1 ? range.endContainer : range.endContainer.parentElement;
      const startBlock = startEl?.closest?.("[data-start-line]");
      const endBlock = endEl?.closest?.("[data-end-line]") || startBlock;
      if (!startBlock) {
        gutter.classList.add("hidden");
        return;
      }
      const startLine = Number(startBlock.getAttribute("data-start-line") || 1);
      const endLine = Number(endBlock?.getAttribute("data-end-line") || startLine);
      const rect = range.getBoundingClientRect();
      gutter.style.top = `${Math.max(12, rect.top - 36)}px`;
      gutter.style.left = `${Math.max(12, Math.min(window.innerWidth - 150, rect.left))}px`;
      gutter.classList.remove("hidden");
      gutter.onclick = () => {
        gutter.classList.add("hidden");
        onOpenModal({ startLine, endLine, quote: text.slice(0, 220) });
      };
    });
  }

  function openCommentModal({ startLine, endLine, quote = "" }) {
    if (!commentModalEl || !backdropEl) return;
    state.activeCommentRange = { startLine, endLine: endLine || startLine, quote };
    renderCommentModalContents();
    backdropEl.classList.remove("hidden");
    commentModalEl.classList.remove("hidden");
  }

  function renderCommentModalContents() {
    if (!commentModalEl) return;
    commentModalEl.textContent = "";
    const range = state.activeCommentRange || { startLine: 1, endLine: 1, quote: "" };
    const allComments = state.currentDoc?.comments || [];
    const matching = allComments.filter((c) => {
      const cs = Number(c.startLine || 1);
      const ce = Number(c.endLine || cs);
      return cs <= range.endLine && ce >= range.startLine;
    });
    const listPool = matching.length > 0 ? matching : allComments;
    const filtered = listPool.filter((c) => {
      if (state.commentFilter === "open") return !isCommentResolved(c);
      if (state.commentFilter === "addressed") return isCommentResolved(c);
      return true;
    });

    const repliesByParent = new Map();
    const topLevel = [];
    for (const c of filtered) {
      if (c.parentCommentId) {
        const arr = repliesByParent.get(c.parentCommentId) || [];
        arr.push(c);
        repliesByParent.set(c.parentCommentId, arr);
      } else {
        topLevel.push(c);
      }
    }

    const filterSeg = el(
      "div",
      { className: "segmented" },
      ...[
        { id: "all", label: `All (${listPool.length})` },
        { id: "open", label: `Open (${listPool.filter((c) => !isCommentResolved(c)).length})` },
        { id: "addressed", label: `Addressed (${listPool.filter((c) => isCommentResolved(c)).length})` },
      ].map((f) =>
        el(
          "button",
          {
            className: state.commentFilter === f.id ? "active" : "",
            onClick: () => {
              state.commentFilter = f.id;
              renderCommentModalContents();
            },
          },
          f.label
        )
      )
    );

    commentModalEl.append(
      el(
        "div",
        { className: "card-header" },
        el(
          "div",
          {},
          el("h3", { className: "card-title" }, `Review Notes · Lines ${range.startLine}–${range.endLine}`),
          el("div", { className: "subtle-meta mono" }, state.selectedDocRelPath || "")
        ),
        el("button", { className: "btn btn-quiet", onClick: closeDrawers }, "Close")
      ),
      range.quote ? el("div", { className: "comment-quote" }, range.quote) : null,
      el("div", { className: "search-bar", style: "margin-bottom:4px" }, filterSeg)
    );

    for (const c of topLevel) {
      const kindLabel = c.commentKind || "feedback";
      const resolved = isCommentResolved(c);
      const thread = el("div", { className: "comment-thread" });
      thread.appendChild(
        el(
          "div",
          { style: "display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px" },
          el(
            "div",
            { style: "display:flex;gap:6px;align-items:center;flex-wrap:wrap" },
            el("strong", { style: "font-size:12px" }, `L${c.startLine}`),
            el("span", { className: `comment-chip ${kindLabel === "change_request" ? "blocker" : ""}` }, kindLabel),
            resolved ? el("span", { className: "pill pill-ok" }, "addressed") : null,
            c.ghPrCommentId ? el("span", { className: "pill" }, `PR #${c.ghPrCommentId}`) : null,
            renderExternalSourcePill(c.externalSource),
            c.authorName ? el("span", { className: "subtle-meta" }, c.authorName) : null
          ),
          el(
            "div",
            { style: "display:flex;gap:4px;align-items:center" },
            el(
              "button",
              {
                className: "btn btn-quiet",
                style: "padding:2px 7px;font-size:12px",
                onClick: async () => {
                  await host.api("/api/review-comments", {
                    action: "update",
                    workspacePath: state.workspacePath,
                    relPath: state.selectedDocRelPath,
                    commentId: c.id,
                    toggleUpvote: true,
                    repoLocator: state.remoteRepo || undefined,
                  });
                  await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
                  renderCommentModalContents();
                },
              },
              `▲ ${commentUpvoteCount(c)}`
            ),
            el(
              "button",
              {
                className: "btn btn-quiet",
                style: "padding:2px 7px;font-size:12px",
                onClick: () => {
                  state.editingCommentId = state.editingCommentId === c.id ? null : c.id;
                  renderCommentModalContents();
                },
              },
              "Edit"
            ),
            el(
              "button",
              {
                className: "btn btn-quiet",
                style: "padding:2px 7px;font-size:12px",
                onClick: () => {
                  state.replyingCommentId = state.replyingCommentId === c.id ? null : c.id;
                  renderCommentModalContents();
                },
              },
              "Reply"
            ),
            el(
              "button",
              {
                className: "btn btn-quiet",
                style: "padding:2px 7px;font-size:12px",
                onClick: async () => {
                  await host.api("/api/review-comments", {
                    action: "update",
                    workspacePath: state.workspacePath,
                    relPath: state.selectedDocRelPath,
                    commentId: c.id,
                    resolved: !resolved,
                    repoLocator: state.remoteRepo || undefined,
                  });
                  await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
                  renderCommentModalContents();
                  render();
                },
              },
              resolved ? "Reopen" : "Resolve"
            )
          )
        )
      );

      if (state.editingCommentId === c.id) {
        const editTa = el("textarea", { className: "textarea-input", rows: 2, style: "width:100%", value: c.body });
        editTa.value = c.body;
        thread.append(
          editTa,
          el(
            "div",
            { style: "display:flex;gap:6px;justify-content:flex-end;margin-top:6px" },
            el("button", { className: "btn btn-quiet", onClick: () => { state.editingCommentId = null; renderCommentModalContents(); } }, "Cancel"),
            el(
              "button",
              {
                className: "btn btn-primary",
                onClick: async () => {
                  const nextBody = editTa.value.trim();
                  if (!nextBody) return;
                  await host.api("/api/review-comments", {
                    action: "edit",
                    workspacePath: state.workspacePath,
                    relPath: state.selectedDocRelPath,
                    commentId: c.id,
                    body: nextBody,
                    repoLocator: state.remoteRepo || undefined,
                  });
                  state.editingCommentId = null;
                  await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
                  renderCommentModalContents();
                  render();
                },
              },
              "Save Edit"
            )
          )
        );
      } else {
        thread.appendChild(el("div", {}, c.body));
      }

      for (const rep of repliesByParent.get(c.id) || []) {
        thread.appendChild(
          el(
            "div",
            { className: "comment-reply" },
            el("div", { className: "subtle-meta" }, rep.authorName || rep.authorEmail || "Reviewer"),
            el("div", {}, rep.body)
          )
        );
      }

      if (state.replyingCommentId === c.id) {
        const repTa = el("textarea", { className: "textarea-input", rows: 2, placeholder: "Write reply...", style: "width:100%;margin-top:8px" });
        thread.append(
          repTa,
          el(
            "div",
            { style: "display:flex;gap:6px;justify-content:flex-end;margin-top:6px" },
            el("button", { className: "btn btn-quiet", onClick: () => { state.replyingCommentId = null; renderCommentModalContents(); } }, "Cancel"),
            el(
              "button",
              {
                className: "btn btn-primary",
                onClick: async () => {
                  const repBody = repTa.value.trim();
                  if (!repBody) return;
                  await host.api("/api/review-comments", {
                    action: "reply",
                    workspacePath: state.workspacePath,
                    relPath: state.selectedDocRelPath,
                    parentCommentId: c.id,
                    body: repBody,
                    repoLocator: state.remoteRepo || undefined,
                  });
                  state.replyingCommentId = null;
                  await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
                  renderCommentModalContents();
                  render();
                },
              },
              "Post Reply"
            )
          )
        );
      }
      commentModalEl.appendChild(thread);
    }

    const kindSel = el(
      "select",
      {
        className: "select-input",
        onChange: (e) => {
          state.activeCommentKind = e.target.value;
        },
      },
      ...["feedback", "change_request", "question", "approval"].map((k) =>
        el("option", { value: k, selected: state.activeCommentKind === k }, k)
      )
    );
    const bodyTa = el("textarea", {
      className: "textarea-input",
      rows: 3,
      placeholder: "Add spec review feedback (Ctrl/Cmd+Enter to save)...",
      style: "width:100%",
    });
    const submitNew = async () => {
      const body = bodyTa.value.trim();
      if (!body) return;
      await host.api("/api/review-comments", {
        action: "add",
        workspacePath: state.workspacePath,
        relPath: state.selectedDocRelPath,
        startLine: range.startLine,
        endLine: range.endLine,
        quote: range.quote,
        commentKind: kindSel.value,
        body,
        gitBranch: state.selectedDocGitRef || state.snapshot?.currentBranch || undefined,
        repoLocator: state.remoteRepo || undefined,
      });
      await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
      renderCommentModalContents();
      render();
    };
    bodyTa.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        submitNew();
      }
    });
    commentModalEl.append(
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "New Note Kind"), kindSel, bodyTa),
      el(
        "div",
        { style: "display:flex;gap:8px;justify-content:flex-end" },
        el("button", { className: "btn btn-primary", onClick: submitNew }, "Save Feedback")
      )
    );
  }

  function renderSpecReviewView() {
    const snap = state.snapshot;
    const allDocs = [];
    for (const s of [...(snap?.specs || []), ...(snap?.otherBranchSpecs || [])]) {
      const suffix = s.onCurrentBranch === false && (s.branchName || s.gitRef) ? ` [${s.branchName || s.gitRef}]` : "";
      allDocs.push({ label: `Spec · ${s.title}${suffix}`, relPath: s.relPath, gitRef: s.gitRef || null });
      for (const ch of s.chapters || []) {
        if (ch.relPath) allDocs.push({ label: `  ↳ ${ch.chapterId}${suffix}`, relPath: ch.relPath, gitRef: s.gitRef || null });
      }
    }
    for (const k of snap?.knowledge || []) {
      allDocs.push({ label: `${k.type} · ${k.title}`, relPath: k.relPath, gitRef: null });
    }

    const docPicker = el(
      "select",
      {
        className: "select-input",
        style: "min-width:260px",
        onChange: async (e) => {
          const picked = allDocs.find((d) => `${d.relPath}::${d.gitRef || ""}` === e.target.value) || {
            relPath: e.target.value,
            gitRef: null,
          };
          await loadDocument(picked.relPath, picked.gitRef);
          render();
        },
      },
      ...allDocs.map((d) =>
        el(
          "option",
          {
            value: `${d.relPath}::${d.gitRef || ""}`,
            selected: d.relPath === state.selectedDocRelPath && (d.gitRef || null) === (state.selectedDocGitRef || null),
          },
          d.label
        )
      )
    );

    const subViewToggle = el(
      "div",
      { className: "segmented" },
      ...[
        { id: "document", label: "Reader" },
        { id: "source", label: "Source" },
        { id: "dag", label: "Graph" },
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

    const openComments = (state.currentDoc?.comments || []).filter((c) => !isCommentResolved(c));
    const reviewSummaryBadge = state.specReviewSummary
      ? el(
          "span",
          { className: `pill ${openComments.length > 0 ? "pill-warn" : "pill-ok"}` },
          `${state.specReviewSummary.reviewState || "draft"} · ${openComments.length} open`
        )
      : null;

    const actionMenuItems = [];
    if (state.selectedDocRelPath && !state.selectedDocGitRef && !state.remoteRepo) {
      actionMenuItems.push(
        el(
          "button",
          {
            className: "btn btn-quiet action-menu-item",
            type: "button",
            onClick: () => host.openFile(state.workspacePath, state.selectedDocRelPath, 1),
          },
          "Open in Editor"
        )
      );
    }
    if (openComments.length > 0 && state.revisePrompt) {
      actionMenuItems.push(
        el(
          "button",
          {
            className: "btn btn-quiet action-menu-item",
            type: "button",
            onClick: () => runFlowAction(state.revisePrompt, "Revise Specification"),
          },
          `Dispatch /flow:revise (${openComments.length})`
        )
      );
    }
    const overflowMenu =
      actionMenuItems.length > 0
        ? el(
            "details",
            { className: "action-menu" },
            el("summary", { className: "btn", title: "Document actions", "aria-label": "Document actions" }, "⋯"),
            el("div", { className: "action-menu-list" }, ...actionMenuItems)
          )
        : null;

    const toolbar = el(
      "div",
      { className: "doc-topbar" },
      el("div", { className: "doc-topbar-left" }, docPicker, reviewSummaryBadge),
      el(
        "div",
        { className: "doc-topbar-right" },
        subViewToggle,
        el(
          "button",
          {
            className: "btn",
            type: "button",
            onClick: () => openCommentModal({ startLine: 1, endLine: 1, quote: "" }),
          },
          `Notes (${(state.currentDoc?.comments || []).length})`
        ),
        overflowMenu
      )
    );

    const siblings = Array.isArray(state.currentDoc?.siblings) ? state.currentDoc.siblings : [];
    const siblingsStrip =
      siblings.length > 1
        ? el(
            "div",
            { className: "doc-meta-strip" },
            el(
              "div",
              { className: "doc-siblings-strip" },
              ...siblings.map((sib) =>
                el(
                  "button",
                  {
                    className: `btn doc-sibling-btn ${sib.active ? "btn-primary" : "btn-quiet"}`,
                    type: "button",
                    title: sib.rel_path,
                    onClick: async () => {
                      await loadDocument(sib.rel_path, state.selectedDocGitRef);
                      render();
                    },
                  },
                  sib.label
                )
              )
            )
          )
        : null;

    const syncWarnBanner = state.specReviewSummary?.syncWarning
      ? el("div", { className: "md-callout warning", style: "margin-bottom:10px" }, state.specReviewSummary.syncWarning)
      : null;

    if (state.specSubView === "dag") {
      return el("div", {}, toolbar, siblingsStrip, syncWarnBanner, renderDagView({ compactHeader: true }));
    }

    if (!state.currentDoc) {
      return el("div", {}, toolbar, el("div", { className: "subtle-meta" }, "Select a document to review."));
    }

    if (state.specSubView === "document") {
      const headings = state.currentDoc.headings || [];
      const outlineBar =
        headings.length > 0
          ? el(
              "details",
              { className: "md-outline-bar" },
              el("summary", { className: "md-outline-summary" }, `Sections (${headings.length})`),
              el(
                "div",
                { className: "md-outline-chips" },
                ...headings.slice(0, 16).map((h) =>
                  el(
                    "button",
                    {
                      className: "md-outline-chip",
                      type: "button",
                      onClick: () => {
                        const target = document.getElementById(`sec-line-${h.line}`);
                        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
                      },
                    },
                    h.text
                  )
                )
              )
            )
          : null;

      const readerEl = renderMarkdownDom(state.currentDoc.markdown || state.currentDoc.raw || "", {
        comments: state.currentDoc.comments || [],
        bodyStartLine: Number(state.currentDoc.body_start_line || (state.currentDoc.frontmatterEndLine || 0) + 1),
        baseRelPath: state.selectedDocRelPath || "",
        onOpenCommentModal: openCommentModal,
        onOpenMedia: openMediaLightbox,
      });
      attachFloatSelectionGutter(readerEl, openCommentModal);
      return el("div", {}, toolbar, siblingsStrip, syncWarnBanner, outlineBar, readerEl);
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
      if (isCommentResolved(c)) continue;
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
        const upvotes = commentUpvoteCount(c);
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
                el("span", { className: `comment-chip ${kindLabel === "change_request" ? "blocker" : ""}` }, kindLabel),
                c.ghPrCommentId ? el("span", { className: "pill" }, `PR #${c.ghPrCommentId}`) : null,
                renderExternalSourcePill(c.externalSource),
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
                      await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
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
                      await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
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
          ...["feedback", "change_request", "question", "approval"].map((k) =>
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
                    await loadDocument(state.selectedDocRelPath, state.selectedDocGitRef);
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

    return el("div", {}, toolbar, siblingsStrip, syncWarnBanner, el("div", { className: "reader-layout" }, outline, linesBox));
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
  setInterval(() => {
    if (document.hidden || isOverlayOpen() || hasOpenDetailsIn(rootEl)) return;
    const sel = window.getSelection();
    if (sel && sel.toString().trim()) return;
    refreshSnapshot({ force: false }).catch(() => {});
  }, 5000);
})();
