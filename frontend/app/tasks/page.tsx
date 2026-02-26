/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { TaskExecutionPanel } from "../../src/components/task-execution-panel";
import { apiDelete, apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";
type TaskPriority = "P0" | "P1" | "P2" | "P3";
type FilterPriority = TaskPriority | "all";
type FilterStatus = TaskStatus | "archived" | "all";
type DetailPriority = TaskPriority | "";

type Task = {
  id: string;
  title: string;
  description: string;
  acceptance_criteria: string;
  topic_id: string;
  status: TaskStatus;
  cancelled_reason?: string;
  priority?: TaskPriority;
  due?: string;
  source: string;
  cycle_id?: string;
  updated_at: string;
};

type TaskList = { items: Task[]; page: number; page_size: number; total: number };
type TaskBatchUpdateResp = { updated: number; failed: number; failures: Array<{ task_id: string; reason: string }> };
type TaskArchiveResp = { archived: number };
type Topic = {
  id: string;
  name: string;
  name_en: string;
  name_zh: string;
  kind: string;
  status: string;
  summary: string;
};
type TopicList = { items: Topic[] };
type DetailDraft = {
  title: string;
  status: TaskStatus;
  cancelled_reason: string;
  priority: DetailPriority;
  topic_id: string;
  description: string;
  acceptance_criteria: string;
};

const PRIORITY_FILTERS: FilterPriority[] = ["all", "P0", "P1", "P2", "P3"];
const STATUS_FILTERS: FilterStatus[] = ["all", "todo", "in_progress", "done", "cancelled", "archived"];
const STATUS_GROUP_ORDER: TaskStatus[] = ["todo", "in_progress", "done", "cancelled"];

export default function TasksPage() {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("P2");
  const [due, setDue] = useState("");
  const [source, setSource] = useState("ui://tasks");

  const [topics, setTopics] = useState<Topic[]>([]);
  const [createTopicId, setCreateTopicId] = useState("");

  const [filterPriority, setFilterPriority] = useState<FilterPriority>("all");
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("in_progress");
  const [filterTopicId, setFilterTopicId] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [detailDraft, setDetailDraft] = useState<DetailDraft | null>(null);
  const [ready, setReady] = useState(false);

  const { t, lang } = useI18n();

  const isArchivedView = filterStatus === "archived";
  const canBulkCancel = filterStatus === "all" || filterStatus === "todo" || filterStatus === "in_progress";
  const canArchiveFromView = filterStatus === "done" || filterStatus === "cancelled";

  const topicMap = useMemo(() => Object.fromEntries(topics.map((topic) => [topic.id, topic])), [topics]);

  const filteredTasks = useMemo(() => {
    const keyword = searchQuery.trim().toLowerCase();
    const source = tasks;
    if (!keyword) return source;
    return source.filter((task) => {
      const bucket = [
        task.id,
        task.title,
        task.description,
        task.acceptance_criteria
      ]
        .join(" ")
        .toLowerCase();
      return bucket.includes(keyword);
    });
  }, [tasks, searchQuery]);

  const groupedTasks = useMemo(
    () =>
      STATUS_GROUP_ORDER.map((status) => ({
        status,
        items: filteredTasks.filter((task) => task.status === status)
      })),
    [filteredTasks]
  );

  const visibleGroups = useMemo(
    () => groupedTasks.filter((group) => group.items.length > 0),
    [groupedTasks]
  );

  const selectedTask = useMemo(
    () => filteredTasks.find((task) => task.id === selectedTaskId) ?? filteredTasks[0] ?? null,
    [filteredTasks, selectedTaskId]
  );

  const allVisibleSelected = useMemo(
    () => filteredTasks.length > 0 && filteredTasks.every((task) => selectedIds.includes(task.id)),
    [filteredTasks, selectedIds]
  );

  useEffect(() => {
    void onLoadTopics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!ready) return;
    void onRefresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, filterPriority, filterStatus, filterTopicId]);

  useEffect(() => {
    if (isArchivedView) {
      setSelectedIds([]);
    }
  }, [isArchivedView]);

  useEffect(() => {
    setSelectedTaskId((prev) => {
      if (prev && filteredTasks.some((task) => task.id === prev)) return prev;
      return filteredTasks[0]?.id ?? null;
    });
  }, [filteredTasks]);

  useEffect(() => {
    if (!selectedTask) {
      setDetailDraft(null);
      return;
    }
    setDetailDraft({
      title: selectedTask.title,
      status: selectedTask.status,
      cancelled_reason: selectedTask.cancelled_reason ?? "",
      priority: selectedTask.priority ?? "",
      topic_id: selectedTask.topic_id,
      description: selectedTask.description,
      acceptance_criteria: selectedTask.acceptance_criteria
    });
  }, [selectedTask]);

  function localizeTopicName(topic?: Topic): string {
    if (!topic) return t("tasks.unknownTopic");
    const target = lang === "zh" ? topic.name_zh : topic.name_en;
    return target?.trim() || topic.name;
  }

  function buildDetailPatch(task: Task, draft: DetailDraft): Record<string, unknown> {
    const patch: Record<string, unknown> = {};
    const nextTitle = draft.title.trim();
    const currentPriority = task.priority ?? "";
    const currentCancelReason = task.cancelled_reason ?? "";
    const nextCancelReason = draft.cancelled_reason.trim();

    if (nextTitle !== task.title) patch.title = nextTitle;
    if (draft.status !== task.status) patch.status = draft.status;
    if (nextCancelReason !== currentCancelReason) patch.cancelled_reason = nextCancelReason || null;
    if (draft.priority !== currentPriority) patch.priority = draft.priority || null;
    if (draft.topic_id !== task.topic_id) patch.topic_id = draft.topic_id;
    if (draft.description !== task.description) patch.description = draft.description;
    if (draft.acceptance_criteria !== task.acceptance_criteria) patch.acceptance_criteria = draft.acceptance_criteria;
    return patch;
  }

  const detailPatch = useMemo(() => {
    if (!selectedTask || !detailDraft) return {};
    return buildDetailPatch(selectedTask, detailDraft);
  }, [selectedTask, detailDraft]);

  const detailDirty = useMemo(() => Object.keys(detailPatch).length > 0, [detailPatch]);

  function userErrorMessage(err: Error): string {
    const raw = err.message;
    if (raw.includes("TASK_INVALID_STATUS_TRANSITION")) return t("tasks.errTransition");
    if (raw.includes("TASK_NOT_FOUND")) return t("tasks.errNotFound");
    if (raw.includes("TASK_CANCEL_REASON_REQUIRED")) return t("tasks.errCancelReasonRequired");
    if (raw.includes("TOPIC_NOT_FOUND")) return t("tasks.errTopic");
    if (raw.includes("VALIDATION_ERROR")) return t("tasks.errValidation");
    return raw;
  }

  async function onLoadTopics() {
    setError("");
    try {
      const listed = await apiGet<TopicList>("/api/v1/topics");
      const activeItems = listed.items.filter((item) => item.status === "active");
      setTopics(activeItems);
      setCreateTopicId((prev) => prev || activeItems[0]?.id || "");
      setReady(true);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    }
  }

  async function onCreate() {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<Task>("/api/v1/tasks", {
        title,
        description: "",
        acceptance_criteria: "",
        topic_id: createTopicId,
        status: "todo",
        priority,
        due: due || undefined,
        source
      });
      setTitle("");
      setDue("");
      setNotice(t("tasks.noticeCreated"));
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onRefresh() {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: "1", page_size: "100" });
      if (filterPriority !== "all") params.set("priority", filterPriority);
      if (filterStatus === "archived") params.set("archived", "true");
      else if (filterStatus !== "all") params.set("status", filterStatus);
      if (filterTopicId !== "all") params.set("topic_id", filterTopicId);

      const listed = await apiGet<TaskList>(`/api/v1/tasks?${params.toString()}`);
      setTasks(listed.items);
      setTotal(listed.total);
      setSelectedIds((prev) => prev.filter((id) => listed.items.some((item) => item.id === id)));
      setSelectedTaskId((prev) => {
        if (prev && listed.items.some((item) => item.id === prev)) return prev;
        return listed.items[0]?.id ?? null;
      });
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onStatus(taskId: string, status: TaskStatus) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<Task>(`/api/v1/tasks/${taskId}`, { status });
      setNotice(`${t("tasks.noticeUpdated")}: ${t(`tasks.statusValue.${status}`)}`);
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  function onExecutionTaskStatusChange(taskId: string, status: TaskStatus) {
    setTasks((prev) => prev.map((task) => (task.id === taskId ? { ...task, status } : task)));
    if (selectedTaskId === taskId) {
      setDetailDraft((prev) => (prev ? { ...prev, status } : prev));
    }
  }

  async function onDelete(taskId: string) {
    if (!window.confirm(t("tasks.confirmDelete"))) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiDelete(`/api/v1/tasks/${taskId}`);
      setNotice(t("tasks.noticeDeleted"));
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onCancel(taskId: string) {
    const reason = window.prompt(t("tasks.promptCancelReason"))?.trim() ?? "";
    if (!reason) {
      setError(t("tasks.errCancelReasonRequired"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<Task>(`/api/v1/tasks/${taskId}`, { status: "cancelled", cancelled_reason: reason });
      setNotice(t("tasks.noticeCancelled"));
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onBulkCancel() {
    if (!selectedIds.length) return;
    const reason = window.prompt(t("tasks.promptBulkCancelReason"))?.trim() ?? "";
    if (!reason) {
      setError(t("tasks.errCancelReasonRequired"));
      return;
    }
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const result = await apiPost<TaskBatchUpdateResp>("/api/v1/tasks/batch-update", {
        task_ids: selectedIds,
        patch: {
          status: "cancelled",
          cancelled_reason: reason
        }
      });
      setNotice(`${t("tasks.noticeBulkCancelled")}: ${result.updated}, failed: ${result.failed}`);
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onSaveDetail() {
    if (!selectedTask || !detailDraft) return;
    if (!detailDraft.title.trim() || !detailDraft.topic_id) {
      setError(t("tasks.errValidation"));
      return;
    }
    if (detailDraft.status === "cancelled" && !detailDraft.cancelled_reason.trim()) {
      setError(t("tasks.errCancelReasonRequired"));
      return;
    }
    setError("");
    setNotice("");
    try {
      if (!detailDirty) {
        setNotice(t("tasks.noticeNoChange"));
        return;
      }
      const patch = { ...detailPatch };
      setLoading(true);
      await apiPatch<Task>(`/api/v1/tasks/${selectedTask.id}`, patch);
      setNotice(t("tasks.noticeDetailSaved"));
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onArchiveSelected() {
    if (!selectedIds.length) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const result = await apiPost<TaskArchiveResp>("/api/v1/tasks/archive-selected", { task_ids: selectedIds });
      setNotice(`${t("tasks.noticeArchived")}: ${result.archived}`);
      await onRefresh();
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  function onResetDetail() {
    if (!selectedTask) return;
    setDetailDraft({
      title: selectedTask.title,
      status: selectedTask.status,
      cancelled_reason: selectedTask.cancelled_reason ?? "",
      priority: selectedTask.priority ?? "",
      topic_id: selectedTask.topic_id,
      description: selectedTask.description,
      acceptance_criteria: selectedTask.acceptance_criteria
    });
    setError("");
    setNotice("");
  }

  function toggleSelected(taskId: string) {
    setSelectedIds((prev) => (prev.includes(taskId) ? prev.filter((id) => id !== taskId) : [...prev, taskId]));
  }

  function toggleSelectAllVisible() {
    if (allVisibleSelected) {
      setSelectedIds((prev) => prev.filter((id) => !filteredTasks.some((task) => task.id === id)));
      return;
    }
    setSelectedIds((prev) => {
      const merged = new Set(prev);
      filteredTasks.forEach((task) => merged.add(task.id));
      return Array.from(merged);
    });
  }

  function formatTime(value?: string) {
    if (!value) return "-";
    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  }

  return (
    <section className="card taskBoard taskBoardV3">
      <div className="taskCommandTop">
        <div>
          <h1 className="h1">{t("tasks.title")}</h1>
          <p className="meta">{t("tasks.subtitle")}</p>
        </div>
        <div className="taskHeroStat">
          <span className="meta">{t("tasks.total")}</span>
          <strong>{total}</strong>
        </div>
      </div>

      <div className="taskCommandCreateBar">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              void onCreate();
            }
          }}
          placeholder={t("tasks.placeholderTitle")}
          className="taskInput"
        />
        <select value={createTopicId} onChange={(e) => setCreateTopicId(e.target.value)} className="taskInput">
          {topics.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {localizeTopicName(topic)}
            </option>
          ))}
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value as TaskPriority)} className="taskInput">
          <option value="P0">P0</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
        </select>
        <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className="taskInput" />
        <button className="badge" onClick={onCreate} disabled={!title.trim() || !createTopicId || loading}>
          {t("tasks.create")}
        </button>
        <button className="badge" onClick={() => onRefresh()} disabled={loading}>
          {t("tasks.refresh")}
        </button>
      </div>

      <div className="taskCommandLayout">
        <aside className="taskFilterPanel taskFilterPanelCommand">
          <h2 className="changesSubTitle">{t("tasks.filtersTitle")}</h2>
          <label className="taskFilterItem taskFilterSearch">
            <span>{t("tasks.search")}</span>
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="taskInput"
              placeholder={t("tasks.searchPlaceholder")}
            />
          </label>
          <div className="taskFilterGrid">
            <label className="taskFilterItem">
              <span>{t("tasks.filterPriority")}</span>
              <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value as FilterPriority)} className="taskInput">
                {PRIORITY_FILTERS.map((item) => (
                  <option key={item} value={item}>
                    {item === "all" ? t("tasks.filterAll") : item}
                  </option>
                ))}
              </select>
            </label>

            <label className="taskFilterItem">
              <span>{t("tasks.filterStatus")}</span>
              <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value as FilterStatus)} className="taskInput">
                {STATUS_FILTERS.map((item) => (
                  <option key={item} value={item}>
                    {item === "all" ? t("tasks.filterAll") : t(`tasks.statusValue.${item}`)}
                  </option>
                ))}
              </select>
            </label>

            <label className="taskFilterItem">
              <span>{t("tasks.filterCategory")}</span>
              <select value={filterTopicId} onChange={(e) => setFilterTopicId(e.target.value)} className="taskInput">
                <option value="all">{t("tasks.filterAll")}</option>
                {topics.map((topic) => (
                  <option key={topic.id} value={topic.id}>
                    {localizeTopicName(topic)}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {!isArchivedView ? (
            <div className="taskBulkBar">
              <label className="meta" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={() => toggleSelectAllVisible()}
                  disabled={!filteredTasks.length || loading}
                />
                {t("tasks.selectAll")}
              </label>
              <span className="meta">{t("tasks.selected")}: {selectedIds.length}</span>
              {canBulkCancel ? (
                <button className="badge" disabled={loading || !selectedIds.length} onClick={onBulkCancel}>
                  {t("tasks.bulkCancel")}
                </button>
              ) : null}
              {canArchiveFromView ? (
                <button className="badge" disabled={loading || !selectedIds.length} onClick={onArchiveSelected}>
                  {t("tasks.archiveSelected")}
                </button>
              ) : null}
            </div>
          ) : (
            <p className="meta taskArchivedHint">{t("tasks.archivedReadOnly")}</p>
          )}

          {error ? <p className="meta taskErrorText">{error}</p> : null}
          {notice ? <p className="meta taskNoticeText">{notice}</p> : null}
        </aside>

        <section className="taskCommandListPanel">
          <div className="taskCommandListHead">
            <h2 className="changesSubTitle">{t("tasks.title")}</h2>
            <span className="meta">{filteredTasks.length} / {total}</span>
          </div>

          {visibleGroups.length ? (
            <div className="taskStatusGroupList">
              {visibleGroups.map((group) => (
                <section key={group.status} className="taskStatusGroup">
                  <div className="taskStatusGroupHead">
                    <span className="badge">{t(`tasks.statusValue.${group.status}`)}</span>
                    <span className="meta">{group.items.length}</span>
                  </div>
                  <div className="taskList taskListV3">
                    {group.items.map((task) => (
                      <div
                        key={task.id}
                        className={`taskRow ${selectedTaskId === task.id ? "taskRowActive" : ""}`}
                        onClick={() => setSelectedTaskId(task.id)}
                      >
                        {!isArchivedView ? (
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(task.id)}
                            onChange={(e) => {
                              e.stopPropagation();
                              toggleSelected(task.id);
                            }}
                            aria-label={`select ${task.title}`}
                          />
                        ) : null}
                        <div className="taskRowMain">
                          <div className="taskTitle">{task.title}</div>
                          <div className="taskMetaLine">
                            <span>{task.priority ?? "-"}</span>
                            <span>{localizeTopicName(topicMap[task.topic_id])}</span>
                            <span>{task.due ?? "-"}</span>
                            <span>{formatTime(task.updated_at)}</span>
                          </div>
                        </div>
                        {!isArchivedView ? (
                          <div className="taskQuickActions">
                            <button className="badge" onClick={(e) => { e.stopPropagation(); onStatus(task.id, "done"); }} disabled={loading}>{t("tasks.done")}</button>
                            <button
                              className="badge"
                              onClick={(e) => {
                                e.stopPropagation();
                                void onCancel(task.id);
                              }}
                              disabled={loading || task.status === "cancelled"}
                            >
                              {t("tasks.cancel")}
                            </button>
                            <button className="badge" onClick={(e) => { e.stopPropagation(); onDelete(task.id); }} disabled={loading}>{t("tasks.delete")}</button>
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <p className="meta">{t("tasks.empty")}</p>
          )}
        </section>

        <aside className="taskDetail taskCommandDetail">
          <h2 className="changesSubTitle">{t("tasks.detail")}</h2>
          {selectedTask ? (
            <div className="taskDetailContent">
              <div className="taskDetailTitle">{selectedTask.title}</div>
              <div className="meta">{selectedTask.id}</div>
              <div className="taskDetailGrid">
                <div>
                  <div className="changesSummaryKey">{t("tasks.updated")}</div>
                  <div className="changesLedgerText">{formatTime(selectedTask.updated_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.source")}</div>
                  <div className="changesLedgerText">{selectedTask.source}</div>
                </div>
              </div>
              <TaskExecutionPanel
                taskId={selectedTask.id}
                onTaskStarted={(status) => onExecutionTaskStatusChange(selectedTask.id, status)}
              />
              <div className="taskDetailEdit">
                {isArchivedView ? (
                  <div className="taskDetailForm">
                    <h3 className="changesGroupTitle">{t("tasks.readOnly")}</h3>
                    <p className="meta">{t("tasks.archivedReadOnly")}</p>
                    <div className="taskDetailGrid">
                      <div>
                        <div className="changesSummaryKey">{t("tasks.status")}</div>
                        <div className="changesLedgerText">{t(`tasks.statusValue.${selectedTask.status}`)}</div>
                      </div>
                      <div>
                        <div className="changesSummaryKey">{t("tasks.priority")}</div>
                        <div className="changesLedgerText">{selectedTask.priority ?? "-"}</div>
                      </div>
                      <div>
                        <div className="changesSummaryKey">{t("tasks.due")}</div>
                        <div className="changesLedgerText">{selectedTask.due ?? "-"}</div>
                      </div>
                      <div>
                        <div className="changesSummaryKey">{t("tasks.filterCategory")}</div>
                        <div className="changesLedgerText">{localizeTopicName(topicMap[selectedTask.topic_id])}</div>
                      </div>
                    </div>
                    {selectedTask.cancelled_reason ? (
                      <div className="taskField">
                        <span>{t("tasks.cancelReason")}</span>
                        <div className="changesLedgerText">{selectedTask.cancelled_reason}</div>
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <>
                    <h3 className="changesGroupTitle">{t("tasks.quickEdit")}</h3>
                    {detailDraft ? (
                      <div className="taskDetailForm">
                        <div className="taskDetailFormGrid taskDetailFormGridCore">
                          <label className="taskField">
                            <span>{t("tasks.status")}</span>
                            <select
                              value={detailDraft.status}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, status: e.target.value as TaskStatus } : prev))}
                              className="taskInput"
                            >
                              <option value="todo">{t("tasks.statusValue.todo")}</option>
                              <option value="in_progress">{t("tasks.statusValue.in_progress")}</option>
                              <option value="done">{t("tasks.statusValue.done")}</option>
                              <option value="cancelled">{t("tasks.statusValue.cancelled")}</option>
                            </select>
                          </label>

                          <label className="taskField">
                            <span>{t("tasks.priority")}</span>
                            <select
                              value={detailDraft.priority}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, priority: e.target.value as DetailPriority } : prev))}
                              className="taskInput"
                            >
                              <option value="">{t("tasks.none")}</option>
                              <option value="P0">P0</option>
                              <option value="P1">P1</option>
                              <option value="P2">P2</option>
                              <option value="P3">P3</option>
                            </select>
                          </label>

                          <label className="taskField">
                            <span>{t("tasks.filterCategory")}</span>
                            <select
                              value={detailDraft.topic_id}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, topic_id: e.target.value } : prev))}
                              className="taskInput"
                            >
                              {topics.map((topic) => (
                                <option key={topic.id} value={topic.id}>
                                  {localizeTopicName(topic)}
                                </option>
                              ))}
                            </select>
                          </label>

                          <label className="taskField taskFieldWide">
                            <span>{t("tasks.title")}</span>
                            <input
                              value={detailDraft.title}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, title: e.target.value } : prev))}
                              className="taskInput"
                            />
                          </label>

                          {detailDraft.status === "cancelled" ? (
                            <label className="taskField taskFieldWide">
                              <span>{t("tasks.cancelReason")}</span>
                              <textarea
                                value={detailDraft.cancelled_reason}
                                onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, cancelled_reason: e.target.value } : prev))}
                                placeholder={t("tasks.placeholderCancelReason")}
                                className="taskInput taskTextArea"
                                rows={2}
                              />
                            </label>
                          ) : null}

                          <label className="taskField taskFieldWide">
                            <span>{t("tasks.description")}</span>
                            <textarea
                              value={detailDraft.description}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, description: e.target.value } : prev))}
                              placeholder={t("tasks.placeholderDescription")}
                              className="taskInput taskTextArea"
                              rows={3}
                            />
                          </label>

                          <label className="taskField taskFieldWide">
                            <span>{t("tasks.acceptance")}</span>
                            <textarea
                              value={detailDraft.acceptance_criteria}
                              onChange={(e) => setDetailDraft((prev) => (prev ? { ...prev, acceptance_criteria: e.target.value } : prev))}
                              placeholder={t("tasks.placeholderAcceptance")}
                              className="taskInput taskTextArea"
                              rows={3}
                            />
                          </label>
                        </div>

                        <label className="taskField">
                          <span>{t("tasks.source")}</span>
                          <input value={selectedTask.source} disabled className="taskInput" />
                        </label>

                        <div className="taskDetailFormActions">
                          <button className="badge" onClick={onResetDetail} disabled={loading || !detailDirty}>
                            {t("tasks.resetDetail")}
                          </button>
                          <button className="badge" onClick={onSaveDetail} disabled={loading || !detailDirty}>
                            {t("tasks.saveDetail")}
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
            </div>
          ) : (
            <p className="meta">{t("tasks.pickOne")}</p>
          )}
        </aside>
      </div>
    </section>
  );
}
