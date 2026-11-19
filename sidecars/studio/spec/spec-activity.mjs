/**
 * @fileoverview Event-driven spec activity recorder, run-phase store, and
 * 5–10 minute periodic worksheet status checkpoint tracker (`SpecActivity`).
 */

import fs from "node:fs";
import path from "node:path";

import { FrontmatterDocument } from "../core/frontmatter.mjs";
import {
  isClosedState,
  readJsonSafe,
  readTextSafe,
  runtimeBaseDir,
  sha256Hex,
  StudioStateStore,
  workspaceRuntimeId,
  writeJsonAtomic,
} from "../core/fs-io.mjs";
import { containedPath, readSetupConfig, resolveWorktreeContext } from "../core/worktree.mjs";

export const ACTIVE_TASK_TTL_MS = 10 * 60 * 1000;
export const RUN_PHASE_TTL_MS = 30 * 60 * 1000;
export const CHECKPOINT_COOLDOWN_MS = 5 * 60 * 1000;
export const CHECKPOINT_PERIODIC_MS = 10 * 60 * 1000;
export const CHECKPOINT_MULTI_TASK_COUNT = 3;
export const VALID_SPEC_PHASES = new Set(["workers", "check", "commit", "sync", "idle"]);

function normalizeRelRepoPath(rawPath) {
  return String(rawPath || "")
    .split("::")[0]
    .split(":")[0]
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\.\//, "")
    .replace(/^\/+/, "");
}

function sanitizeIdSegment(rawId, fallback = "default") {
  return String(rawId || "").trim().replace(/[^A-Za-z0-9._-]/g, "_") || fallback;
}

function defaultNowMs(env = process.env) {
  const raw = env?.FLOW_TEST_NOW_MS;
  if (raw !== undefined && raw !== null && String(raw).trim() !== "" && Number.isFinite(Number(raw))) {
    return Number(raw);
  }
  return Date.now();
}

function toIsoNoMillis(ms) {
  return new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
}

function canonicalRealPath(targetPath) {
  const resolved = path.resolve(String(targetPath || ""));
  try {
    return fs.realpathSync(resolved);
  } catch {
    return resolved;
  }
}

/**
 * Tracks live task file-edit overlays, workflow phases, and 5–10 minute status checkpoints.
 */
export class SpecActivity {
  static resolveActivityDir(effectiveRoot, env = process.env) {
    return path.join(runtimeBaseDir(env), workspaceRuntimeId(canonicalRealPath(effectiveRoot)), "activity");
  }

  static resolvePhaseDir(effectiveRoot, env = process.env) {
    return path.join(runtimeBaseDir(env), workspaceRuntimeId(canonicalRealPath(effectiveRoot)), "run");
  }

  static resolveCheckpointDir(env = process.env) {
    return path.join(StudioStateStore.resolveConfigDir(env), "spec-sync-due");
  }

  static findOwningWorkspace(filePath) {
    if (!filePath || typeof filePath !== "string") return "";
    let cur = path.resolve(filePath);
    try {
      if (fs.existsSync(cur) && !fs.statSync(cur).isDirectory()) cur = path.resolve(cur, "..");
    } catch {
      cur = path.resolve(cur, "..");
    }
    for (let depth = 0; depth < 8; depth += 1) {
      if (fs.existsSync(path.join(cur, ".agents", "bundles", "specs"))) return cur;
      const parent = path.resolve(cur, "..");
      if (parent === cur) break;
      cur = parent;
    }
    return "";
  }

