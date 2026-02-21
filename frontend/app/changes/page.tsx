"use client";

import { useMemo, useState } from "react";

import { apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type DryRunResp = {
  change_set_id: string;
  summary: Record<string, number>;
  diff: string[];
  diff_items?: Array<{
    entity: string;
    action: string;
    fields: string[];
    text: string;
  }>;
  status: "proposed";
};

type CommitResp = {
  commit_id: string;
  change_set_id: string;
  status: "committed";
  committed_at: string;
};

type UndoResp = {
  undone_commit_id: string;
  revert_commit_id: string;
  status: "reverted";
};

const FIELD_LABELS: Record<string, string> = {
  field_title: "Title",
  field_status: "Status",
  field_priority: "Priority",
  field_due: "Due date",
  field_project: "Project",
  field_source: "Source",
  field_cycle_id: "Cycle",
  field_next_review_at: "Next review",
  field_blocked_by_task_id: "Blocked by"
};

function prettyFieldKey(key: string): string {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  if (!key.startsWith("field_")) return key;
  return key
    .replace(/^field_/, "")
    .split("_")
    .filter(Boolean)
    .join(" ");
}

const defaultActions = JSON.stringify(
  [
    {
      type: "create_task",
      payload: {
        title: "Review weekly plan",
        status: "todo",
        priority: "P2",
        source: "chat://session/local"
      }
    }
  ],
  null,
  2
);

export default function ChangesPage() {
  const [actionsInput, setActionsInput] = useState(defaultActions);
  const [dryRun, setDryRun] = useState<DryRunResp | null>(null);
  const [commit, setCommit] = useState<CommitResp | null>(null);
  const [undo, setUndo] = useState<UndoResp | null>(null);
  const [error, setError] = useState<string>("");
  const [pending, setPending] = useState<"dry" | "commit" | "undo" | "">("");
  const [taskOnly, setTaskOnly] = useState(false);
  const { t } = useI18n();

  const canCommit = useMemo(() => !!dryRun?.change_set_id, [dryRun]);
  const summaryEntries = useMemo(
    () =>
      dryRun
        ? Object.entries(dryRun.summary).sort(([a], [b]) => a.localeCompare(b))
        : [],
    [dryRun]
  );
  const entitySummaryEntries = useMemo(
    () =>
      summaryEntries.filter(([key]) =>
        ["creates", "updates", "duplicate_candidates", "task_create", "task_update", "note_append"].includes(
          key
        )
      ),
    [summaryEntries]
  );
  const fieldSummaryEntries = useMemo(
    () => summaryEntries.filter(([key]) => key.startsWith("field_")),
    [summaryEntries]
  );
  const filteredDiffItems = useMemo(() => {
    const items = dryRun?.diff_items ?? [];
    if (!taskOnly) return items;
    return items.filter((item) => item.entity === "task");
  }, [dryRun, taskOnly]);

  async function onDryRun() {
    setError("");
    setPending("dry");
    try {
      const actions = JSON.parse(actionsInput);
      const res = await apiPost<DryRunResp>("/api/v1/changes/dry-run", {
        actions,
        actor: { type: "agent", id: "openclaw" },
        tool: "openclaw-skill"
      });
      setDryRun(res);
      setCommit(null);
      setUndo(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function onCommit() {
    if (!dryRun) return;
    setError("");
    setPending("commit");
    try {
      const res = await apiPost<CommitResp>(
        `/api/v1/changes/${dryRun.change_set_id}/commit`,
        { approved_by: { type: "user", id: "usr_local" } }
      );
      setCommit(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function onUndoLast() {
    setError("");
    setPending("undo");
    try {
      const res = await apiPost<UndoResp>("/api/v1/commits/undo-last", {
        requested_by: { type: "user", id: "usr_local" },
        reason: "rollback from changes UI"
      });
      setUndo(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  return (
    <section className="card">
      <h1 className="h1">{t("changes.title")}</h1>
      <p className="meta">{t("changes.subtitle")}</p>

      <label htmlFor="actions-json" className="meta" style={{ display: "block", marginTop: 12 }}>
        {t("changes.actionsJson")}
      </label>
      <textarea
        id="actions-json"
        value={actionsInput}
        onChange={(e) => setActionsInput(e.target.value)}
        rows={12}
        style={{ width: "100%", marginTop: 8, border: "2px solid var(--line)", borderRadius: 10, padding: 10, fontFamily: "IBM Plex Mono, monospace" }}
      />

      <div className="badges" style={{ marginTop: 14 }}>
        <button className="badge" onClick={onDryRun} disabled={pending !== ""}>
          {pending === "dry" ? t("changes.pendingDry") : t("changes.dryRun")}
        </button>
        <button className="badge" onClick={onCommit} disabled={!canCommit || pending !== ""}>
          {pending === "commit" ? t("changes.pendingCommit") : t("changes.commit")}
        </button>
        <button className="badge" onClick={onUndoLast} disabled={pending !== ""}>
          {pending === "undo" ? t("changes.pendingUndo") : t("changes.undo")}
        </button>
      </div>

      {error ? <p className="meta" style={{ color: "var(--danger)", marginTop: 12 }}>{error}</p> : null}

      {dryRun ? (
        <div className="changesBlock">
          <h2 className="changesSubTitle">{t("changes.summary")}</h2>
          <h3 className="changesGroupTitle">{t("changes.entity")}</h3>
          <div className="changesSummaryGrid">
            {entitySummaryEntries.map(([key, value]) => (
              <div key={key} className="changesSummaryCard">
                <div className="changesSummaryKey">{key}</div>
                <div className="changesSummaryValue">{value}</div>
              </div>
            ))}
          </div>
          <h3 className="changesGroupTitle">{t("changes.fields")}</h3>
          <div className="changesSummaryGrid">
            {fieldSummaryEntries.length ? (
              fieldSummaryEntries.map(([key, value]) => (
                <div key={key} className="changesSummaryCard">
                  <div className="changesSummaryKey">{prettyFieldKey(key)}</div>
                  <div className="changesSummaryRawKey">{key}</div>
                  <div className="changesSummaryValue">{value}</div>
                </div>
              ))
            ) : (
              <div className="changesSummaryCard">
                <div className="changesSummaryKey">{t("changes.fieldChanges")}</div>
                <div className="changesSummaryValue">0</div>
              </div>
            )}
          </div>

          <h2 className="changesSubTitle">{t("changes.diffLedger")}</h2>
          <label className="changesToggle">
            <input
              type="checkbox"
              checked={taskOnly}
              onChange={(e) => setTaskOnly(e.target.checked)}
            />
            {t("changes.taskOnly")}
          </label>
          {filteredDiffItems.length ? (
            <div className="changesLedger">
              {filteredDiffItems.map((item, idx) => (
                <article key={`${item.entity}-${item.action}-${idx}`} className="changesLedgerItem">
                  <div className="changesLedgerHead">
                    <span className="changesChip changesChipEntity">{item.entity}</span>
                    <span className="changesChip changesChipAction">{item.action}</span>
                  </div>
                  <p className="changesLedgerText">{item.text}</p>
                  <div className="changesFieldRow">
                    {item.fields.map((field) => (
                      <span key={field} className="changesFieldChip" title={field}>
                        {prettyFieldKey(`field_${field.replace(/^field_/, "")}`)}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="changesLedgerFallback">
              {(taskOnly ? [] : dryRun.diff).map((line) => (
                <p key={line} className="changesLedgerText">
                  {line}
                </p>
              ))}
              {taskOnly ? <p className="changesLedgerText">{t("changes.noTaskChanges")}</p> : null}
            </div>
          )}
        </div>
      ) : null}

      {commit ? (
        <div className="changesResult changesResultCommit">
          <h2 className="changesSubTitle">{t("changes.commitResult")}</h2>
          <div className="changesResultGrid">
            <div>
              <div className="changesSummaryKey">commit_id</div>
              <div className="changesLedgerText">{commit.commit_id}</div>
            </div>
            <div>
              <div className="changesSummaryKey">change_set_id</div>
              <div className="changesLedgerText">{commit.change_set_id}</div>
            </div>
            <div>
              <div className="changesSummaryKey">status</div>
              <div className="changesLedgerText">{commit.status}</div>
            </div>
            <div>
              <div className="changesSummaryKey">committed_at</div>
              <div className="changesLedgerText">{commit.committed_at}</div>
            </div>
          </div>
        </div>
      ) : null}

      {undo ? (
        <div className="changesResult changesResultUndo">
          <h2 className="changesSubTitle">{t("changes.undoResult")}</h2>
          <div className="changesResultGrid">
            <div>
              <div className="changesSummaryKey">undone_commit_id</div>
              <div className="changesLedgerText">{undo.undone_commit_id}</div>
            </div>
            <div>
              <div className="changesSummaryKey">revert_commit_id</div>
              <div className="changesLedgerText">{undo.revert_commit_id}</div>
            </div>
            <div>
              <div className="changesSummaryKey">status</div>
              <div className="changesLedgerText">{undo.status}</div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
