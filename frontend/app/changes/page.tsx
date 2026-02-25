"use client";

import { useEffect, useMemo, useState } from "react";

import { apiDelete, apiGet, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type ChangeListItem = {
  change_set_id: string;
  status: string;
  actor: { type: string; id: string };
  tool: string;
  summary: Record<string, number>;
  actions_count: number;
  created_at: string;
  committed_at?: string | null;
};

type ChangeListResp = {
  items: ChangeListItem[];
  page: number;
  page_size: number;
  total: number;
};

type ChangeActionDetail = {
  action_id: string;
  action_index: number;
  action_type: string;
  payload: Record<string, unknown>;
  apply_result?: Record<string, unknown> | null;
};

type ChangeDetail = {
  change_set_id: string;
  status: string;
  actor: { type: string; id: string };
  tool: string;
  summary: Record<string, number>;
  diff_items: Array<{ entity: string; action: string; fields: string[]; text: string }>;
  created_at: string;
  committed_at?: string | null;
  actions: ChangeActionDetail[];
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

type AuditEventItem = {
  event_id: string;
  occurred_at: string;
  actor: { type: string; id: string };
  tool: string;
  action: string;
  target: { type: string; id: string };
  source_refs: string[];
  metadata?: Record<string, unknown>;
};
type AuditListResp = {
  items: AuditEventItem[];
  page: number;
  page_size: number;
  total: number;
};

const ENTITY_KEYS = ["creates", "updates", "duplicate_candidates", "task_create", "task_update", "note_append"];

const FIELD_LABELS: Record<string, string> = {
  field_title: "Title",
  field_status: "Status",
  field_priority: "Priority",
  field_due: "Due date",
  field_source: "Source",
  field_cycle_id: "Cycle",
  field_next_review_at: "Next review",
  field_blocked_by_task_id: "Blocked by",
  field_topic_id: "Category",
  field_task_type: "Task type"
};

function prettyFieldKey(key: string): string {
  if (FIELD_LABELS[key]) return FIELD_LABELS[key];
  if (!key.startsWith("field_")) return key;
  return key.replace(/^field_/, "").split("_").filter(Boolean).join(" ");
}

export default function ChangesPage() {
  const { t } = useI18n();

  const [list, setList] = useState<ChangeListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [detail, setDetail] = useState<ChangeDetail | null>(null);
  const [appliedEvents, setAppliedEvents] = useState<AuditEventItem[]>([]);
  const [commitResult, setCommitResult] = useState<CommitResp | null>(null);
  const [undoResult, setUndoResult] = useState<UndoResp | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [pending, setPending] = useState<"" | "refresh" | "detail" | "commit" | "undo" | "reject">("");

  const entitySummaryEntries = useMemo(
    () =>
      detail
        ? Object.entries(detail.summary)
            .filter(([key]) => ENTITY_KEYS.includes(key))
            .sort(([a], [b]) => a.localeCompare(b))
        : [],
    [detail]
  );
  const fieldSummaryEntries = useMemo(
    () =>
      detail
        ? Object.entries(detail.summary)
            .filter(([key]) => key.startsWith("field_"))
            .sort(([a], [b]) => a.localeCompare(b))
        : [],
    [detail]
  );

  useEffect(() => {
    void loadInbox();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    void loadDetail(selectedId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  async function loadInbox() {
    setError("");
    setNotice("");
    setPending("refresh");
    try {
      const listed = await apiGet<ChangeListResp>("/api/v1/changes?page=1&page_size=100&status=proposed");
      setList(listed.items);
      setSelectedId((prev) => {
        if (prev && listed.items.some((item) => item.change_set_id === prev)) return prev;
        return listed.items[0]?.change_set_id ?? "";
      });
      setCommitResult(null);
      setUndoResult(null);
      setAppliedEvents([]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function loadDetail(changeSetId: string) {
    setError("");
    setPending("detail");
    try {
      const row = await apiGet<ChangeDetail>(`/api/v1/changes/${changeSetId}`);
      setDetail(row);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function onCommitSelected() {
    if (!selectedId) {
      setError(t("changes.errNeedSelect"));
      return;
    }
    setError("");
    setNotice("");
    setPending("commit");
    try {
      const reqId = `ui-${Date.now()}`;
      const res = await apiPost<CommitResp>(`/api/v1/changes/${selectedId}/commit`, {
        approved_by: { type: "user", id: "usr_local" },
        client_request_id: reqId
      });
      setCommitResult(res);
      setNotice(t("changes.noticeCommitted"));
      await loadCommitAppliedEvents(res.commit_id);
      await loadInbox();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function onUndoLast() {
    setError("");
    setNotice("");
    setPending("undo");
    try {
      const res = await apiPost<UndoResp>("/api/v1/commits/undo-last", {
        requested_by: { type: "user", id: "usr_local" },
        reason: "rollback from changes UI",
        client_request_id: `ui-undo-${Date.now()}`
      });
      setUndoResult(res);
      setNotice(t("changes.noticeUndone"));
      await loadInbox();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function onRejectSelected() {
    if (!selectedId) {
      setError(t("changes.errNeedSelect"));
      return;
    }
    setError("");
    setNotice("");
    setPending("reject");
    try {
      await apiDelete(`/api/v1/changes/${selectedId}`);
      setNotice(t("changes.noticeRejected"));
      setCommitResult(null);
      setUndoResult(null);
      await loadInbox();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending("");
    }
  }

  async function loadCommitAppliedEvents(commitId: string) {
    const listed = await apiGet<AuditListResp>("/api/v1/audit/events?page=1&page_size=100&action=changes_apply_action");
    const rows = listed.items.filter((item) => (item.metadata?.commit_id as string | undefined) === commitId);
    setAppliedEvents(rows);
  }

  return (
    <section className="card">
      <h1 className="h1">{t("changes.title")}</h1>
      <p className="meta">{t("changes.subtitle")}</p>

      <div className="badges" style={{ marginTop: 12 }}>
        <button className="badge" onClick={() => loadInbox()} disabled={pending !== ""}>
          {pending === "refresh" ? `${t("changes.refreshInbox")}...` : t("changes.refreshInbox")}
        </button>
        <button className="badge" onClick={onCommitSelected} disabled={pending !== "" || !selectedId}>
          {pending === "commit" ? t("changes.pendingCommit") : t("changes.commitSelected")}
        </button>
        <button className="badge" onClick={onRejectSelected} disabled={pending !== "" || !selectedId}>
          {pending === "reject" ? t("changes.pendingReject") : t("changes.rejectSelected")}
        </button>
        <button className="badge" onClick={onUndoLast} disabled={pending !== ""}>
          {pending === "undo" ? t("changes.pendingUndo") : t("changes.undo")}
        </button>
      </div>

      {error ? <p className="meta" style={{ color: "var(--danger)", marginTop: 10 }}>{error}</p> : null}
      {notice ? <p className="meta" style={{ color: "var(--success)", marginTop: 10 }}>{notice}</p> : null}

      <div className="changesInboxLayout">
        <aside className="changesInboxList">
          <h2 className="changesSubTitle">{t("changes.title")}</h2>
          {!list.length ? <p className="meta">{t("changes.inboxEmpty")}</p> : null}
          {list.map((item) => (
            <button
              key={item.change_set_id}
              className={`changesInboxItem ${selectedId === item.change_set_id ? "changesInboxItemActive" : ""}`}
              onClick={() => setSelectedId(item.change_set_id)}
              disabled={pending !== ""}
            >
              <div className="changesInboxHead">
                <span className="changesChip changesChipAction">{item.status}</span>
                <span className="changesSummaryRawKey">{item.change_set_id}</span>
              </div>
              <div className="changesInboxMeta">
                <span>{t("changes.proposalCount")}: {item.actions_count}</span>
                <span>{t("changes.proposalActor")}: {item.actor.type}:{item.actor.id}</span>
                <span>{t("changes.proposalTool")}: {item.tool}</span>
                <span>{t("changes.proposalCreatedAt")}: {new Date(item.created_at).toLocaleString()}</span>
              </div>
            </button>
          ))}
        </aside>

        <div className="changesInboxDetail">
          {!detail ? (
            <p className="meta">{t("changes.selectProposal")}</p>
          ) : (
            <>
              <div className="changesResult changesResultCommit">
                <div className="changesResultGrid">
                  <div>
                    <div className="changesSummaryKey">change_set_id</div>
                    <div className="changesLedgerText">{detail.change_set_id}</div>
                  </div>
                  <div>
                    <div className="changesSummaryKey">{t("changes.proposalActor")}</div>
                    <div className="changesLedgerText">{detail.actor.type}:{detail.actor.id}</div>
                  </div>
                  <div>
                    <div className="changesSummaryKey">{t("changes.proposalTool")}</div>
                    <div className="changesLedgerText">{detail.tool}</div>
                  </div>
                  <div>
                    <div className="changesSummaryKey">{t("changes.proposalCreatedAt")}</div>
                    <div className="changesLedgerText">{new Date(detail.created_at).toLocaleString()}</div>
                  </div>
                </div>
              </div>

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
              </div>

              <div className="changesBlock">
                <h2 className="changesSubTitle">{t("changes.diffLedger")}</h2>
                {detail.diff_items.length ? (
                  <div className="changesLedger">
                    {detail.diff_items.map((item, idx) => (
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
                  <p className="changesLedgerText">{t("changes.noTaskChanges")}</p>
                )}
              </div>

              <div className="changesBlock">
                <h2 className="changesSubTitle">{t("changes.appliedActions")}</h2>
                {appliedEvents.length ? (
                  <div className="changesLedger">
                    {appliedEvents.map((item) => (
                      <article key={item.event_id} className="changesLedgerItem">
                        <div className="changesLedgerHead">
                          <span className="changesChip changesChipEntity">{item.target.type}</span>
                          <span className="changesChip changesChipAction">
                            {(item.metadata?.action_type as string | undefined) ?? item.action}
                          </span>
                        </div>
                        <p className="changesLedgerText">{item.target.id}</p>
                        <div className="changesFieldRow">
                          <span className="changesFieldChip">
                            idx: {(item.metadata?.action_index as number | undefined) ?? "-"}
                          </span>
                          <span className="changesFieldChip">{new Date(item.occurred_at).toLocaleString()}</span>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="changesLedgerText">{t("changes.noAppliedActions")}</p>
                )}
              </div>

              {commitResult ? (
                <div className="changesResult changesResultCommit">
                  <h2 className="changesSubTitle">{t("changes.commitResult")}</h2>
                  <div className="changesResultGrid">
                    <div>
                      <div className="changesSummaryKey">commit_id</div>
                      <div className="changesLedgerText">{commitResult.commit_id}</div>
                    </div>
                    <div>
                      <div className="changesSummaryKey">change_set_id</div>
                      <div className="changesLedgerText">{commitResult.change_set_id}</div>
                    </div>
                    <div>
                      <div className="changesSummaryKey">status</div>
                      <div className="changesLedgerText">{commitResult.status}</div>
                    </div>
                    <div>
                      <div className="changesSummaryKey">committed_at</div>
                      <div className="changesLedgerText">{commitResult.committed_at}</div>
                    </div>
                  </div>
                </div>
              ) : null}

              {undoResult ? (
                <div className="changesResult changesResultUndo">
                  <h2 className="changesSubTitle">{t("changes.undoResult")}</h2>
                  <div className="changesResultGrid">
                    <div>
                      <div className="changesSummaryKey">undone_commit_id</div>
                      <div className="changesLedgerText">{undoResult.undone_commit_id}</div>
                    </div>
                    <div>
                      <div className="changesSummaryKey">revert_commit_id</div>
                      <div className="changesLedgerText">{undoResult.revert_commit_id}</div>
                    </div>
                    <div>
                      <div className="changesSummaryKey">status</div>
                      <div className="changesLedgerText">{undoResult.status}</div>
                    </div>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
