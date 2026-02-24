"use strict";

const { createKmsClient } = require("./lib/client");

const skill = {
  name: "kms",
  version: "1.0.0",
  description: "KMS read/write governance skill for tasks, journals and knowledge",
  actions: {
    get_context_bundle: {
      description: "Read compact context bundle for planning/analysis",
      parameters: {
        type: "object",
        properties: {
          intent: { type: "string" },
          window_days: { type: "number", default: 14 },
          include_done: { type: "boolean", default: false },
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
          topic_id: args.topic_id,
        };
        return client.getContextBundle(params);
      },
    },
    list_tasks: {
      description: "List tasks from KMS task system",
      parameters: {
        type: "object",
        properties: {
          page: { type: "number", default: 1 },
          page_size: { type: "number", default: 50 },
          status: { type: "string" },
          priority: { type: "string" },
          topic_id: { type: "string" },
          q: { type: "string" },
        },
      },
      handler: async (args, context) => {
        const client = createKmsClient(context);
        return client.listTasks(args || {});
      },
    },
    search_notes: {
      description: "Search notes in KMS knowledge base",
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
      description: "List journals from KMS",
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
          task_type: { type: "string" },
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
