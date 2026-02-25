"use strict";

function normTitle(value) {
  return String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^0-9a-zA-Z\u4e00-\u9fff]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const TOPIC_KEYWORD_RULES = [
  {
    topicId: "top_fx_engineering_arch",
    keywords: [
      "code",
      "coding",
      "dev",
      "bug",
      "fix",
      "debug",
      "api",
      "backend",
      "frontend",
      "database",
      "数据库",
      "开发",
      "代码",
      "排障",
      "修复",
      "接口",
    ],
  },
  {
    topicId: "top_fx_operations_delivery",
    keywords: ["deploy", "release", "delivery", "ops", "oncall", "incident", "上线", "运维", "交付", "发布"],
  },
  {
    topicId: "top_fx_product_strategy",
    keywords: ["roadmap", "strategy", "product", "需求", "规划", "产品", "方案", "设计"],
  },
  {
    topicId: "top_fx_growth_marketing",
    keywords: ["growth", "marketing", "campaign", "seo", "内容增长", "增长", "营销", "投放"],
  },
  {
    topicId: "top_fx_finance_legal",
    keywords: ["finance", "legal", "invoice", "contract", "compliance", "财务", "法务", "合同", "合规"],
  },
  {
    topicId: "top_fx_learning_research",
    keywords: ["research", "learn", "study", "read", "学习", "研究", "调研", "复盘"],
  },
];

function inferTopicId(text) {
  const normalized = normTitle(text);
  if (!normalized) return null;
  for (const rule of TOPIC_KEYWORD_RULES) {
    for (const keyword of rule.keywords) {
      if (normalized.includes(normTitle(keyword))) {
        return rule.topicId;
      }
    }
  }
  return null;
}

function normalizeNodeStatus(status) {
  if (status === "todo") return "waiting";
  if (status === "in_progress") return "execute";
  if (status === "cancelled") return "removed";
  return status || "waiting";
}

function sortNodes(nodes) {
  return [...(Array.isArray(nodes) ? nodes : [])].sort((a, b) => {
    const orderA = Number(a && a.order_hint) || 0;
    const orderB = Number(b && b.order_hint) || 0;
    if (orderA !== orderB) return orderA - orderB;
    const timeA = String((a && a.created_at) || "");
    const timeB = String((b && b.created_at) || "");
    if (timeA !== timeB) return timeA.localeCompare(timeB);
    return String((a && a.id) || "").localeCompare(String((b && b.id) || ""));
  });
}

function compactNode(node) {
  if (!node) return null;
  return {
    id: node.id,
    title: node.title,
    node_type: node.node_type,
    status: node.status,
    normalized_status: normalizeNodeStatus(node.status),
    order_hint: node.order_hint,
    assignee_type: node.assignee_type || null,
    assignee_id: node.assignee_id || null,
  };
}

function summarizeRouteGraph(graph) {
  const nodes = sortNodes(graph && graph.nodes);
  const edges = Array.isArray(graph && graph.edges) ? graph.edges : [];
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  const normalizedNodes = nodes.map((node) => ({
    node,
    normalizedStatus: normalizeNodeStatus(node.status),
  }));
  const executing = normalizedNodes.filter((item) => item.normalizedStatus === "execute").map((item) => item.node);
  const done = normalizedNodes.filter((item) => item.normalizedStatus === "done").map((item) => item.node);
  const waiting = normalizedNodes.filter((item) => item.normalizedStatus === "waiting").map((item) => item.node);

  const focusCandidates = nodes.filter((node) => node.node_type === "goal" || node.node_type === "start");
  const executableNodes = focusCandidates.length ? focusCandidates : nodes;
  const executingNode =
    executableNodes.find((node) => normalizeNodeStatus(node.status) === "execute") ||
    nodes.find((node) => normalizeNodeStatus(node.status) === "execute") ||
    null;
  const doneNodes = executableNodes.filter((node) => normalizeNodeStatus(node.status) === "done");
  const lastDoneNode = doneNodes.length ? doneNodes[doneNodes.length - 1] : null;
  const fallbackNode =
    executableNodes.find((node) => node.node_type !== "start") ||
    executableNodes[0] ||
    nodes[0] ||
    null;
  const currentNode = executingNode || lastDoneNode || fallbackNode;

  const previousNodes = currentNode
    ? edges
        .filter((edge) => edge.to_node_id === currentNode.id)
        .map((edge) => nodeById.get(edge.from_node_id))
        .filter(Boolean)
    : [];

  return {
    node_count: nodes.length,
    edge_count: edges.length,
    current_node: compactNode(currentNode),
    previous_nodes: previousNodes.map((node) => compactNode(node)),
    executing_nodes: executing.map((node) => compactNode(node)),
    done_nodes: done.map((node) => compactNode(node)),
    waiting_nodes: waiting.map((node) => compactNode(node)),
  };
}