  static recordEdit({
    workspace,
    conversationId,
    parentConversationId = null,
    filePath,
    tool = "edit_file",
    isWorker = false,
    env = process.env,
    nowMs = defaultNowMs(env),
  } = {}) {
    const convId = String(conversationId || "").trim();
    if (!filePath || !convId) return { recorded: false };

    let candidateWs = workspace && String(workspace).trim() ? String(workspace).trim() : "";
    let resolvedRoot = candidateWs ? resolveWorktreeContext(candidateWs) : null;
    const absTarget = path.resolve(filePath);

    const relFitsRoot = (rootPair) => {
      if (!rootPair) return "";
      const relEff = path.relative(rootPair.effectiveRoot, absTarget);
      const relWt =
        rootPair.projectDir !== rootPair.effectiveRoot ? path.relative(rootPair.projectDir, absTarget) : relEff;
      if (!relEff.startsWith("..") && !path.isAbsolute(relEff)) return relEff;
      if (!relWt.startsWith("..") && !path.isAbsolute(relWt)) return relWt;
      return "";
    };

    let chosenRel = relFitsRoot(resolvedRoot);
    if (!chosenRel) {
      const owning = SpecActivity.findOwningWorkspace(filePath);
      if (owning) {
        candidateWs = owning;
        resolvedRoot = resolveWorktreeContext(owning);
        chosenRel = relFitsRoot(resolvedRoot);
      }
    }
    if (!candidateWs || !resolvedRoot || !chosenRel) return { recorded: false };

    const { effectiveRoot } = resolvedRoot;
    const setup = readSetupConfig(effectiveRoot);
    const specsDir = containedPath(effectiveRoot, path.join(setup.bundle_root, "specs"));
    if (!specsDir || !fs.existsSync(specsDir)) return { recorded: false };

    const relPosix = normalizeRelRepoPath(chosenRel);
    const nowIso = toIsoNoMillis(nowMs);
    const bundleSpecsPrefix = `${setup.bundle_root.replace(/\\/g, "/")}/specs/`;
    if (relPosix.startsWith(bundleSpecsPrefix)) {
      const rest = relPosix.slice(bundleSpecsPrefix.length);
      const flowId = rest.split("/")[0] || "";
      if (flowId) {
        let taskId = null;
        if (/(?:^|\/)tasks\/[^/]+\.md$/i.test(rest) && fs.existsSync(absTarget)) {
          const tDoc = FrontmatterDocument.parse(readTextSafe(absTarget) || "");
          const rawId = tDoc.text("id");
          if (rawId) taskId = rawId.includes(":") ? rawId : `${flowId}:${rawId}`;
        }
        SpecActivity.acknowledgeTasks(effectiveRoot, flowId, taskId ? [taskId] : null, {
          conversationId: taskId ? null : convId,
          nowMs,
          env,
        });
      }
      return { recorded: false, acknowledged: Boolean(flowId) };
    }

    const matches = SpecActivity.#matchPathToOpenTasks(specsDir, relPosix);
    if (matches.length === 0) return { recorded: false };

    const safeConv = sanitizeIdSegment(convId);
    const actDir = SpecActivity.resolveActivityDir(effectiveRoot, env);
    const actFile = path.join(actDir, `${safeConv}.json`);
    const prev = readJsonSafe(actFile);
    const record = prev && typeof prev === "object"
      ? prev
      : {
          v: 1,
          conversation_id: convId,
          parent_conversation_id: parentConversationId || null,
          is_worker: Boolean(isWorker),
          workspace: effectiveRoot,
          started_at: nowIso,
          last_at: nowIso,
          last_path: relPosix,
          tool,
          active: true,
          touched_paths: [],
          flows: {},
        };

    record.last_at = nowIso;
    record.last_path = relPosix;
    record.tool = tool;
    record.active = true;
    const touched = new Set(Array.isArray(record.touched_paths) ? record.touched_paths : []);
    touched.add(relPosix);
    record.touched_paths = [...touched].slice(-50);

    const certain = matches.length === 1;
    const touchedFlows = new Set();
    for (const m of matches) {
      if (!record.flows[m.flow_id]) {
        record.flows[m.flow_id] = { unrecorded_tasks: [], tasks: {} };
      }
      const flowEntry = record.flows[m.flow_id];
      const prevTask = flowEntry.tasks[m.task_id];
      flowEntry.tasks[m.task_id] = {
        started_at: prevTask?.started_at || nowIso,
        last_at: nowIso,
        last_path: relPosix,
        certain: Boolean(prevTask?.certain || certain),
      };
      if (!flowEntry.unrecorded_tasks.includes(m.task_id)) {
        flowEntry.unrecorded_tasks.push(m.task_id);
      }
      touchedFlows.add(m.flow_id);
    }

    writeJsonAtomic(actFile, record, 2);

    // Check 5-min multi-task or 10-min ongoing checkpoint threshold.
    SpecActivity.#maybeMarkCheckpointDue(effectiveRoot, record, touchedFlows, { nowMs, env });
    return { recorded: true, matches: matches.map((m) => m.task_id), certain };
  }

