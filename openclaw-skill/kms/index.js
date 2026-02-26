"use strict";

const { createKmsClient } = require("./lib/client");

const skill = {
  name: "kms",
  version: "1.0.0",
  description: "Memrail read/write governance skill for tasks, journals and knowledge",
  actions: {
    get_context_bundle: {
      description: "Read compact context bundle for planning/analysis",
      parameters: {
        type: "object",
        properties: {
          intent: { type: "string" },
          window_days: { type: "number", default: 14 },
          include_done: { type: "boolean", default: false },
          tasks_limit: { type: "number", default: 20 },
          notes_limit: { type: "number", default: 20 },
          journals_limit: { type: "number", default: 14 },
          topic_id: {
            type: "array",
            items: { type: "string" },
          },
        },
        required: ["intent"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        const params = {
          intent: args.intent,
          window_days: args.window_days ?? 14,
          include_done: args.include_done ?? false,
          tasks_limit: args.tasks_limit,
          notes_limit: args.notes_limit,
          journals_limit: args.journals_limit,
          topic_id: args.topic_id,
        };
        return client.getContextBundle(params);
      },
    },
    list_tasks: {
      description: "List tasks from Memrail task system",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 50 },
          status: { type: "string" },
          priority: { type: "string" },
          archived: { type: "boolean" },
          topic_id: { type: "string" },
          cycle_id: { type: "string" },
          stale_days: { type: "number" },
          due_before: { type: "string" },
          updated_before: { type: "string" },
          view: { type: "string" },
          q: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listTasks(args || {});
      },
    },
    list_topics: {
      description: "List all topics",
      parameters: {
        type: "object",
        properties: {},
      },
      handler: async (_args, context) => {
        const client = createKmsClient(context);
        return client.listTopics();
      },
    },
    list_cycles: {
      description: "List all cycles",
      parameters: {
        type: "object",
        properties: {},
      },
      handler: async (_args, context) => {
        const client = createKmsClient(context);
        return client.listCycles();
      },
    },
    list_ideas: {
      description: "List ideas",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 20 },
          task_id: { type: "string" },
          status: { type: "string" },
          q: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listIdeas(args || {});
      },
    },
    list_changes: {
      description: "List proposed/committed/rejected change sets",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 20 },
          status: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listChanges(args || {});
      },
    },
    get_change: {
      description: "Get one change set detail",
      parameters: {
        type: "object",
        properties: {
          change_set_id: { type: "string" },
        },
        required: ["change_set_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getChange(args.change_set_id);
      },
    },
    list_audit_events: {
      description: "List audit events with filters",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 20 },
          actor_type: { type: "string" },
          actor_id: { type: "string" },
          tool: { type: "string" },
          action: { type: "string" },
          target_type: { type: "string" },
          target_id: { type: "string" },
          occurred_from: { type: "string" },
          occurred_to: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listAuditEvents(args || {});
      },
    },
    list_task_views_summary: {
      description: "Get task view counters (today/overdue/this_week/backlog/blocked/done)",
      parameters: {
        type: "object",
        properties: {},
      },
      handler: async (_args, context) => {
        const client = createKmsClient(context);
        return client.listTaskViewsSummary();
      },
    },
    list_note_topic_summary: {
      description: "Get note count summary grouped by topic",
      parameters: {
        type: "object",
        properties: {
          status: { type: "string", default: "active" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listNoteTopicSummary(args || {});
      },
    },
    list_routes: {
      description: "List routes with optional filters",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 100 },
          task_id: { type: "string" },
          status: { type: "string" },
          q: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listRoutes(args || {});
      },
    },
    list_task_routes: {
      description: "List route flows under a task",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 100 },
          status: { type: "string" },
          q: { type: "string" },
        },
        required: ["task_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listRoutes({
          task_id: args.task_id,
          page: args.page ?? 1,
          page_size: args.page_size ?? 100,
          status: args.status,
          q: args.q,
        });
      },
    },
    list_route_node_logs: {
      description: "List execution logs for one route node",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          node_id: { type: "string" },
        },
        required: ["route_id", "node_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getNodeLogs(args.route_id, args.node_id);
      },
    },
    get_route_graph: {
      description: "Get full node-edge graph for a route",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
        },
        required: ["route_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getRouteGraph(args.route_id);
      },
    },
    get_task_execution_snapshot: {
      description: "Get latest task execution snapshot including current node and previous step",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
          include_all_routes: { type: "boolean", default: true },
          include_logs: { type: "boolean", default: false },
          page_size: { type: "number", default: 100 },
        },
        required: ["task_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getTaskExecutionSnapshot({
          task_id: args.task_id,
          include_all_routes: args.include_all_routes,
          include_logs: args.include_logs,
          page_size: args.page_size,
        });
      },
    },
    search_notes: {
      description: "Search notes in Memrail knowledge base",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 50 },
          q: { type: "string" },
          topic_id: { type: "string" },
          status: { type: "string" },
          unclassified: { type: "boolean" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.searchNotes(args || {});
      },
    },
    list_journals: {
      description: "List journals from Memrail",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 30 },
          date_from: { type: "string" },
          date_to: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listJournals(args || {});
      },
    },
    get_journal: {
      description: "Read one journal by date (YYYY-MM-DD)",
      parameters: {
        type: "object",
        properties: {
          journal_date: { type: "string" },
        },
        required: ["journal_date"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getJournal(args.journal_date);
      },
    },
    api_get: {
      description: "Generic read-through for any /api/v1/* endpoint",
      parameters: {
        type: "object",
        properties: {
          path: { type: "string" },
          params: {
            type: "object",
            additionalProperties: true,
          },
        },
        required: ["path"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.apiGet(args.path, args.params || {});
      },
    },
    propose_record_todo: {
      description: "Dry-run create/update todo from explicit user command",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string" },
          description: { type: "string" },
          priority: { type: "string", enum: ["P0", "P1", "P2", "P3"] },
          due: { type: "string" },
          topic_id: { type: "string" },
          source: { type: "string" },
        },
        required: ["title", "source"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeRecordTodo(args);
      },
    },
    propose_append_journal: {
      description: "Dry-run append to daily journal (single journal per day)",
      parameters: {
        type: "object",
        properties: {
          journal_date: { type: "string" },
          append_text: { type: "string" },
          source: { type: "string" },
        },
        required: ["journal_date", "append_text", "source"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeAppendJournal(args);
      },
    },
    propose_upsert_knowledge: {
      description: "Dry-run upsert topic knowledge by title (append when existing)",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string" },
          body_increment: { type: "string" },
          source: { type: "string" },
          topic_id: { type: "string" },
          tags: {
            type: "array",
            items: { type: "string" },
          },
        },
        required: ["title", "body_increment", "source"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeUpsertKnowledge(args);
      },
    },
    commit_changes: {
      description: "Commit a previously approved change set",
      parameters: {
        type: "object",
        properties: {
          change_set_id: { type: "string" },
          approved_by_type: { type: "string", default: "user" },
          approved_by_id: { type: "string", default: "usr_local" },
          client_request_id: { type: "string" },
        },
        required: ["change_set_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.commitChanges(
          args.change_set_id,
          { type: args.approved_by_type || "user", id: args.approved_by_id || "usr_local" },
          args.client_request_id
        );
      },
    },
    reject_changes: {
      description: "Reject and delete a proposed change set",
      parameters: {
        type: "object",
        properties: {
          change_set_id: { type: "string" },
        },
        required: ["change_set_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.rejectChanges(args.change_set_id);
      },
    },
    undo_last_commit: {
      description: "Undo the most recent batch commit",
      parameters: {
        type: "object",
        properties: {
          reason: { type: "string" },
          requested_by_type: { type: "string", default: "user" },
          requested_by_id: { type: "string", default: "usr_local" },
          client_request_id: { type: "string" },
        },
        required: ["reason"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.undoLastCommit(
          { type: args.requested_by_type || "user", id: args.requested_by_id || "usr_local" },
          args.reason,
          args.client_request_id
        );
      },
    },
  },
};

module.exports = skill;
module.exports.default = skill;
