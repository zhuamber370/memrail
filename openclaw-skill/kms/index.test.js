"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const skill = require("./index");
const { createKmsClient } = require("./lib/client");

test("kms skill exposes comprehensive read actions", () => {
  const actionNames = Object.keys(skill.actions);
  const expected = [
    "list_topics",
    "list_cycles",
    "list_ideas",
    "list_changes",
    "get_change",
    "list_audit_events",
    "list_task_views_summary",
    "list_note_topic_summary",
    "list_routes",
    "list_route_node_logs",
    "list_links",
    "list_inbox",
    "list_knowledge",
    "list_journal_items",
    "list_task_sources",
    "list_note_sources",
    "propose_create_idea",
    "propose_create_route",
    "propose_create_route_node",
    "propose_create_knowledge",
    "propose_create_link",
    "propose_capture_inbox",
    "api_get",
  ];

  for (const action of expected) {
    assert.ok(actionNames.includes(action), `missing action: ${action}`);
  }
});

test("list_tasks supports full backend query filters", () => {
  const properties = skill.actions.list_tasks.parameters.properties;
  const expectedFilters = ["archived", "cycle_id", "stale_days", "due_before", "updated_before", "view"];
  for (const key of expectedFilters) {
    assert.ok(Object.prototype.hasOwnProperty.call(properties, key), `missing list_tasks filter: ${key}`);
  }
});

test("api_get enforces relative /api/v1 path and forwards params", async () => {
  const oldBaseUrl = process.env.KMS_BASE_URL;
  const oldApiKey = process.env.KMS_API_KEY;
  const oldFetch = global.fetch;

  process.env.KMS_BASE_URL = "http://127.0.0.1:8000";
  process.env.KMS_API_KEY = "test-key";
  global.fetch = async (url) => ({
    ok: true,
    status: 200,
    json: async () => ({ url }),
    text: async () => "",
  });

  try {
    const client = createKmsClient({});
    await assert.rejects(
      async () => client.apiGet("http://example.com/api/v1/tasks", {}),
      /path must start with '\/'/
    );
    await assert.rejects(async () => client.apiGet("/health", {}), /path must start with \/api\/v1\//);

    const out = await client.apiGet("/api/v1/tasks", { page: 1, page_size: 20 });
    assert.equal(out.url, "http://127.0.0.1:8000/api/v1/tasks?page=1&page_size=20");
  } finally {
    process.env.KMS_BASE_URL = oldBaseUrl;
    process.env.KMS_API_KEY = oldApiKey;
    global.fetch = oldFetch;
  }
});