  static setPhase(workspaceRoot, flowId, { phase, detail = null, env = process.env, nowMs = defaultNowMs(env) } = {}) {
    const cleanPhase = String(phase || "").trim().toLowerCase();
    if (!VALID_SPEC_PHASES.has(cleanPhase)) {
      throw new Error(`Invalid phase '${phase}'. Expected one of: ${[...VALID_SPEC_PHASES].join(", ")}.`);
    }
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const phaseDir = SpecActivity.resolvePhaseDir(effectiveRoot, env);
    const target = path.join(phaseDir, `${sanitizeIdSegment(flowId)}.json`);
    const payload = {
      v: 1,
      flow_id: flowId,
      phase: cleanPhase,
      detail: detail ? String(detail).trim() : null,
      updated_at: toIsoNoMillis(nowMs),
      updated_ms: nowMs,
    };
    writeJsonAtomic(target, payload, 2);
    return payload;
  }

  static acknowledgeTasks(workspaceRoot, flowId, taskIds = null, { conversationId = null, env = process.env, nowMs = defaultNowMs(env) } = {}) {
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const actDir = SpecActivity.resolveActivityDir(effectiveRoot, env);
    if (!fs.existsSync(actDir)) return;
    const clearSet = Array.isArray(taskIds) && taskIds.length > 0 ? new Set(taskIds) : null;
    const safeTarget = conversationId ? sanitizeIdSegment(conversationId) : null;

    for (const fname of fs.readdirSync(actDir)) {
      if (!fname.endsWith(".json")) continue;
      if (safeTarget && fname !== `${safeTarget}.json`) continue;
      const full = path.join(actDir, fname);
      const data = readJsonSafe(full);
      const flowEntry = data?.flows?.[flowId];
      if (!flowEntry || !Array.isArray(flowEntry.unrecorded_tasks)) continue;
      flowEntry.unrecorded_tasks = clearSet
        ? flowEntry.unrecorded_tasks.filter((id) => !clearSet.has(id))
        : [];
      writeJsonAtomic(full, data, 2);
    }

    const dueFile = path.join(SpecActivity.resolveCheckpointDir(env), `${sanitizeIdSegment(effectiveRoot)}__${sanitizeIdSegment(flowId)}.json`);
    if (fs.existsSync(dueFile)) {
      const due = readJsonSafe(dueFile);
      if (due) {
        due.due = false;
        due.last_synced_ms = nowMs;
        writeJsonAtomic(dueFile, due, 2);
      }
    }
  }

  static finishTurn(workspaceRoot, conversationId, { env = process.env, nowMs = defaultNowMs(env) } = {}) {
    if (!conversationId) return;
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const actFile = path.join(SpecActivity.resolveActivityDir(effectiveRoot, env), `${sanitizeIdSegment(conversationId)}.json`);
    const data = readJsonSafe(actFile);
    if (!data) return;
    data.active = false;
    data.last_at = toIsoNoMillis(nowMs);
    writeJsonAtomic(actFile, data, 2);
  }

  static clearConversation(workspaceRoot, conversationId, { env = process.env } = {}) {
    if (!conversationId) return;
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const actFile = path.join(SpecActivity.resolveActivityDir(effectiveRoot, env), `${sanitizeIdSegment(conversationId)}.json`);
    if (fs.existsSync(actFile)) {
      try {
        fs.unlinkSync(actFile);
      } catch {
        // Ignore concurrent cleanup.
      }
    }
  }

