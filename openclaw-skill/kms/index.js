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
      description:
        "Natural-language task execution reader for current node, DAG state, dependencies and branch relations",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
          task_query: { type: "string" },
          task_title: { type: "string" },
          q: { type: "string" },
          include_all_routes: { type: "boolean", default: true },
          include_logs: { type: "boolean", default: false },
          page_size: { type: "number", default: 100 },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getTaskExecutionSnapshot({
          task_id: args.task_id,
          task_query: args.task_query,
          task_title: args.task_title,
          q: args.q,
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
    list_journal_items: {
      description: "List journal items for a specific journal date",
      parameters: {
        type: "object",
        properties: {
          journal_date: { type: "string" },
        },
        required: ["journal_date"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listJournalItems(args.journal_date);
      },
    },
    list_task_sources: {
      description: "List source records of a task",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
        },
        required: ["task_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listTaskSources(args.task_id);
      },
    },
    list_note_sources: {
      description: "List source records of a note",
      parameters: {
        type: "object",
        properties: {
          note_id: { type: "string" },
        },
        required: ["note_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listNoteSources(args.note_id);
      },
    },
    list_links: {
      description: "List entity links with optional filters",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 50 },
          from_type: { type: "string" },
          from_id: { type: "string" },
          to_type: { type: "string" },
          to_id: { type: "string" },
          relation: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listLinks(args || {});
      },
    },
    list_inbox: {
      description: "List inbox items",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 50 },
          status: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listInbox(args || {});
      },
    },
    get_inbox: {
      description: "Get one inbox item",
      parameters: {
        type: "object",
        properties: {
          inbox_id: { type: "string" },
        },
        required: ["inbox_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getInbox(args.inbox_id);
      },
    },
    list_knowledge: {
      description: "List knowledge items",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 20 },
          status: { type: "string", default: "active" },
          category: { type: "string" },
          q: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listKnowledge(args || {});
      },
    },
    get_knowledge: {
      description: "Get one knowledge item",
      parameters: {
        type: "object",
        properties: {
          item_id: { type: "string" },
        },
        required: ["item_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.getKnowledge(args.item_id);
      },
    },
    api_get: {
      description: "Fallback generic read-through for uncovered /api/v1/* endpoints",
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
    propose_capture_inbox: {
      description: "Dry-run capture inbox item",
      parameters: {
        type: "object",
        properties: {
          content: { type: "string" },
          source: { type: "string" },
        },
        required: ["content", "source"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCaptureInbox(args);
      },
    },
    propose_create_idea: {
      description: "Dry-run create idea",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
          title: { type: "string" },
          problem: { type: "string" },
          hypothesis: { type: "string" },
          status: { type: "string" },
          topic_id: { type: "string" },
          source: { type: "string" },
        },
        required: ["task_id", "title", "source"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateIdea(args);
      },
    },
    propose_patch_idea: {
      description: "Dry-run patch idea",
      parameters: {
        type: "object",
        properties: {
          idea_id: { type: "string" },
          title: { type: "string" },
          problem: { type: "string" },
          hypothesis: { type: "string" },
          status: { type: "string" },
          topic_id: { type: "string" },
          source: { type: "string" },
        },
        required: ["idea_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePatchIdea(args);
      },
    },
    propose_promote_idea: {
      description: "Dry-run promote idea to route node",
      parameters: {
        type: "object",
        properties: {
          idea_id: { type: "string" },
          route_id: { type: "string" },
          node_type: { type: "string", enum: ["goal", "idea"] },
          title: { type: "string" },
          description: { type: "string" },
        },
        required: ["idea_id", "route_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePromoteIdea(args);
      },
    },
    propose_create_route: {
      description: "Dry-run create route",
      parameters: {
        type: "object",
        properties: {
          task_id: { type: "string" },
          name: { type: "string" },
          goal: { type: "string" },
          status: { type: "string" },
          priority: { type: "string" },
          owner: { type: "string" },
          parent_route_id: { type: "string" },
        },
        required: ["task_id", "name"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateRoute(args);
      },
    },
    propose_patch_route: {
      description: "Dry-run patch route",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          name: { type: "string" },
          goal: { type: "string" },
          status: { type: "string" },
          priority: { type: "string" },
          owner: { type: "string" },
          parent_route_id: { type: "string" },
        },
        required: ["route_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePatchRoute(args);
      },
    },
    propose_create_route_node: {
      description: "Dry-run create route node",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          node_type: { type: "string", enum: ["start", "goal", "idea"] },
          title: { type: "string" },
          description: { type: "string" },
          status: { type: "string", enum: ["waiting", "execute", "done"] },
          parent_node_id: { type: "string" },
          order_hint: { type: "number" },
          assignee_type: { type: "string", enum: ["human", "agent"] },
          assignee_id: { type: "string" },
        },
        required: ["route_id", "node_type", "title"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateRouteNode(args);
      },
    },
    propose_patch_route_node: {
      description: "Dry-run patch route node",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          node_id: { type: "string" },
          node_type: { type: "string", enum: ["start", "goal", "idea"] },
          title: { type: "string" },
          description: { type: "string" },
          status: { type: "string", enum: ["waiting", "execute", "done"] },
          parent_node_id: { type: "string" },
          order_hint: { type: "number" },
          assignee_type: { type: "string", enum: ["human", "agent"] },
          assignee_id: { type: "string" },
        },
        required: ["route_id", "node_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePatchRouteNode(args);
      },
    },
    propose_delete_route_node: {
      description: "Dry-run delete route node",
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
        return client.proposeDeleteRouteNode(args);
      },
    },
    propose_create_route_edge: {
      description: "Dry-run create route edge",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          from_node_id: { type: "string" },
          to_node_id: { type: "string" },
          relation: { type: "string", enum: ["refine", "initiate", "handoff"] },
          description: { type: "string" },
        },
        required: ["route_id", "from_node_id", "to_node_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateRouteEdge(args);
      },
    },
    propose_patch_route_edge: {
      description: "Dry-run patch route edge",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          edge_id: { type: "string" },
          description: { type: "string" },
        },
        required: ["route_id", "edge_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePatchRouteEdge(args);
      },
    },
    propose_delete_route_edge: {
      description: "Dry-run delete route edge",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          edge_id: { type: "string" },
        },
        required: ["route_id", "edge_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeDeleteRouteEdge(args);
      },
    },
    propose_append_route_node_log: {
      description: "Dry-run append route node log",
      parameters: {
        type: "object",
        properties: {
          route_id: { type: "string" },
          node_id: { type: "string" },
          content: { type: "string" },
          actor_type: { type: "string", enum: ["human", "agent"] },
          actor_id: { type: "string" },
          log_type: { type: "string", enum: ["note", "evidence", "decision", "summary"] },
          source_ref: { type: "string" },
        },
        required: ["route_id", "node_id", "content"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeAppendRouteNodeLog(args);
      },
    },
    propose_create_knowledge: {
      description: "Dry-run create knowledge item",
      parameters: {
        type: "object",
        properties: {
          title: { type: "string" },
          body: { type: "string" },
          category: { type: "string", enum: ["ops_manual", "mechanism_spec", "decision_record"] },
        },
        required: ["title", "body"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateKnowledge(args);
      },
    },
    propose_patch_knowledge: {
      description: "Dry-run patch knowledge item",
      parameters: {
        type: "object",
        properties: {
          item_id: { type: "string" },
          title: { type: "string" },
          body: { type: "string" },
          category: { type: "string", enum: ["ops_manual", "mechanism_spec", "decision_record"] },
          status: { type: "string", enum: ["active", "archived"] },
        },
        required: ["item_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposePatchKnowledge(args);
      },
    },
    propose_archive_knowledge: {
      description: "Dry-run archive knowledge item",
      parameters: {
        type: "object",
        properties: {
          item_id: { type: "string" },
        },
        required: ["item_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeArchiveKnowledge(args);
      },
    },
    propose_delete_knowledge: {
      description: "Dry-run delete knowledge item",
      parameters: {
        type: "object",
        properties: {
          item_id: { type: "string" },
        },
        required: ["item_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeDeleteKnowledge(args);
      },
    },
    propose_create_link: {
      description: "Dry-run create link",
      parameters: {
        type: "object",
        properties: {
          from_type: { type: "string", enum: ["note", "task"] },
          from_id: { type: "string" },
          to_type: { type: "string", enum: ["note", "task"] },
          to_id: { type: "string" },
          relation: { type: "string" },
        },
        required: ["from_type", "from_id", "to_type", "to_id", "relation"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeCreateLink(args);
      },
    },
    propose_delete_link: {
      description: "Dry-run delete link",
      parameters: {
        type: "object",
        properties: {
          link_id: { type: "string" },
        },
        required: ["link_id"],
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.proposeDeleteLink(args);
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
