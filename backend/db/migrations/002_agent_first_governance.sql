-- Agent-First governance schema

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

ALTER TABLE topics ADD COLUMN IF NOT EXISTS name_en VARCHAR(120);
ALTER TABLE topics ADD COLUMN IF NOT EXISTS name_zh VARCHAR(120);
UPDATE topics SET name_en = name WHERE name_en IS NULL OR BTRIM(name_en) = '';
UPDATE topics SET name_zh = name WHERE name_zh IS NULL OR BTRIM(name_zh) = '';
ALTER TABLE topics ALTER COLUMN name_en SET NOT NULL;
ALTER TABLE topics ALTER COLUMN name_zh SET NOT NULL;

INSERT INTO topics (id, name, name_en, name_zh, kind, status, summary)
VALUES
  ('top_fx_product_strategy', 'Product & Strategy', 'Product & Strategy', '产品与战略', 'domain', 'active', 'Business direction, priorities, and decision framing.'),
  ('top_fx_engineering_arch', 'Engineering & Architecture', 'Engineering & Architecture', '工程与架构', 'domain', 'active', 'System design, implementation, code quality, and technical debt.'),
  ('top_fx_operations_delivery', 'Operations & Delivery', 'Operations & Delivery', '运营与交付', 'domain', 'active', 'Execution workflows, delivery coordination, and operational runbooks.'),
  ('top_fx_growth_marketing', 'Growth & Marketing', 'Growth & Marketing', '增长与营销', 'domain', 'active', 'Acquisition, positioning, messaging, and user growth loops.'),
  ('top_fx_finance_legal', 'Finance & Legal', 'Finance & Legal', '财务与法务', 'domain', 'active', 'Budgeting, contracts, compliance, and risk control.'),
  ('top_fx_learning_research', 'Learning & Research', 'Learning & Research', '学习与研究', 'domain', 'active', 'Research findings, experiments, and knowledge exploration.'),
  ('top_fx_other', 'Other', 'Other', '其他', 'domain', 'active', 'Fallback bucket for uncategorized items pending review.')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    name_zh = EXCLUDED.name_zh,
    kind = EXCLUDED.kind,
    status = 'active',
    summary = EXCLUDED.summary;

