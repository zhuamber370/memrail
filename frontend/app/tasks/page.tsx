/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type TaskView = "today" | "overdue" | "this_week" | "backlog" | "blocked" | "done";

type Task = {
  id: string;
  title: string;
  status: "todo" | "in_progress" | "done" | "cancelled";
  priority?: "P0" | "P1" | "P2" | "P3";
  due?: string;
  project?: string;
  source: string;
  cycle_id?: string;
  blocked_by_task_id?: string;
  next_review_at?: string;
  updated_at: string;
};

type TaskList = { items: Task[]; page: number; page_size: number; total: number };
type TaskViewsSummary = Record<TaskView, number>;
type TaskBatchUpdateResp = { updated: number; failed: number; failures: Array<{ task_id: string; reason: string }> };

const VIEWS: TaskView[] = ["today", "overdue", "this_week", "backlog", "blocked", "done"];

export default function TasksPage() {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<"P0" | "P1" | "P2" | "P3">("P2");
  const [project, setProject] = useState("");
  const [due, setDue] = useState("");
  const [source, setSource] = useState("ui://tasks");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [summary, setSummary] = useState<TaskViewsSummary>({
    today: 0,
    overdue: 0,
    this_week: 0,
    backlog: 0,
    blocked: 0,
    done: 0
  });
  const [view, setView] = useState<TaskView>("today");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [bulkPriority, setBulkPriority] = useState<"P0" | "P1" | "P2" | "P3">("P2");
  const [bulkStatus, setBulkStatus] = useState<"todo" | "in_progress" | "done" | "cancelled">("in_progress");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [detailProject, setDetailProject] = useState("");
  const [detailDue, setDetailDue] = useState("");
  const { t } = useI18n();

  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) ?? null,
    [tasks, selectedTaskId]
  );

  useEffect(() => {
    onRefresh(view);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    setDetailProject(selectedTask?.project ?? "");
    setDetailDue(selectedTask?.due ?? "");
  }, [selectedTaskId, selectedTask?.project, selectedTask?.due]);

  function userErrorMessage(err: Error): string {
    const raw = err.message;
    if (raw.includes("TASK_INVALID_STATUS_TRANSITION")) return t("tasks.errTransition");
    if (raw.includes("TASK_NOT_FOUND")) return t("tasks.errNotFound");
    if (raw.includes("VALIDATION_ERROR")) return t("tasks.errValidation");
    return raw;
  }

  async function onCreate() {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<Task>("/api/v1/tasks", {
        title,
        status: "todo",
        priority,
        due: due || undefined,
        project: project || undefined,
        source
      });
      setTitle("");
      setProject("");
      setDue("");
      setNotice(t("tasks.noticeCreated"));
      await onRefresh(view);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onRefresh(nextView: TaskView) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const listed = await apiGet<TaskList>(
        `/api/v1/tasks?page=1&page_size=50&view=${encodeURIComponent(nextView)}`
      );
      const counts = await apiGet<TaskViewsSummary>("/api/v1/tasks/views/summary");
      setTasks(listed.items);
      setSummary(counts);
      setSelectedIds((prev) => prev.filter((id) => listed.items.some((item) => item.id === id)));
      setSelectedTaskId((prev) => prev ?? listed.items[0]?.id ?? null);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onStatus(taskId: string, status: Task["status"]) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPatch<Task>(`/api/v1/tasks/${taskId}`, { status });
      setNotice(`${t("tasks.noticeUpdated")}: ${status}`);
      await onRefresh(view);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onReopen(taskId: string) {
    setError("");
    setNotice("");
    setLoading(true);
    try {
      await apiPost<Task>(`/api/v1/tasks/${taskId}/reopen`, {});
      setNotice(t("tasks.noticeReopened"));
      await onRefresh(view);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onBulkUpdate(payload: Record<string, unknown>) {
    if (!selectedIds.length) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const result = await apiPost<TaskBatchUpdateResp>("/api/v1/tasks/batch-update", {
        task_ids: selectedIds,
        patch: payload
      });
      setNotice(`${t("tasks.noticeBulk")}: ${result.updated}, failed: ${result.failed}`);
      await onRefresh(view);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  async function onSaveDetail() {
    if (!selectedTask) return;
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const patch: Record<string, unknown> = {};
      const normalizedProject = detailProject.trim();
      if (normalizedProject !== (selectedTask.project ?? "")) {
        patch.project = normalizedProject || null;
      }
      if (detailDue && detailDue !== (selectedTask.due ?? "")) {
        patch.due = detailDue;
      } else if (!detailDue && (selectedTask.due ?? "")) {
        patch.due = null;
      }
      if (!Object.keys(patch).length) {
        setNotice(t("tasks.noticeNoChange"));
        setLoading(false);
        return;
      }
      await apiPatch<Task>(`/api/v1/tasks/${selectedTask.id}`, patch);
      setNotice(t("tasks.noticeDetailSaved"));
      await onRefresh(view);
    } catch (e) {
      setError(userErrorMessage(e as Error));
    } finally {
      setLoading(false);
    }
  }

  function toggleSelected(taskId: string) {
    setSelectedIds((prev) => (prev.includes(taskId) ? prev.filter((id) => id !== taskId) : [...prev, taskId]));
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
    <section className="card taskBoard">
      <h1 className="h1">{t("tasks.title")}</h1>
      <p className="meta">{t("tasks.subtitle")}</p>

      <div className="taskViewTabs">
        {VIEWS.map((item) => (
          <button
            key={item}
            className={`badge ${view === item ? "taskViewTabActive" : ""}`}
            onClick={() => setView(item)}
            disabled={loading}
          >
            {t(`tasks.view.${item}`)} ({summary[item] ?? 0})
          </button>
        ))}
      </div>

      <div className="taskLayout">
        <div>
          <div className="taskCreateRow">
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("tasks.placeholderTitle")}
              className="taskInput"
            />
            <select value={priority} onChange={(e) => setPriority(e.target.value as typeof priority)} className="taskInput">
              <option value="P0">P0</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
            </select>
            <input value={project} onChange={(e) => setProject(e.target.value)} placeholder={t("tasks.placeholderProject")} className="taskInput" />
            <input type="date" value={due} onChange={(e) => setDue(e.target.value)} className="taskInput" />
            <button className="badge" onClick={onCreate} disabled={!title.trim() || loading}>
              {t("tasks.create")}
            </button>
            <button className="badge" onClick={() => onRefresh(view)} disabled={loading}>
              {t("tasks.refresh")}
            </button>
          </div>

          <div className="taskBulkBar">
            <div className="meta">{t("tasks.selected")}: {selectedIds.length}</div>
            <select value={bulkPriority} onChange={(e) => setBulkPriority(e.target.value as typeof bulkPriority)} className="taskInput">
              <option value="P0">P0</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
            </select>
            <button className="badge" disabled={!selectedIds.length || loading} onClick={() => onBulkUpdate({ priority: bulkPriority })}>
              {t("tasks.bulkPriority")}
            </button>
            <select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value as typeof bulkStatus)} className="taskInput">
              <option value="todo">todo</option>
              <option value="in_progress">in_progress</option>
              <option value="done">done</option>
              <option value="cancelled">cancelled</option>
            </select>
            <button className="badge" disabled={!selectedIds.length || loading} onClick={() => onBulkUpdate({ status: bulkStatus })}>
              {t("tasks.bulkStatus")}
            </button>
          </div>

          {error ? <p className="meta" style={{ color: "var(--danger)", marginTop: 10 }}>{error}</p> : null}
          {notice ? <p className="meta" style={{ color: "var(--success)", marginTop: 10 }}>{notice}</p> : null}

          <div className="taskList">
            {tasks.map((task) => (
              <div key={task.id} className={`taskRow ${selectedTaskId === task.id ? "taskRowActive" : ""}`} onClick={() => setSelectedTaskId(task.id)}>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(task.id)}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleSelected(task.id);
                  }}
                  aria-label={`select ${task.title}`}
                />
                <div className="taskRowMain">
                  <div className="taskTitle">{task.title}</div>
                  <div className="meta">
                    {task.status} | {task.priority ?? "-"} | {task.project ?? "-"}
                  </div>
                </div>
                <div className="taskQuickActions">
                  <button className="badge" onClick={(e) => { e.stopPropagation(); onStatus(task.id, "in_progress"); }} disabled={loading}>{t("tasks.start")}</button>
                  <button className="badge" onClick={(e) => { e.stopPropagation(); onStatus(task.id, "done"); }} disabled={loading}>{t("tasks.done")}</button>
                  <button className="badge" onClick={(e) => { e.stopPropagation(); onReopen(task.id); }} disabled={loading}>{t("tasks.reopen")}</button>
                </div>
              </div>
            ))}
            {!tasks.length ? <p className="meta">{t("tasks.empty")}</p> : null}
          </div>
        </div>

        <aside className="taskDetail">
          <h2 className="changesSubTitle">{t("tasks.detail")}</h2>
          {selectedTask ? (
            <div className="taskDetailContent">
              <div className="taskDetailTitle">{selectedTask.title}</div>
              <div className="meta">{selectedTask.id}</div>
              <div className="taskDetailGrid">
                <div>
                  <div className="changesSummaryKey">{t("tasks.status")}</div>
                  <div className="changesLedgerText">{selectedTask.status}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.priority")}</div>
                  <div className="changesLedgerText">{selectedTask.priority ?? "-"}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.project")}</div>
                  <div className="changesLedgerText">{selectedTask.project ?? "-"}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.due")}</div>
                  <div className="changesLedgerText">{selectedTask.due ?? "-"}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.cycle")}</div>
                  <div className="changesLedgerText">{selectedTask.cycle_id ?? "-"}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.blockedBy")}</div>
                  <div className="changesLedgerText">{selectedTask.blocked_by_task_id ?? "-"}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.nextReview")}</div>
                  <div className="changesLedgerText">{formatTime(selectedTask.next_review_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.updated")}</div>
                  <div className="changesLedgerText">{formatTime(selectedTask.updated_at)}</div>
                </div>
                <div>
                  <div className="changesSummaryKey">{t("tasks.source")}</div>
                  <div className="changesLedgerText">{selectedTask.source}</div>
                </div>
              </div>
              <div className="taskDetailEdit">
                <h3 className="changesGroupTitle">{t("tasks.quickEdit")}</h3>
                <div className="taskDetailEditRow">
                  <input
                    value={detailProject}
                    onChange={(e) => setDetailProject(e.target.value)}
                    placeholder={t("tasks.placeholderProject")}
                    className="taskInput"
                  />
                  <input
                    type="date"
                    value={detailDue}
                    onChange={(e) => setDetailDue(e.target.value)}
                    className="taskInput"
                  />
                  <button className="badge" onClick={onSaveDetail} disabled={loading}>
                    {t("tasks.saveDetail")}
                  </button>
                </div>
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