function createKmsClient(context) {
  const config = (context && context.config && context.config.kms) || {};
  const baseUrl = process.env.KMS_BASE_URL || config.baseUrl || "";
  const apiKey = process.env.KMS_API_KEY || config.apiKey || "";
  const actorId = process.env.KMS_ACTOR_ID || config.actorId || "openclaw";

  if (!baseUrl) {
    throw new Error("KMS_BASE_URL is required");
  }
  if (!apiKey) {
    throw new Error("KMS_API_KEY is required");
  }

  const base = String(baseUrl).replace(/\/+$/, "");
  const headers = {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
  };

  async function request(method, path, payload, params, retries429, retries500) {
    const retry429 = Number.isFinite(retries429) ? retries429 : 3;
    const retry500 = Number.isFinite(retries500) ? retries500 : 2;
    const maxAttempts = Math.max(retry429, retry500) + 1;
    const query = params
      ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null))
      : "";

    let lastErr;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      try {
        const response = await fetch(`${base}${path}${query}`, {
          method,
          headers,
          body: payload ? JSON.stringify(payload) : undefined,
        });

        if (response.status === 429 || response.status === 500) {
          const limit = response.status === 429 ? retry429 : retry500;
          if (attempt < limit) {
            await sleep(200 * 2 ** attempt);
            continue;
          }
        }

        if (response.status >= 400 && response.status < 500 && response.status !== 409 && response.status !== 429) {
          const text = await response.text();
          throw new Error(`${response.status}: ${text}`);
        }

        if (response.status === 409 && attempt < 1) {
          await sleep(100);
          continue;
        }

        if (!response.ok) {
          const text = await response.text();
          throw new Error(`${response.status}: ${text}`);
        }

        return response.json();
      } catch (error) {
        lastErr = error;
      }
    }

    throw new Error(`request failed after retries: ${String(lastErr)}`);
  }

  async function get(path, params) {
    return request("GET", path, null, params, 0, 0);
  }

  async function post(path, payload, retries429, retries500) {
    return request("POST", path, payload, null, retries429, retries500);
  }

  async function listTasks(params) {
    return get("/api/v1/tasks", params || {});
  }

  async function searchNotes(params) {
    return get("/api/v1/notes/search", params || {});
  }

  async function listTopics() {
    return get("/api/v1/topics", {});
  }

  async function listJournals(params) {
    return get("/api/v1/journals", params || {});
  }

  async function getJournal(journalDate) {
    return get(`/api/v1/journals/${journalDate}`, {});
  }

  async function getContextBundle(params) {
    return get("/api/v1/context/bundle", params || {});
  }

  async function listRoutes(params) {
    return get("/api/v1/routes", params || {});
  }

  async function getRouteGraph(routeId) {
    if (!routeId) throw new Error("route_id is required");
    return get(`/api/v1/routes/${routeId}/graph`, {});
  }

  async function getNodeLogs(routeId, nodeId) {
    if (!routeId) throw new Error("route_id is required");
    if (!nodeId) throw new Error("node_id is required");
    return get(`/api/v1/routes/${routeId}/nodes/${nodeId}/logs`, {});
  }

  async function getTaskExecutionSnapshot(params) {
    const taskId = params && params.task_id;
    if (!taskId) throw new Error("task_id is required");

    const includeAllRoutes = params && Object.prototype.hasOwnProperty.call(params, "include_all_routes")
      ? Boolean(params.include_all_routes)
      : true;
    const includeLogs = Boolean(params && params.include_logs);
    const pageSize = Number(params && params.page_size) > 0 ? Number(params.page_size) : 100;

    const routesPayload = await listRoutes({
      page: 1,
      page_size: pageSize,
      task_id: taskId,
    });
    const routes = Array.isArray(routesPayload && routesPayload.items) ? routesPayload.items : [];
    const activeRoute = routes.find((route) => route.status === "active") || null;
    const selectedRoute = activeRoute || routes[0] || null;

    if (!selectedRoute) {
      return {
        task_id: taskId,
        fetched_at: new Date().toISOString(),
        routes: [],
        selected_route_id: null,
        selected_route: null,
        selected_route_graph: null,
        selected_route_state: null,
        route_snapshots: [],
      };
    }

    const selectedRouteGraph = await getRouteGraph(selectedRoute.id);
    const selectedRouteState = summarizeRouteGraph(selectedRouteGraph);

    let selectedRouteLogs = null;
    if (includeLogs) {
      selectedRouteLogs = {};
      const nodes = Array.isArray(selectedRouteGraph.nodes) ? selectedRouteGraph.nodes : [];
      for (const node of nodes) {
        const logs = await getNodeLogs(selectedRoute.id, node.id);
        selectedRouteLogs[node.id] = logs && Array.isArray(logs.items) ? logs.items : [];
      }
    }

    let routeSnapshots = [
      {
        route: selectedRoute,
        graph: selectedRouteGraph,
        state: selectedRouteState,
      },
    ];
    if (selectedRouteLogs) {
      routeSnapshots[0].node_logs = selectedRouteLogs;
    }

    if (includeAllRoutes && routes.length > 1) {
      const additionalRoutes = routes.filter((route) => route.id !== selectedRoute.id);
      const extraSnapshots = await Promise.all(
        additionalRoutes.map(async (route) => {
          const graph = await getRouteGraph(route.id);
          const state = summarizeRouteGraph(graph);
          const snapshot = { route, graph, state };
          if (!includeLogs) return snapshot;
          const nodeLogs = {};
          const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
          for (const node of nodes) {
            const logs = await getNodeLogs(route.id, node.id);
            nodeLogs[node.id] = logs && Array.isArray(logs.items) ? logs.items : [];
          }
          snapshot.node_logs = nodeLogs;
          return snapshot;
        })
      );
      routeSnapshots = routeSnapshots.concat(extraSnapshots);
    }

    return {
      task_id: taskId,
      fetched_at: new Date().toISOString(),
      routes,
      selected_route_id: selectedRoute.id,
      selected_route: selectedRoute,
      selected_route_graph: selectedRouteGraph,
      selected_route_state: selectedRouteState,
      route_snapshots: routeSnapshots,
    };
  }

  async function proposeChanges(actions, actor, tool) {
    return post("/api/v1/changes/dry-run", {
      actions,
      actor: actor || { type: "agent", id: actorId },
      tool: tool || "openclaw-skill",
    });
  }

  async function commitChanges(changeSetId, approvedBy, clientRequestId) {
    const payload = { approved_by: approvedBy || { type: "user", id: "usr_local" } };
    if (clientRequestId) payload.client_request_id = clientRequestId;
    return post(`/api/v1/changes/${changeSetId}/commit`, payload);
  }

  async function rejectChanges(changeSetId) {
    if (!changeSetId) throw new Error("change_set_id is required");
    return request("DELETE", `/api/v1/changes/${changeSetId}`, null, null, 0, 0);
  }

  async function undoLastCommit(requestedBy, reason, clientRequestId) {
    const payload = {
      requested_by: requestedBy || { type: "user", id: "usr_local" },
      reason: reason || "manual undo",
    };
    if (clientRequestId) payload.client_request_id = clientRequestId;
    return post("/api/v1/commits/undo-last", payload);
  }

  async function defaultTopicId() {
    const topics = await listTopics();
    const items = topics.items || [];
    const fallback = items.length > 0 ? String(items[0].id) : null;
    const preferred = items.find((item) => item.id === "top_fx_other");
    const resolved = preferred ? "top_fx_other" : fallback;
    if (!resolved) throw new Error("no active topics found for task classification");
    return resolved;
  }

  async function findActiveTaskByTitle(title) {
    const listed = await listTasks({ page: 1, page_size: 100, q: title });
    const target = normTitle(title);
    const items = listed.items || [];
    for (const item of items) {
      if ((item.status === "todo" || item.status === "in_progress") && normTitle(item.title) === target) {
        return item;
      }
    }
    return null;
  }

  async function findActiveNoteByTitle(title) {
    const listed = await searchNotes({ page: 1, page_size: 100, q: title, status: "active" });
    const target = normTitle(title);
    const items = listed.items || [];
    for (const item of items) {
      if (normTitle(item.title) === target) {
        return item;
      }
    }
    return null;
  }

  async function proposeRecordTodo(args) {
    const title = args.title;
    const source = args.source;
    if (!title) throw new Error("title is required");
    if (!source) throw new Error("source is required");

    const actor = args.actor || { type: "agent", id: actorId };
    const tool = args.tool || "openclaw-skill";
    const existing = await findActiveTaskByTitle(title);

    if (existing) {
      return proposeChanges(
        [
          {
            type: "update_task",
            payload: {
              task_id: existing.id,
              description: args.description || existing.description || "",
              priority: args.priority || existing.priority,
              due: args.due || existing.due,
              source,
            },
          },
        ],
        actor,
        tool
      );
    }

    const inferredTopicId = inferTopicId([args.title, args.description].filter(Boolean).join(" "));
    const topicId = args.topic_id || inferredTopicId || (await defaultTopicId());
    const payload = {
      title,
      description: args.description || "",
      status: "todo",
      source,
      topic_id: topicId,
    };
    if (args.priority) payload.priority = args.priority;
    if (args.due) payload.due = args.due;

    return proposeChanges([{ type: "create_task", payload }], actor, tool);
  }

  async function proposeAppendJournal(args) {
    if (!args.journal_date) throw new Error("journal_date is required");
    if (!args.append_text) throw new Error("append_text is required");
    if (!args.source) throw new Error("source is required");

    return proposeChanges(
      [
        {
          type: "upsert_journal_append",
          payload: {
            journal_date: args.journal_date,
            append_text: args.append_text,
            source: args.source,
          },
        },
      ],
      args.actor || { type: "agent", id: actorId },
      args.tool || "openclaw-skill"
    );
  }

  async function proposeUpsertKnowledge(args) {
    if (!args.title) throw new Error("title is required");
    if (!args.body_increment) throw new Error("body_increment is required");
    if (!args.source) throw new Error("source is required");

    const actor = args.actor || { type: "agent", id: actorId };
    const tool = args.tool || "openclaw-skill";
    const existing = await findActiveNoteByTitle(args.title);

    if (existing) {
      const payload = {
        note_id: existing.id,
        body_append: args.body_increment,
        source: args.source,
      };
      if (args.topic_id) payload.topic_id = args.topic_id;
      if (Array.isArray(args.tags)) payload.tags = args.tags;
      return proposeChanges([{ type: "patch_note", payload }], actor, tool);
    }

    const notePayload = {
      title: args.title,
      body: args.body_increment,
      sources: [{ type: "text", value: args.source }],
      tags: Array.isArray(args.tags) ? args.tags : [],
    };
    if (args.topic_id) notePayload.topic_id = args.topic_id;

    return proposeChanges([{ type: "append_note", payload: notePayload }], actor, tool);
  }

  return {
    actorId,
    listTasks,
    listRoutes,
    getRouteGraph,
    getTaskExecutionSnapshot,
    searchNotes,
    listTopics,
    listJournals,
    getJournal,
    getContextBundle,
    proposeChanges,
    commitChanges,
    rejectChanges,
    undoLastCommit,
    proposeRecordTodo,
    proposeAppendJournal,
    proposeUpsertKnowledge,
  };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

module.exports = {
  createKmsClient,
};