CREATE TABLE IF NOT EXISTS topic_aliases (
  id VARCHAR(40) PRIMARY KEY,
  topic_id VARCHAR(40) NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
  alias VARCHAR(120) NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
  task_id VARCHAR(40),
  topic_id VARCHAR(40),
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

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS acceptance_criteria TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS topic_id VARCHAR(40);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS cancelled_reason TEXT;
ALTER TABLE notes ADD COLUMN IF NOT EXISTS topic_id VARCHAR(40);
ALTER TABLE notes ADD COLUMN IF NOT EXISTS status VARCHAR(20);
UPDATE notes SET status = 'active' WHERE status IS NULL;

UPDATE tasks SET description = '' WHERE description IS NULL;
UPDATE tasks SET acceptance_criteria = '' WHERE acceptance_criteria IS NULL;

INSERT INTO topics (id, name, name_en, name_zh, kind, status, summary)
VALUES (
  'top_legacy',
  'Legacy / Uncategorized',
  'Legacy / Uncategorized',
  'Legacy / Uncategorized',
  'domain',
  'archived',
  'Auto-created for backfill'
)
ON CONFLICT (id) DO NOTHING;

UPDATE topics SET status = 'archived' WHERE id = 'top_legacy';

UPDATE tasks t
SET topic_id = 'top_fx_engineering_arch'
FROM topics p
WHERE t.topic_id = p.id
  AND p.id NOT IN (
    'top_fx_product_strategy',
    'top_fx_engineering_arch',
    'top_fx_operations_delivery',
    'top_fx_growth_marketing',
    'top_fx_finance_legal',
    'top_fx_learning_research',
    'top_fx_other'
  )
  AND p.name IN ('Agent Platform Architecture', 'Skill Ecosystem & Tooling');

UPDATE tasks t
SET topic_id = 'top_fx_operations_delivery'
FROM topics p
WHERE t.topic_id = p.id
  AND p.id NOT IN (
    'top_fx_product_strategy',
    'top_fx_engineering_arch',
    'top_fx_operations_delivery',
    'top_fx_growth_marketing',
    'top_fx_finance_legal',
    'top_fx_learning_research',
    'top_fx_other'
  )
  AND p.name IN ('OpenClaw Operations', 'BridgeTalk Delivery');

UPDATE tasks t
SET topic_id = 'top_fx_product_strategy'
FROM topics p
WHERE t.topic_id = p.id
  AND p.id NOT IN (
    'top_fx_product_strategy',
    'top_fx_engineering_arch',
    'top_fx_operations_delivery',
    'top_fx_growth_marketing',
    'top_fx_finance_legal',
    'top_fx_learning_research',
    'top_fx_other'
  )
  AND p.name IN ('Agent-First Discovery', 'Opportunity Validation', 'Solo Company OS');

UPDATE tasks t
SET topic_id = 'top_fx_growth_marketing'
FROM topics p
WHERE t.topic_id = p.id
  AND p.id NOT IN (
    'top_fx_product_strategy',
    'top_fx_engineering_arch',
    'top_fx_operations_delivery',
    'top_fx_growth_marketing',
    'top_fx_finance_legal',
    'top_fx_learning_research',
    'top_fx_other'
  )
  AND p.name IN ('Brand & Naming');

UPDATE tasks t
SET topic_id = 'top_fx_learning_research'
FROM topics p
WHERE t.topic_id = p.id
  AND p.id NOT IN (
    'top_fx_product_strategy',
    'top_fx_engineering_arch',
    'top_fx_operations_delivery',
    'top_fx_growth_marketing',
    'top_fx_finance_legal',
    'top_fx_learning_research',
    'top_fx_other'
  )
  AND p.name IN ('Quant Workflow');

UPDATE tasks
SET topic_id = 'top_fx_other'
WHERE topic_id IS NULL
   OR topic_id NOT IN (
     'top_fx_product_strategy',
     'top_fx_engineering_arch',
     'top_fx_operations_delivery',
     'top_fx_growth_marketing',
     'top_fx_finance_legal',
     'top_fx_learning_research',
     'top_fx_other'
   );

UPDATE topics
SET status = 'archived'
WHERE id NOT IN (
  'top_fx_product_strategy',
  'top_fx_engineering_arch',
  'top_fx_operations_delivery',
  'top_fx_growth_marketing',
  'top_fx_finance_legal',
  'top_fx_learning_research',
  'top_fx_other'
);

ALTER TABLE tasks ALTER COLUMN description SET DEFAULT '';
ALTER TABLE tasks ALTER COLUMN acceptance_criteria SET DEFAULT '';
ALTER TABLE tasks ALTER COLUMN description SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN acceptance_criteria SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN topic_id SET NOT NULL;
ALTER TABLE tasks DROP COLUMN IF EXISTS next_action;
ALTER TABLE tasks DROP COLUMN IF EXISTS task_type;
ALTER TABLE tasks DROP COLUMN IF EXISTS blocked_by_task_id;
ALTER TABLE tasks DROP COLUMN IF EXISTS next_review_at;
ALTER TABLE tasks DROP COLUMN IF EXISTS project;
ALTER TABLE notes ALTER COLUMN status SET DEFAULT 'active';
ALTER TABLE notes ALTER COLUMN status SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_tasks_topic_id'
  ) THEN
    ALTER TABLE tasks
      ADD CONSTRAINT fk_tasks_topic_id
      FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE RESTRICT;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_notes_topic_id'
  ) THEN
    ALTER TABLE notes
      ADD CONSTRAINT fk_notes_topic_id
      FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS task_sources (
  id VARCHAR(40) PRIMARY KEY,
  task_id VARCHAR(40) NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  source_kind VARCHAR(20) NOT NULL,
  source_ref TEXT NOT NULL,
  excerpt TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_journal_items_task_id'
  ) THEN
    ALTER TABLE journal_items
      ADD CONSTRAINT fk_journal_items_task_id
      FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_journal_items_topic_id'
  ) THEN
    ALTER TABLE journal_items
      ADD CONSTRAINT fk_journal_items_topic_id
      FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'change_sets'
  ) THEN
    CREATE TABLE IF NOT EXISTS change_actions (
      id VARCHAR(40) PRIMARY KEY,
      change_set_id VARCHAR(40) NOT NULL REFERENCES change_sets(id) ON DELETE CASCADE,
      action_index INTEGER NOT NULL DEFAULT 0,
      action_type VARCHAR(40) NOT NULL,
      payload_json JSONB NOT NULL,
      apply_result_json JSONB
    );

    ALTER TABLE change_actions ADD COLUMN IF NOT EXISTS action_index INTEGER;
    UPDATE change_actions SET action_index = 0 WHERE action_index IS NULL;
    ALTER TABLE change_actions ALTER COLUMN action_index SET DEFAULT 0;
    ALTER TABLE change_actions ALTER COLUMN action_index SET NOT NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'commits'
  ) THEN
    WITH ranked AS (
      SELECT
        id,
        ROW_NUMBER() OVER (
          PARTITION BY client_request_id
          ORDER BY committed_at DESC, id DESC
        ) AS rn
      FROM commits
      WHERE client_request_id IS NOT NULL
    )
    UPDATE commits c
    SET client_request_id = NULL
    FROM ranked r
    WHERE c.id = r.id
      AND r.rn > 1;

    CREATE UNIQUE INDEX IF NOT EXISTS ux_commits_client_request_id
    ON commits (client_request_id)
    WHERE client_request_id IS NOT NULL;
  END IF;
END $$;