  static consumeSyncDue(workspaceRoot, { env = process.env, nowMs = defaultNowMs(env) } = {}) {
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const dueDir = SpecActivity.resolveCheckpointDir(env);
    if (!fs.existsSync(dueDir)) return [];
    const prefix = `${sanitizeIdSegment(effectiveRoot)}__`;
    const dueFlows = [];
    for (const fname of fs.readdirSync(dueDir)) {
      if (!fname.startsWith(prefix) || !fname.endsWith(".json")) continue;
      const full = path.join(dueDir, fname);
      const data = readJsonSafe(full);
      if (!data?.due) continue;
      if (data.last_notified_ms && nowMs - data.last_notified_ms < CHECKPOINT_COOLDOWN_MS) continue;
      data.last_notified_ms = nowMs;
      data.due = false;
      writeJsonAtomic(full, data, 2);
      dueFlows.push(data.flow_id);
    }
    return dueFlows;
  }

  static freshLeaseConversations(workspaceRoot, { env = process.env, nowSec = Math.floor(Date.now() / 1000) } = {}) {
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const leaseDir = path.join(runtimeBaseDir(env), workspaceRuntimeId(canonicalRealPath(effectiveRoot)), "subagents");
    const altLeaseDir = path.join(runtimeBaseDir(env), workspaceRuntimeId(effectiveRoot), "subagents");
    const active = new Set();
    for (const dir of [...new Set([leaseDir, altLeaseDir])]) {
      if (!fs.existsSync(dir)) continue;
      for (const fname of fs.readdirSync(dir)) {
        if (!fname.endsWith(".lease")) continue;
        const lines = (readTextSafe(path.join(dir, fname)) || "").split(/\r?\n/);
        const epoch = Number(lines[0]);
        if (!Number.isFinite(epoch) || nowSec - epoch > 900) continue;
        try {
          const meta = lines[1] ? JSON.parse(lines[1]) : {};
          if (meta.conversation_id) active.add(String(meta.conversation_id));
        } catch {
          // Ignore invalid JSON line.
        }
      }
    }
    return active;
  }

  static isClaimLive(claimedBy, freshConversations) {
    const cleanClaim = String(claimedBy || "").trim();
    if (!cleanClaim || !(freshConversations instanceof Set) || freshConversations.size === 0) return false;
    for (const conv of freshConversations) {
      if (
        cleanClaim === conv ||
        cleanClaim.startsWith(`${conv}:`) ||
        cleanClaim.endsWith(`:${conv}`) ||
        cleanClaim.includes(`:${conv}:`)
      ) {
        return true;
      }
    }
    return false;
  }

  static overlay(workspaceRoot, { env = process.env, nowMs = defaultNowMs(env), prune = true } = {}) {
    const { effectiveRoot } = resolveWorktreeContext(workspaceRoot);
    const flows = {};

    const phaseDir = SpecActivity.resolvePhaseDir(effectiveRoot, env);
    if (fs.existsSync(phaseDir)) {
      for (const fname of fs.readdirSync(phaseDir).filter((f) => f.endsWith(".json"))) {
        const pData = readJsonSafe(path.join(phaseDir, fname));
        if (!pData?.flow_id) continue;
        if (nowMs - (pData.updated_ms || 0) > RUN_PHASE_TTL_MS) {
          if (prune) {
            try {
              fs.unlinkSync(path.join(phaseDir, fname));
            } catch {
              // Ignore concurrent cleanup.
            }
          }
          continue;
        }
        flows[pData.flow_id] = {
          phase: pData.phase || "idle",
          phase_detail: pData.detail || null,
          phase_since: pData.updated_at || null,
          tasks: {},
        };
      }
    }

    const actDir = SpecActivity.resolveActivityDir(effectiveRoot, env);
    if (fs.existsSync(actDir)) {
      for (const fname of fs.readdirSync(actDir).filter((f) => f.endsWith(".json"))) {
        const full = path.join(actDir, fname);
        const rec = readJsonSafe(full);
        if (!rec || !rec.flows) continue;
        const lastMs = Date.parse(rec.last_at || "") || 0;
        const expired = nowMs - lastMs > ACTIVE_TASK_TTL_MS;
        if (expired) {
          if (prune) {
            try {
              fs.unlinkSync(full);
            } catch {
              // Ignore cleanup failures.
            }
          }
          continue;
        }
        for (const [flowId, flowInfo] of Object.entries(rec.flows)) {
          if (!flows[flowId]) {
            flows[flowId] = { phase: "idle", phase_detail: null, phase_since: null, tasks: {} };
          }
          for (const [taskId, tInfo] of Object.entries(flowInfo?.tasks || {})) {
            const tLastMs = Date.parse(tInfo.last_at || "") || 0;
            if (nowMs - tLastMs > ACTIVE_TASK_TTL_MS) continue;
            flows[flowId].tasks[taskId] = {
              conversation_id: rec.conversation_id,
              started_at: tInfo.started_at,
              last_at: tInfo.last_at,
              last_path: tInfo.last_path,
              working_now: Boolean(rec.active),
              certain: Boolean(tInfo.certain),
            };
          }
        }
      }
    }
    return { flows, live_etag: sha256Hex(JSON.stringify(flows)).slice(0, 12) };
  }

