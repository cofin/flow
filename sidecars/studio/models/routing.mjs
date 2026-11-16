/**
 * System-One Decision Engine (`builtin`, `/v1/systemone`, `gemini-decision-1`, `onnx`)
 * paired with continuous multi-objective `(model, effort)` utility scoring and
 * Upward Frontier Delegation floor enforcement.
 */

const DELEGATED_UPWARD_KINDS = new Set([
  "planning",
  "semantic_validation",
  "spec_review",
  "committee",
  "adversarial",
  "diagnosis",
]);

const FRONTIER_CAPABILITY_FLOOR = 0.8;

/**
 * Evaluate execution lane, complexity rubric, validation need, and replan signals
 * without generating chat prose (`0` output tokens).
 */
export class DecisionEngine {
  /**
   * @param {{ provider?: string, endpoint?: string, fetchImpl?: typeof fetch, env?: NodeJS.ProcessEnv }} [options]
   */
  constructor({ provider = "builtin", endpoint = "", fetchImpl = globalThis.fetch, env = process.env } = {}) {
    this.provider = String(provider || "builtin").toLowerCase();
    this.endpoint = String(endpoint || "").trim();
    this.fetchImpl = typeof fetchImpl === "function" ? fetchImpl : null;
    this.env = env;
  }

  /**
   * Evaluate routing signals for a slice or workflow task.
   *
   * @param {{
   *   taskKind?: string,
   *   filesCount?: number,
   *   estimatedLoc?: number,
   *   failedAttempts?: number,
   *   risk?: "low" | "normal" | "high",
   *   hasHighRiskSurface?: boolean,
   *   complexity?: number | null,
   * }} input
   */
  async evaluate(input = {}) {
    const taskKind = String(input.taskKind || "implementation").toLowerCase();
    const filesCount = Number(input.filesCount ?? 1);
    const estLoc = Number(input.estimatedLoc ?? 80);
    const failedAttempts = Number(input.failedAttempts ?? 0);
    const isHighRisk = input.risk === "high" || Boolean(input.hasHighRiskSurface);

    if (this.provider === "systemone-http" && this.endpoint && this.fetchImpl) {
      try {
        const res = await this.fetchImpl(this.endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            questions: [
              {
                name: "execution_lane",
                kind: "choice",
                options: ["inline_fast_path", "single_worker", "wave_pipeline", "small_swarm"],
                context: { taskKind, filesCount, estLoc, failedAttempts, isHighRisk },
              },
              { name: "complexity_rubric", kind: "score", min: 0, max: 4 },
              { name: "should_replan", kind: "noul" },
              { name: "needs_adversarial", kind: "noul" },
              { name: "needs_frontier_validation", kind: "noul" },
            ],
          }),
          signal: AbortSignal.timeout(2500),
        });
        if (res.ok) {
          const data = await res.json();
          const ans = data?.answers || data;
          if (ans?.execution_lane && Number.isFinite(Number(ans.complexity_rubric))) {
            const conf = Number(ans.confidence ?? 0.9);
            const rawScore = Number(ans.complexity_rubric);
            const effectiveScore = conf < 0.65 ? Math.min(4, rawScore + 0.75) : rawScore;
            return {
              provider: "systemone-http",
              confidence: conf,
              execution_lane: String(ans.execution_lane),
              complexity_rubric: effectiveScore,
              demand: Number((0.25 + 0.18 * effectiveScore).toFixed(4)),
              should_replan: Boolean(ans.should_replan),
              needs_adversarial: Boolean(ans.needs_adversarial),
              needs_frontier_validation: Boolean(ans.needs_frontier_validation),
            };
          }
        }
      } catch {
        // Fall back seamlessly to builtin evaluator on network or endpoint failure.
      }
    }

    let executionLane = "wave_pipeline";
    if (filesCount <= 5 && estLoc <= 300 && !isHighRisk && taskKind === "implementation") {
      executionLane = filesCount <= 2 && estLoc <= 120 ? "inline_fast_path" : "single_worker";
    } else if (filesCount > 3 && !isHighRisk) {
      executionLane = "small_swarm";
    }

    let complexityScore = Number.isFinite(Number(input.complexity)) ? Number(input.complexity) : 1.6;
    if (!Number.isFinite(Number(input.complexity))) {
      if (DELEGATED_UPWARD_KINDS.has(taskKind)) complexityScore = 3.5;
      else if (taskKind === "narrow_fetch" || taskKind === "sync") complexityScore = 0.4;
      else if (taskKind === "research") complexityScore = 2.4;
      else complexityScore = Math.min(4, 1.0 + (estLoc / 250) * 1.4 + (isHighRisk ? 1.2 : 0));
    }
    if (failedAttempts >= 1) complexityScore = Math.min(4, complexityScore + failedAttempts * 0.6);

    const demand = DELEGATED_UPWARD_KINDS.has(taskKind)
      ? Math.max(0.86, Math.min(1, 0.25 + 0.18 * complexityScore))
      : Math.max(0.15, Math.min(1, 0.22 + 0.19 * complexityScore));

    return {
      provider: "builtin",
      confidence: 0.92,
      execution_lane: executionLane,
      complexity_rubric: Number(complexityScore.toFixed(2)),
      demand: Number(demand.toFixed(4)),
      should_replan: failedAttempts >= 3,
      needs_adversarial: isHighRisk || complexityScore >= 3.0,
      needs_frontier_validation: isHighRisk || DELEGATED_UPWARD_KINDS.has(taskKind) || failedAttempts >= 2 || complexityScore >= 3.0,
    };
  }
}

/**
 * Multi-objective continuous `(model, effort)` selector across discovered harness inventories.
 */
