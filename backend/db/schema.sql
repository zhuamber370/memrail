CREATE TABLE IF NOT EXISTS inbox_items (
  id VARCHAR(40) PRIMARY KEY,
  content TEXT NOT NULL,
  source VARCHAR(300) NOT NULL,
  status VARCHAR(20) NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS topics (
  id VARCHAR(40) PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  name_en VARCHAR(120) NOT NULL,
  name_zh VARCHAR(120) NOT NULL,
  kind VARCHAR(20) NOT NULL,
  status VARCHAR(20) NOT NULL,
  summary TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS topic_aliases (
  id VARCHAR(40) PRIMARY KEY,
  topic_id VARCHAR(40) NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  alias VARCHAR(120) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO topics (id, name, name_en, name_zh, kind, status, summary)
VALUES
  ('top_fx_product_strategy', 'Product & Strategy', 'Product & Strategy', '产品与战略', 'domain', 'active', 'Business direction, priorities, and decision framing.'),
  ('top_fx_engineering_arch', 'Engineering & Architecture', 'Engineering & Architecture', '工程与架构', 'domain', 'active', 'System design, implementation, code quality, and technical debt.'),
  ('top_fx_operations_delivery', 'Operations & Delivery', 'Operations & Delivery', '运营与交付', 'domain', 'active', 'Execution workflows, delivery coordination, and operational runbooks.'),
  ('top_fx_growth_marketing', 'Growth & Marketing', 'Growth & Marketing', '增长与营销', 'domain', 'active', 'Acquisition, positioning, messaging, and user growth loops.'),
  ('top_fx_finance_legal', 'Finance & Legal', 'Finance & Legal', '财务与法务', 'domain', 'active', 'Budgeting, contracts, compliance, and risk control.'),
  ('top_fx_learning_research', 'Learning & Research', 'Learning & Research', '学习与研究', 'domain', 'active', 'Research findings, experiments, and knowledge exploration.'),
  ('top_fx_other', 'Other', 'Other', '其他', 'domain', 'active', 'Fallback bucket for uncategorized items pending review.')
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS tasks (
  id VARCHAR(40) PRIMARY KEY,
  title VARCHAR(120) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  acceptance_criteria TEXT NOT NULL DEFAULT '',
  topic_id VARCHAR(40) NOT NULL REFERENCES topics(id) ON DELETE RESTRICT,
  status VARCHAR(20) NOT NULL,
  cancelled_reason TEXT,
  priority VARCHAR(2),
  due DATE,
  source VARCHAR(300) NOT NULL,
  cycle_id VARCHAR(40),
  archived_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cycles (
  id VARCHAR(40) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journals (
  id VARCHAR(40) PRIMARY KEY,
  journal_date DATE NOT NULL UNIQUE,
  raw_content TEXT NOT NULL DEFAULT '',
  digest TEXT NOT NULL DEFAULT '',
  triage_status VARCHAR(20) NOT NULL DEFAULT 'open',
  source VARCHAR(300) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS journal_items (
  id VARCHAR(40) PRIMARY KEY,
  journal_id VARCHAR(40) NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  kind VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  resolution VARCHAR(20) NOT NULL DEFAULT 'pending',
  task_id VARCHAR(40) REFERENCES tasks(id) ON DELETE SET NULL,
  topic_id VARCHAR(40) REFERENCES topics(id) ON DELETE SET NULL,
  ignore_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS topic_entries (
  id VARCHAR(40) PRIMARY KEY,
  topic_id VARCHAR(40) NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  entry_type VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notes (
  id VARCHAR(40) PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  body TEXT NOT NULL,
  tags_json JSON NOT NULL DEFAULT '[]',
  topic_id VARCHAR(40) REFERENCES topics(id) ON DELETE SET NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS note_sources (
  id VARCHAR(40) PRIMARY KEY,
  note_id VARCHAR(40) NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
  source_type VARCHAR(20) NOT NULL,
  source_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS knowledge_items (
  id VARCHAR(40) PRIMARY KEY,
  type VARCHAR(20) NOT NULL,
  title VARCHAR(200) NOT NULL,
  topic_id VARCHAR(40) REFERENCES topics(id) ON DELETE SET NULL,
  tags_json JSON NOT NULL DEFAULT '[]',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  content_json JSON NOT NULL DEFAULT '{}'::json,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_evidences (
  id VARCHAR(40) PRIMARY KEY,
  item_id VARCHAR(40) NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  source_ref TEXT NOT NULL,
  excerpt TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS links (
  id VARCHAR(40) PRIMARY KEY,
  from_type VARCHAR(20) NOT NULL,
  from_id VARCHAR(40) NOT NULL,
  to_type VARCHAR(20) NOT NULL,
  to_id VARCHAR(40) NOT NULL,
  relation VARCHAR(40) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS task_sources (
  id VARCHAR(40) PRIMARY KEY,
  task_id VARCHAR(40) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  source_kind VARCHAR(20) NOT NULL,
  source_ref TEXT NOT NULL,
  excerpt TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS change_sets (
  id VARCHAR(40) PRIMARY KEY,
  actor_type VARCHAR(20) NOT NULL,
  actor_id VARCHAR(80) NOT NULL,
  tool VARCHAR(80) NOT NULL,
  status VARCHAR(20) NOT NULL,
  summary_json JSONB NOT NULL,
  diff_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  committed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS change_actions (
  id VARCHAR(40) PRIMARY KEY,
  change_set_id VARCHAR(40) NOT NULL REFERENCES change_sets(id) ON DELETE CASCADE,
  action_index INTEGER NOT NULL DEFAULT 0,
  action_type VARCHAR(40) NOT NULL,
  payload_json JSONB NOT NULL,
  apply_result_json JSONB
);

CREATE TABLE IF NOT EXISTS commits (
  id VARCHAR(40) PRIMARY KEY,
  change_set_id VARCHAR(40) UNIQUE NOT NULL REFERENCES change_sets(id) ON DELETE CASCADE,
  committed_by_type VARCHAR(20) NOT NULL,
  committed_by_id VARCHAR(80) NOT NULL,
  committed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  client_request_id VARCHAR(120)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_commits_client_request_id
ON commits (client_request_id)
WHERE client_request_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS audit_events (
  id VARCHAR(40) PRIMARY KEY,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  actor_type VARCHAR(20) NOT NULL,
  actor_id VARCHAR(80) NOT NULL,
  tool VARCHAR(80) NOT NULL,
  action VARCHAR(80) NOT NULL,
  target_type VARCHAR(40) NOT NULL,
  target_id VARCHAR(40) NOT NULL,
  source_refs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  before_hash VARCHAR(128),
  after_hash VARCHAR(128),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);