  static #matchPathToOpenTasks(specsDir, relPosix) {
    const matches = [];
    for (const ent of fs.readdirSync(specsDir, { withFileTypes: true })) {
      if (!ent.isDirectory()) continue;
      const specDir = path.join(specsDir, ent.name);
      const specFile = path.join(specDir, "spec.md");
      if (!fs.existsSync(specFile)) continue;
      const sDoc = FrontmatterDocument.parse(readTextSafe(specFile) || "");
      const sState = (sDoc.text("state") || "").toLowerCase();
      if (isClosedState(sState) || sState === "archived" || sState === "paused") continue;

      const taskFiles = [];
      const rootTasks = path.join(specDir, "tasks");
      if (fs.existsSync(rootTasks)) {
        for (const tf of fs.readdirSync(rootTasks)) {
          if (tf.endsWith(".md") && tf !== "index.md") taskFiles.push(path.join(rootTasks, tf));
        }
      }
      const chRoot = path.join(specDir, "chapters");
      if (fs.existsSync(chRoot)) {
        for (const chEnt of fs.readdirSync(chRoot, { withFileTypes: true })) {
          if (!chEnt.isDirectory()) continue;
          const chTasks = path.join(chRoot, chEnt.name, "tasks");
          if (!fs.existsSync(chTasks)) continue;
          for (const tf of fs.readdirSync(chTasks)) {
            if (tf.endsWith(".md") && tf !== "index.md") taskFiles.push(path.join(chTasks, tf));
          }
        }
      }

      for (const tf of taskFiles) {
        const tDoc = FrontmatterDocument.parse(readTextSafe(tf) || "");
        if (isClosedState(tDoc.text("state"))) continue;
        const owned = [...tDoc.textList("files"), ...tDoc.textList("tests")].map(normalizeRelRepoPath);
        if (owned.includes(relPosix)) {
          const stem = path.basename(tf, ".md").split("-")[0];
          const taskId = tDoc.text("id") || `${ent.name}:${stem}`;
          matches.push({ flow_id: ent.name, task_id: taskId });
        }
      }
    }
    return matches;
  }

  static #maybeMarkCheckpointDue(effectiveRoot, record, touchedFlows, { nowMs, env }) {
    const startMs = Date.parse(record.started_at || "") || nowMs;
    const elapsedMs = nowMs - startMs;
    const dueDir = SpecActivity.resolveCheckpointDir(env);
    for (const flowId of touchedFlows) {
      const count = record.flows?.[flowId]?.unrecorded_tasks?.length || 0;
      const shouldNotify =
        (elapsedMs >= CHECKPOINT_COOLDOWN_MS && count >= CHECKPOINT_MULTI_TASK_COUNT) ||
        (elapsedMs >= CHECKPOINT_PERIODIC_MS && count >= 1);
      if (!shouldNotify) continue;
      const duePath = path.join(dueDir, `${sanitizeIdSegment(effectiveRoot)}__${sanitizeIdSegment(flowId)}.json`);
      const prev = readJsonSafe(duePath);
      if (prev?.last_notified_ms && nowMs - prev.last_notified_ms < CHECKPOINT_COOLDOWN_MS) continue;
      writeJsonAtomic(
        duePath,
        {
          flow_id: flowId,
          due: true,
          unrecorded_count: count,
          last_notified_ms: prev?.last_notified_ms || 0,
        },
        2,
      );
    }
  }
}