export class AdaptiveModelRouter {
  /**
   * @param {{ decisionEngine?: DecisionEngine }} [options]
   */
  constructor({ decisionEngine = null } = {}) {
    this.decisionEngine = decisionEngine || new DecisionEngine();
  }

  /**
   * Rank all eligible `(model, effort)` candidates for a task descriptor and enforce
   * upward capability floors for delegated deep-reasoning kinds.
   *
   * @param {any[]} candidates
   * @param {{
   *   taskKind?: string,
   *   complexity?: number | null,
   *   risk?: "low" | "normal" | "high",
   *   authorVendor?: string | null,
   *   requireVendorDiversity?: boolean,
   *   compiledPromptTokens?: number,
   *   quotaFloorFraction?: number,
   *   demandOverride?: number | null,
   * }} [task]
   */
  select(candidates, task = {}) {
    const taskKind = String(task.taskKind || "implementation").toLowerCase();
    const isUpwardDelegated = DELEGATED_UPWARD_KINDS.has(taskKind) || task.risk === "high";
    const requiredContext = Math.max(4000, Math.round((Number(task.compiledPromptTokens) || 4000) * 2.5));
    const quotaFloor = Number(task.quotaFloorFraction ?? (taskKind === "adversarial" ? 0.2 : 0.25));

    let demand = Number.isFinite(Number(task.demandOverride))
      ? Number(task.demandOverride)
      : isUpwardDelegated
        ? 0.92
        : taskKind === "sync" || taskKind === "narrow_fetch"
          ? 0.25
          : Math.max(0.4, Math.min(0.85, 0.35 + (Number(task.complexity ?? 1.8) / 4) * 0.45));

    const eligible = (candidates || []).filter(
      (c) =>
        c &&
        c.tool_call !== false &&
        Number(c.live_availability ?? 1) > 0 &&
        Number(c.context_window ?? 128000) >= requiredContext,
    );

    if (eligible.length === 0) {
      return {
        model: null,
        effort: isUpwardDelegated ? "xhigh" : taskKind === "sync" ? "low" : "medium",
        tier: isUpwardDelegated ? "frontier" : taskKind === "sync" ? "light" : "balanced",
        degraded: true,
        degraded_reason: "No eligible tool-calling models found in harness inventory.",
        fallback_chain: [],
      };
    }

    const healthyPool = eligible.filter((c) => Number(c.live_availability) >= quotaFloor);
    const activePool = healthyPool.length > 0 ? healthyPool : eligible;

    const minAvail = activePool.reduce((m, c) => Math.min(m, Number(c.live_availability)), 1);
    const costWeight = minAvail < 0.35 ? 0.45 : isUpwardDelegated ? 0.05 : 0.22;
    const speedWeight = isUpwardDelegated ? 0.05 : taskKind === "sync" || taskKind === "narrow_fetch" ? 0.4 : 0.18;
    const diversityBonus = task.requireVendorDiversity || taskKind === "adversarial" ? 0.35 : 0;

    const scored = activePool.map((c) => {
      const cap = Number(c.capability_index ?? 0.5);
      const underCapPenalty = cap < demand ? 1.8 * (demand - cap) : 0.22 * (cap - demand);
      const fit = 1 - Math.min(1, underCapPenalty);
      const quotaScore = Number(c.live_availability ?? 1);
      const pricePenalty = costWeight * Number(c.price_index ?? 0.5);
      const latencyPenalty = speedWeight * Number(c.latency_index ?? 0.3);
      const divGain =
        diversityBonus > 0 && task.authorVendor && c.vendor && c.vendor !== task.authorVendor ? diversityBonus : 0;
      const priorityGain = Math.min(0.1, Number(c.fallback_priority || 0) * 0.002);
      const utility = 0.65 * fit + 0.3 * quotaScore - pricePenalty - latencyPenalty + divGain + priorityGain;
      return { candidate: c, utility };
    });

    scored.sort((a, b) => b.utility - a.utility || b.candidate.capability_index - a.candidate.capability_index);
    const winner = scored[0].candidate;
    const degraded = isUpwardDelegated && Number(winner.capability_index) < FRONTIER_CAPABILITY_FLOOR;

    const fallbackChain = [];
    const seenPairs = new Set();
    for (const item of scored) {
      const pairKey = `${item.candidate.model}::${item.candidate.effort}`;
      if (seenPairs.has(pairKey)) continue;
      seenPairs.add(pairKey);
      fallbackChain.push({
        model: item.candidate.model,
        runtime_target: item.candidate.runtime_target,
        effort: item.candidate.effort,
        vendor: item.candidate.vendor,
        capability_index: item.candidate.capability_index,
        utility: Number(item.utility.toFixed(4)),
      });
    }

    const tier =
      Number(winner.capability_index) >= 0.8
        ? "frontier"
        : Number(winner.capability_index) >= 0.58
          ? "balanced"
          : Number(winner.capability_index) >= 0.36
            ? "fast"
            : "light";

    return {
      harness: winner.harness,
      model: winner.model,
      runtime_target: winner.runtime_target,
      display_name: winner.display_name,
      effort: winner.effort,
      vendor: winner.vendor,
      tier,
      utility: Number(scored[0].utility.toFixed(4)),
      capability_index: winner.capability_index,
      quota_fraction: winner.quota_fraction,
      degraded,
      degraded_reason: degraded
        ? `Selected model capability (${winner.capability_index}) is below frontier floor (${FRONTIER_CAPABILITY_FLOOR}).`
        : null,
      fallback_chain: fallbackChain.slice(0, 6),
    };
  }

  /**
   * Synchronous convenience resolution over pre-normalized candidates.
   *
   * @param {any[]} candidates
   * @param {Record<string, any>} options
   */
  route(candidates, options = {}) {
    return this.select(candidates, options);
  }
}
