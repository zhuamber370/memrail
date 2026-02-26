/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type IdeaStatus = "captured" | "triage" | "discovery" | "ready" | "rejected";
type RouteNodeType = "goal" | "idea";

type Idea = {
  id: string;
  title: string;
  problem: string;
  hypothesis: string;
  status: IdeaStatus;
  source: string;
  updated_at: string;
};

type IdeaListOut = {
  items: Idea[];
  page: number;
  page_size: number;
  total: number;
};

type RouteOption = {
  id: string;
  name: string;
  status: string;
};

type RouteListOut = {
  items: RouteOption[];
  page: number;
  page_size: number;
  total: number;
};

const IDEA_STATUSES: IdeaStatus[] = ["captured", "triage", "discovery", "ready", "rejected"];
const NODE_TYPES: RouteNodeType[] = ["goal", "idea"];

export default function IdeasPage() {
  const { t } = useI18n();
  const [taskId, setTaskId] = useState("");

  const [title, setTitle] = useState("");
  const [problem, setProblem] = useState("");
  const [hypothesis, setHypothesis] = useState("");
  const [source, setSource] = useState("ui://ideas");
  const [createStatus, setCreateStatus] = useState<IdeaStatus>("captured");

  const [filterStatus, setFilterStatus] = useState<IdeaStatus | "all">("all");
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedIdeaId, setSelectedIdeaId] = useState<string | null>(null);

  const [statusDraft, setStatusDraft] = useState<IdeaStatus>("captured");
  const [promoteRouteId, setPromoteRouteId] = useState("");
  const [promoteNodeType, setPromoteNodeType] = useState<RouteNodeType>("goal");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedIdea = useMemo(
    () => ideas.find((item) => item.id === selectedIdeaId) ?? null,
    [ideas, selectedIdeaId]
  );

  useEffect(() => {
    const queryTaskId = new URLSearchParams(window.location.search).get("task_id") ?? "";
    setTaskId(queryTaskId.trim());
  }, []);

  useEffect(() => {
    if (!taskId) {
      setIdeas([]);
      setRoutes([]);
      setSelectedIdeaId(null);
      return;
    }
    void onRefresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, taskId]);

  useEffect(() => {
    if (!selectedIdea) return;
    setStatusDraft(selectedIdea.status);
  }, [selectedIdea]);

  function statusLabel(status: IdeaStatus): string {
    return t(`ideas.status.${status}`);
  }

  async function onRefresh() {
    if (!taskId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const ideaParams = new URLSearchParams({ page: "1", page_size: "100", task_id: taskId });
      if (filterStatus !== "all") ideaParams.set("status", filterStatus);

      const [ideaRes, routeRes] = await Promise.all([
        apiGet<IdeaListOut>(`/api/v1/ideas?${ideaParams.toString()}`),
        apiGet<RouteListOut>(`/api/v1/routes?page=1&page_size=100&task_id=${encodeURIComponent(taskId)}`)
      ]);
      setIdeas(ideaRes.items);
      setRoutes(routeRes.items);
      setSelectedIdeaId((prev) => {
        if (prev && ideaRes.items.some((item) => item.id === prev)) return prev;
        return ideaRes.items[0]?.id ?? null;
      });
      setPromoteRouteId((prev) => {
        if (prev && routeRes.items.some((item) => item.id === prev)) return prev;
        return routeRes.items[0]?.id ?? "";
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onCreateIdea() {
    if (!taskId || !title.trim() || !source.trim()) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPost<Idea>("/api/v1/ideas", {
        task_id: taskId,
        title: title.trim(),
        problem: problem.trim(),
        hypothesis: hypothesis.trim(),
        status: createStatus,
        source: source.trim()
      });
      setTitle("");
      setProblem("");
      setHypothesis("");
      setNotice(t("ideas.noticeCreated"));
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onSaveStatus() {
    if (!selectedIdea) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPatch<Idea>(`/api/v1/ideas/${selectedIdea.id}`, { status: statusDraft });
      setNotice(t("ideas.noticeUpdated"));
      await onRefresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onPromote() {
    if (!selectedIdea) return;
    if (!promoteRouteId) {
      setError(t("ideas.errNeedRoute"));
      return;
    }
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPost(`/api/v1/ideas/${selectedIdea.id}/promote`, {
        route_id: promoteRouteId,
        node_type: promoteNodeType
      });
      setNotice(t("ideas.noticePromoted"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card ideasBoard">
      <h1 className="h1">{t("ideas.title")}</h1>
      <p className="meta">{t("ideas.subtitle")}</p>
      {!taskId ? <p className="meta">{t("ideas.contextRequired")}</p> : null}
      {taskId ? (
        <p className="meta">
          {t("ideas.contextTask")}: {taskId}
        </p>
      ) : null}

      {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      {notice ? <p style={{ color: "var(--success)" }}>{notice}</p> : null}

      {taskId ? (
      <section className="ideasCreate">
        <input
          className="taskInput"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={t("ideas.placeholderTitle")}
        />
        <select
          className="taskInput"
          value={createStatus}
          onChange={(event) => setCreateStatus(event.target.value as IdeaStatus)}
        >
          {IDEA_STATUSES.map((status) => (
            <option key={status} value={status}>
              {statusLabel(status)}
            </option>
          ))}
        </select>
        <input
          className="taskInput"
          value={source}
          onChange={(event) => setSource(event.target.value)}
          placeholder={t("ideas.placeholderSource")}
        />
        <button className="badge" disabled={loading} onClick={onCreateIdea}>
          {t("ideas.create")}
        </button>
        <button className="badge" disabled={loading} onClick={onRefresh}>
          {t("ideas.refresh")}
        </button>
        <textarea
          className="taskInput taskTextArea ideasCreateWide"
          value={problem}
          onChange={(event) => setProblem(event.target.value)}
          placeholder={t("ideas.placeholderProblem")}
        />
        <textarea
          className="taskInput taskTextArea ideasCreateWide"
          value={hypothesis}
          onChange={(event) => setHypothesis(event.target.value)}
          placeholder={t("ideas.placeholderHypothesis")}
        />
      </section>
      ) : null}

      {taskId ? (
      <div className="ideasLayout">
        <section className="ideasListPanel">
          <div className="taskField">
            <span>{t("ideas.filterStatus")}</span>
            <select
              className="taskInput"
              value={filterStatus}
              onChange={(event) => setFilterStatus(event.target.value as IdeaStatus | "all")}
            >
              <option value="all">{t("ideas.filterAll")}</option>
              {IDEA_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {statusLabel(status)}
                </option>
              ))}
            </select>
          </div>

          <div className="ideasList">
            {ideas.length ? (
              ideas.map((idea) => (
                <button
                  key={idea.id}
                  className={`ideasRow ${idea.id === selectedIdeaId ? "ideasRowActive" : ""}`}
                  onClick={() => setSelectedIdeaId(idea.id)}
                >
                  <div className="ideasRowTitle">{idea.title}</div>
                  <div className="taskMetaLine">
                    <span>{statusLabel(idea.status)}</span>
                    <span>{new Date(idea.updated_at).toLocaleString()}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="meta">{t("ideas.emptyList")}</div>
            )}
          </div>
        </section>

        <section className="ideasDetail">
          {selectedIdea ? (
            <>
              <h2 className="ideasDetailTitle">{t("ideas.detail")}</h2>
              <div className="ideasField">
                <span>{t("ideas.status")}</span>
                <select
                  className="taskInput"
                  value={statusDraft}
                  onChange={(event) => setStatusDraft(event.target.value as IdeaStatus)}
                >
                  {IDEA_STATUSES.map((status) => (
                    <option key={status} value={status}>
                      {statusLabel(status)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="ideasField">
                <span>{t("ideas.source")}</span>
                <div className="meta">{selectedIdea.source}</div>
              </div>
              <div className="ideasField">
                <span>{t("ideas.problem")}</span>
                <div className="ideasTextBlock">{selectedIdea.problem || "-"}</div>
              </div>
              <div className="ideasField">
                <span>{t("ideas.hypothesis")}</span>
                <div className="ideasTextBlock">{selectedIdea.hypothesis || "-"}</div>
              </div>
              <div className="taskMetaLine">
                <span>
                  {t("ideas.updated")}: {new Date(selectedIdea.updated_at).toLocaleString()}
                </span>
              </div>

              <div className="ideasActionRow">
                <button className="badge" disabled={loading} onClick={onSaveStatus}>
                  {t("ideas.saveStatus")}
                </button>
              </div>

              <div className="ideasPromote">
                <h3 className="changesSubTitle">{t("ideas.promote")}</h3>
                <div className="ideasPromoteGrid">
                  <div className="ideasField">
                    <span>{t("ideas.promoteRoute")}</span>
                    <select
                      className="taskInput"
                      value={promoteRouteId}
                      onChange={(event) => setPromoteRouteId(event.target.value)}
                    >
                      {routes.map((route) => (
                        <option key={route.id} value={route.id}>
                          {route.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="ideasField">
                    <span>{t("ideas.promoteNodeType")}</span>
                    <select
                      className="taskInput"
                      value={promoteNodeType}
                      onChange={(event) => setPromoteNodeType(event.target.value as RouteNodeType)}
                    >
                      {NODE_TYPES.map((type) => (
                        <option key={type} value={type}>
                          {t(`routes.nodeType.${type}`)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {selectedIdea.status !== "ready" ? (
                  <p className="meta">{t("ideas.promoteNeedReady")}</p>
                ) : null}
                <button
                  className="badge"
                  disabled={loading || selectedIdea.status !== "ready"}
                  onClick={onPromote}
                >
                  {t("ideas.promoteAction")}
                </button>
              </div>
            </>
          ) : (
            <div className="meta">{t("ideas.emptyDetail")}</div>
          )}
        </section>
      </div>
      ) : null}
    </div>
  );
}
