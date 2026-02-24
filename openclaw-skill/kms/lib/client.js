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

    const inferredTopicId = inferTopicId([args.title, args.description, args.task_type].filter(Boolean).join(" "));
    const topicId = args.topic_id || inferredTopicId || (await defaultTopicId());
    const payload = {
      title,
      description: args.description || "",
      status: "todo",
      source,
      task_type: args.task_type || "build",
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
