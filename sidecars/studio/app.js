/**
 * Calm, low-noise Flow Studio frontend (`Roadmap`, `Spec & Review`,
 * `Knowledge Catalog`, and `Activity & Hooks` + compact `AuxPane` Companion).
 *
 * Uses safe DOM node creation (`createElement` + `textContent`) throughout.
 */
(function initFlowStudioApp() {
  const host = window.flowHost;
  const rootEl = document.getElementById("studio-root");
  const drawerEl = document.getElementById("new-spec-drawer");
  const backdropEl = document.getElementById("drawer-backdrop");
  const toastRegion = document.getElementById("toast-region");

  const urlParams = new URLSearchParams(window.location.search);
  const forcedTheme = urlParams.get("theme");
  if (forcedTheme === "light" || forcedTheme === "dark") {
    document.documentElement.setAttribute("data-theme", forcedTheme);
  }

  const state = {
    tab: urlParams.get("tab") || "roadmap",
    workspacePath: "",
    workspaces: [],
    snapshot: null,
    selectedDocRelPath: null,
    currentDoc: null,
    activeCommentLine: null,
    revisePrompt: "",
    catalogQuery: "",
    catalogMode: "hybrid",
    catalogHits: [],
    catalogStatus: null,
    provenanceQuery: "",
    provenanceHits: [],
    driftReport: null,
    harnesses: [],
    writerGuard: null,
    harnessRuns: [],
    selectedHarness: "host",
    executionMode: "direct-workspace",
    modelsQuota: null,
  };

  /**
   * Helper to construct DOM nodes cleanly without unsafe HTML string interpolation.
   *
   * @param {string} tag
   * @param {Record<string, any>} [attrs]
   * @param {...(Node | string | null | undefined)} children
   */
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

  function showToast(message) {
    if (!toastRegion) return;
    const item = el("div", { className: "toast" }, message);
    toastRegion.appendChild(item);
    setTimeout(() => item.remove(), 4200);
  }

  async function bootstrap() {
    try {
      const initialUri = host.getInitialWorkspaceUri();
      const ctx = await host.api(
        "/api/studio-context",
        initialUri ? { workspaceUri: initialUri } : {}
      );
      state.workspacePath = ctx.defaultWorkspace;
      state.workspaces = ctx.workspaces || [ctx.defaultWorkspace];
      state.harnesses = ctx.harnesses || [];
      await refreshSnapshot();
    } catch (err) {
      showToast(err instanceof Error ? err.message : "Failed to load Studio context");
      render();
    }
  }

  async function refreshSnapshot() {
    if (!state.workspacePath) return;
    state.snapshot = await host.api("/api/bundle-snapshot", {
      workspacePath: state.workspacePath,
      registerWorkspace: true,
    });
    if (!state.selectedDocRelPath && state.snapshot.specs.length > 0) {
      state.selectedDocRelPath = state.snapshot.specs[0].relPath;
    }
    if (state.tab === "review" && state.selectedDocRelPath) {
      await loadDocument(state.selectedDocRelPath);
    } else if (state.tab === "catalog") {
      await refreshCatalog();
    } else if (state.tab === "activity") {
      await refreshActivity();
    }
    render();
  }

  async function loadDocument(relPath) {
    state.selectedDocRelPath = relPath;
    state.currentDoc = await host.api("/api/spec-document", {
      workspacePath: state.workspacePath,
      relPath,
    });
    const commentRes = await host.api("/api/review-comments", {
      action: "list",
      workspacePath: state.workspacePath,
      relPath,
    });
    state.revisePrompt = commentRes.revisePrompt || "";
  }

  async function refreshCatalog() {
    const statusRes = await host.api("/api/catalog-status", { workspacePath: state.workspacePath });
    state.catalogStatus = statusRes.status;
    if (state.catalogQuery.trim()) {
      const res = await host.api("/api/catalog-search", {
        workspacePath: state.workspacePath,
        query: state.catalogQuery,
        mode: state.catalogMode,
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
    const [hRes, mRes] = await Promise.all([
      host.api("/api/harnesses", { workspacePath: state.workspacePath }),
      host.api("/api/models-and-quota", { workspacePath: state.workspacePath }),
    ]);
    state.harnesses = hRes.harnesses || [];
    state.writerGuard = hRes.writerGuard || null;
    state.harnessRuns = hRes.runs || [];
    state.modelsQuota = mRes;
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

  function render() {
    if (!rootEl) return;
    rootEl.textContent = "";

    if (host.isCompanionView) {
      rootEl.className = "studio-shell companion-mode";
      rootEl.appendChild(renderCompanionView());
      return;
    }

    rootEl.className = "studio-shell";
    rootEl.appendChild(renderTopBar());
    rootEl.appendChild(renderTabsBar());

    if (state.tab === "roadmap") rootEl.appendChild(renderRoadmapView());
    else if (state.tab === "review") rootEl.appendChild(renderSpecReviewView());
    else if (state.tab === "catalog") rootEl.appendChild(renderCatalogView());
    else if (state.tab === "activity") rootEl.appendChild(renderActivityView());
  }

  function renderCompanionView() {
    const snap = state.snapshot;
    const activeSpec =
      snap?.specs?.find((s) => s.flowId === snap.activeFlowId) || snap?.specs?.[0] || null;

    const logoSrc = window.__FLOW_LOGO_URI__ || "/logo.svg";
    const header = el(
      "div",
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
            el("span", { className: "brand-badge" }, "Companion")
          ),
          el(
            "div",
            { className: "subtle-meta" },
            snap?.python ? `${snap.repoName || "Workspace"} · ${snap.python.manager}` : snap?.repoName || "OKF v0.2"
          )
        )
      ),
      el(
        "button",
        { className: "btn", onClick: () => host.openFullStudio() },
        "Open Studio"
      )
    );

    const container = el("div", {}, header);
    if (!activeSpec) {
      container.appendChild(
        el(
          "div",
          { className: "card" },
          el("h3", { className: "card-title" }, "No active specification"),
          el("p", { className: "card-desc" }, "Create a Feature Spec or Master PRD to track chapters and tasks."),
          el(
            "div",
            { className: "progress-row" },
            el("button", { className: "btn btn-primary", onClick: () => openNewSpecDrawer() }, "+ New Spec")
          )
        )
      );
      return container;
    }

    const pct =
      activeSpec.totalTasks > 0
        ? Math.round((activeSpec.completedTasks / activeSpec.totalTasks) * 100)
        : 0;

    container.appendChild(
      el(
        "div",
        { className: "card", style: "margin-top:16px" },
        el("h3", { className: "card-title" }, activeSpec.title),
        el("p", { className: "card-desc" }, activeSpec.description || activeSpec.flowId),
        el(
          "div",
          { className: "progress-row" },
          el(
            "div",
            { className: "progress-track" },
            el("div", {
              className: `progress-fill ${pct === 100 ? "done" : ""}`,
              style: `width:${pct}%`,
            })
          ),
          el("span", { className: "subtle-meta" }, `${activeSpec.completedTasks}/${activeSpec.totalTasks} tasks`)
        ),
        activeSpec.recommendedAction
          ? el(
              "div",
              { style: "margin-top:14px;display:flex;gap:8px" },
              el(
                "button",
                {
                  className: "btn btn-primary",
                  onClick: () =>
                    runFlowAction(activeSpec.recommendedAction.command, activeSpec.recommendedAction.label),
                },
                activeSpec.recommendedAction.label
              )
            )
          : null
      )
    );

    const touchedTruth = (snap?.knowledge || []).filter((k) => k.truthBlock).slice(0, 2);
    for (const item of touchedTruth) {
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

  function renderTopBar() {
    const snap = state.snapshot;
    const wsSelect = el(
      "select",
      {
        className: "select-input",
        "aria-label": "Active workspace",
        onChange: async (e) => {
          state.workspacePath = e.target.value;
          state.selectedDocRelPath = null;
          await refreshSnapshot();
        },
      },
      ...state.workspaces.map((ws) =>
        el("option", { value: ws, selected: ws === state.workspacePath }, ws.split("/").pop() || ws)
      )
    );

    const pyBadge = snap?.python
      ? el(
          "span",
          { className: "pill", title: `Runner: ${snap.python.runPrefix.join(" ")}` },
          `${snap.python.manager}${snap.python.entrypoints.length ? ` · ${snap.python.entrypoints.length} cli` : ""}`
        )
      : null;

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
        pyBadge,
        wsSelect,
        el(
          "button",
          { className: "btn btn-quiet", onClick: () => refreshSnapshot() },
          "Refresh"
        ),
        el(
          "button",
          { className: "btn btn-primary", onClick: () => openNewSpecDrawer() },
          "+ New Spec"
        )
      )
    );
  }

  function renderTabsBar() {
    const tabs = [
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
              if (t.id === "review" && state.selectedDocRelPath) {
                await loadDocument(state.selectedDocRelPath);
              } else if (t.id === "catalog") {
                await refreshCatalog();
              } else if (t.id === "activity") {
                await refreshActivity();
              }
              render();
            },
          },
          t.label
        )
      )
    );
  }

  function renderRoadmapView() {
    const snap = state.snapshot;
    if (!snap) return el("div", { className: "subtle-meta" }, "Loading workspace...");

    const wrap = el("div", {});
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
            el(
              "h3",
              { className: "card-title" },
              el("span", { className: `status-dot ${spec.state}` }),
              spec.title
            ),
            el("p", { className: "card-desc" }, spec.description || spec.flowId)
          ),
          el(
            "div",
            { style: "display:flex;gap:8px;align-items:center" },
            spec.unresolvedComments > 0
              ? el("span", { className: "pill pill-warn" }, `${spec.unresolvedComments} review notes`)
              : null,
            el(
              "button",
              {
                className: "btn",
                onClick: async () => {
                  state.tab = "review";
                  await loadDocument(spec.relPath);
                  render();
                },
              },
              "Read & Review"
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
          el(
            "div",
            { className: "progress-track" },
            el("div", {
              className: `progress-fill ${pct === 100 ? "done" : ""}`,
              style: `width:${pct}%`,
            })
          ),
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
                        onClick: () =>
                          runFlowAction(`/flow:implement ${spec.flowId} ${ch.chapterId}`, `Implement ${ch.chapterId}`),
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
        style: "min-width:280px",
        onChange: async (e) => {
          await loadDocument(e.target.value);
          render();
        },
      },
      ...allDocs.map((d) =>
        el("option", { value: d.relPath, selected: d.relPath === state.selectedDocRelPath }, d.label)
      )
    );

    const openComments = (state.currentDoc?.comments || []).filter((c) => !c.resolved);
    const toolbar = el(
      "div",
      { className: "search-bar" },
      docPicker,
      state.selectedDocRelPath
        ? el(
            "button",
            {
              className: "btn",
              onClick: () => host.openFile(state.workspacePath, state.selectedDocRelPath, 1),
            },
            "Open in Editor"
          )
        : null,
      openComments.length > 0
        ? el(
            "button",
            {
              className: "btn btn-primary",
              onClick: () => runFlowAction(state.revisePrompt, "Revise Specification"),
            },
            `Dispatch /flow:revise (${openComments.length})`
          )
        : el("span", { className: "subtle-meta" }, "Click any line number to attach a review note.")
    );

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
      if (c.resolved) continue;
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
              title: "Add inline review comment",
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
        linesBox.appendChild(
          el(
            "div",
            { className: "inline-comment-box" },
            el(
              "div",
              { style: "display:flex;justify-content:space-between;align-items:center;margin-bottom:4px" },
              el("strong", { style: "font-size:12px" }, `Line ${c.startLine}`),
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
            ),
            el("div", {}, c.body)
          )
        );
      }

      if (state.activeCommentLine === ln.lineNumber) {
        const inputEl = el("textarea", {
          className: "textarea-input",
          rows: 2,
          placeholder: "Describe requested spec refinement...",
          style: "width:100%;margin-bottom:8px",
        });
        linesBox.appendChild(
          el(
            "div",
            { className: "inline-comment-box" },
            inputEl,
            el(
              "div",
              { style: "display:flex;gap:8px;justify-content:flex-end" },
              el(
                "button",
                {
                  className: "btn btn-quiet",
                  onClick: () => {
                    state.activeCommentLine = null;
                    render();
                  },
                },
                "Cancel"
              ),
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
                      body,
                    });
                    state.activeCommentLine = null;
                    await loadDocument(state.selectedDocRelPath);
                    await refreshSnapshot();
                  },
                },
                "Save Note"
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
      placeholder: "Search OKF concepts, truth blocks, and specs (press / to focus)...",
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
      ...["hybrid", "bm25", "semantic"].map((m) =>
        el(
          "button",
          {
            className: state.catalogMode === m ? "active" : "",
            onClick: async () => {
              state.catalogMode = m;
              await refreshCatalog();
              render();
            },
          },
          m === "hybrid" ? "Hybrid RRF" : m === "bm25" ? "BM25" : "Semantic"
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
            showToast("Synchronized DuckDB catalog from Markdown bundles.");
            render();
          },
        },
        "Re-index DuckDB"
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
          `DuckDB Catalog · ${state.catalogStatus.entry_count} entries · Embedder: ${state.catalogStatus.embedder_model} (${state.catalogStatus.embedding_dim}d)`
        )
      : null;

    const resultsWrap = el("div", {});
    if (state.driftReport) {
      const brokenCount =
        (state.driftReport.broken_links?.length || 0) +
        (state.driftReport.missing_sources?.length || 0);
      resultsWrap.appendChild(
        el(
          "div",
          { className: "card" },
          el(
            "h3",
            { className: "card-title" },
            brokenCount === 0
              ? "Zero citation or link drift detected"
              : `${brokenCount} citation / link drift issues`
          ),
          ...[
            ...(state.driftReport.broken_links || []),
            ...(state.driftReport.missing_sources || []),
          ].map((issue) =>
            el(
              "div",
              { className: "subtle-meta mono", style: "margin-top:6px" },
              `${issue.rel_path} → ${issue.target} (${issue.issue_kind})`
            )
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
              el("div", { className: "subtle-meta" }, `${hit.concept_type} · ${hit.concept_id}`)
            ),
            el(
              "div",
              { style: "display:flex;gap:8px;align-items:center" },
              el(
                "span",
                { className: `pill ${hit.trust_tier === "human-reviewed" ? "pill-ok" : ""}` },
                hit.trust_tier
              ),
              el(
                "button",
                {
                  className: "btn btn-quiet",
                  onClick: async () => {
                    state.tab = "review";
                    await loadDocument(hit.rel_path);
                    render();
                  },
                },
                "Open"
              )
            )
          ),
          hit.description ? el("p", { className: "card-desc" }, hit.description) : null,
          hit.truth_block ? el("div", { className: "truth-callout" }, hit.truth_block) : null
        )
      );
    }

    return el("div", {}, searchRow, statusLine, resultsWrap);
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
      ...installedHarnesses.map((h) =>
        el("option", { value: h.id, selected: state.selectedHarness === h.id }, `${h.label} (${h.binary})`)
      )
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
      el("h3", { className: "card-title" }, "Cross-Harness & A2A Execution Bridge"),
      el(
        "p",
        { className: "card-desc" },
        "Route planning, implementation, or read-only zero-context reviews to any installed harness CLI. Toggle Execution Mode freely between direct workspace writes, isolated Git worktrees, and read-only sandboxes."
      ),
      state.writerGuard?.activeWriter
        ? el(
            "div",
            { className: "truth-callout", style: "border-left-color:var(--warn)" },
            `Advisory: ${state.writerGuard.reason} Consider Isolated Worktree or Read-Only if running concurrently.`
          )
        : null,
      el(
        "div",
        { className: "search-bar", style: "margin-top:14px" },
        harnessPicker,
        modeToggle
      ),
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
        )
      )
    );

    const pyInfo = state.snapshot?.python;
    const pyCard = el(
      "section",
      { className: "card" },
      el("h3", { className: "card-title" }, "Detected Python Environment & Entrypoints"),
      el(
        "p",
        { className: "card-desc" },
        pyInfo
          ? `Manager: ${pyInfo.manager} (${pyInfo.reason}) · Run prefix: ${pyInfo.runPrefix.join(" ")}`
          : "No Python project metadata detected."
      ),
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
                el(
                  "div",
                  {},
                  el("strong", {}, `${r.label} · ${r.executionMode}`),
                  el("div", { className: "subtle-meta mono" }, r.prompt)
                ),
                el("span", { className: `pill ${r.status === "completed" ? "pill-ok" : ""}` }, r.status)
              )
            )
          )
    );

    return el("div", {}, bridgeCard, el("div", { className: "grid-two" }, pyCard, runsCard));
  }

  function openNewSpecDrawer() {
    if (!drawerEl || !backdropEl) return;
    drawerEl.textContent = "";
    backdropEl.classList.remove("hidden");
    drawerEl.classList.remove("hidden");

    const kindSelect = el(
      "select",
      { className: "select-input" },
      el("option", { value: "Spec" }, "Feature Specification (/flow:plan)"),
      el("option", { value: "PRD" }, "Master PRD (/flow:prd)")
    );
    const slugInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "e.g. multi-region-failover",
    });
    const titleInput = el("input", {
      type: "text",
      className: "text-input",
      placeholder: "Human-readable title",
    });
    const problemInput = el("textarea", {
      className: "textarea-input",
      rows: 4,
      placeholder: "Problem framing, constraints, and target user outcomes...",
    });
    const chaptersCheck = el("input", { type: "checkbox", checked: true });

    const closeDrawer = () => {
      backdropEl.classList.add("hidden");
      drawerEl.classList.add("hidden");
    };
    backdropEl.onclick = closeDrawer;

    drawerEl.append(
      el(
        "div",
        { style: "display:flex;justify-content:space-between;align-items:center" },
        el("h3", { className: "card-title" }, "New Specification"),
        el("button", { className: "btn btn-quiet", onClick: closeDrawer }, "Close")
      ),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Type"), kindSelect),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Slug (flow_id)"), slugInput),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Title"), titleInput),
      el("div", { className: "field-group" }, el("label", { className: "field-label" }, "Problem & Context"), problemInput),
      el(
        "label",
        { style: "display:flex;gap:8px;align-items:center;font-size:13px" },
        chaptersCheck,
        "Scaffold chaptered layout (chapters/ch01-foundation)"
      ),
      el(
        "div",
        { style: "display:flex;gap:10px;margin-top:8px" },
        el(
          "button",
          {
            className: "btn",
            onClick: async () => {
              const created = await host.api("/api/create-spec", {
                workspacePath: state.workspacePath,
                kind: kindSelect.value,
                flowId: slugInput.value,
                title: titleInput.value,
                problem: problemInput.value,
                hasChapters: chaptersCheck.checked,
              });
              closeDrawer();
              state.selectedDocRelPath = created.relPath;
              state.tab = "review";
              await refreshSnapshot();
              showToast(`Created ${created.relPath}`);
            },
          },
          "Create Draft Only"
        ),
        el(
          "button",
          {
            className: "btn btn-primary",
            onClick: async () => {
              const created = await host.api("/api/create-spec", {
                workspacePath: state.workspacePath,
                kind: kindSelect.value,
                flowId: slugInput.value,
                title: titleInput.value,
                problem: problemInput.value,
                hasChapters: chaptersCheck.checked,
              });
              closeDrawer();
              await refreshSnapshot();
              await runFlowAction(created.dispatchCommand, `Plan ${created.flowId}`);
            },
          },
          "Create & Co-Plan with Agent"
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
      }
    } else if (e.key === "Escape") {
      backdropEl?.classList.add("hidden");
      drawerEl?.classList.add("hidden");
    }
  });

  host.onEvent(async (evt) => {
    if (evt?.type === "bundle.changed" || evt?.type === "workspace.changed") {
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
