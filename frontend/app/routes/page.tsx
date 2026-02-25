/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { RouteGraphPreview, type RouteGraphEdge, type RouteGraphNode } from "../../src/components/route-graph-preview";
import { apiGet, apiPatch, apiPost } from "../../src/lib/api";
import { useI18n } from "../../src/i18n";

type RouteStatus = "candidate" | "active" | "parked" | "completed" | "cancelled";
type RouteNodeType = "decision" | "milestone" | "task";
type RouteNodeStatus = "todo" | "in_progress" | "done" | "cancelled";
type RoutePriority = "P0" | "P1" | "P2" | "P3" | "";

type Route = {
  id: string;
  name: string;
  goal: string;
  status: RouteStatus;
  priority: RoutePriority;
  owner: string | null;
  updated_at: string;
};

type RouteListOut = {
  items: Route[];
  page: number;
  page_size: number;
  total: number;
};

type RouteGraphOut = {
  route_id: string;
  nodes: RouteGraphNode[];
  edges: RouteGraphEdge[];
};

const ROUTE_STATUSES: RouteStatus[] = ["candidate", "active", "parked", "completed", "cancelled"];
const NODE_TYPES: RouteNodeType[] = ["decision", "milestone", "task"];
const ROUTE_PRIORITIES: RoutePriority[] = ["", "P0", "P1", "P2", "P3"];

export default function RoutesPage() {
  const { t } = useI18n();
  const [taskId, setTaskId] = useState("");

  const [name, setName] = useState("");
  const [goal, setGoal] = useState("");
  const [status, setStatus] = useState<RouteStatus>("candidate");
  const [priority, setPriority] = useState<RoutePriority>("P2");
  const [owner, setOwner] = useState("");

  const [filterStatus, setFilterStatus] = useState<RouteStatus | "all">("all");
  const [routes, setRoutes] = useState<Route[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null);

  const [statusDraft, setStatusDraft] = useState<RouteStatus>("candidate");
  const [nodeType, setNodeType] = useState<RouteNodeType>("task");
  const [nodeTitle, setNodeTitle] = useState("");
  const [nodeDescription, setNodeDescription] = useState("");

  const [nodes, setNodes] = useState<RouteGraphNode[]>([]);
  const [edges, setEdges] = useState<RouteGraphEdge[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedRoute = useMemo(
    () => routes.find((item) => item.id === selectedRouteId) ?? null,
    [routes, selectedRouteId]
  );

  useEffect(() => {
    const queryTaskId = new URLSearchParams(window.location.search).get("task_id") ?? "";
    setTaskId(queryTaskId.trim());
  }, []);

  useEffect(() => {
    if (!taskId) {
      setRoutes([]);
      setSelectedRouteId(null);
      setNodes([]);
      setEdges([]);
      return;
    }
    void onRefreshRoutes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterStatus, taskId]);

  useEffect(() => {
    if (!selectedRoute) {
      setNodes([]);
      setEdges([]);
      return;
    }
    setStatusDraft(selectedRoute.status);
    void onLoadGraph(selectedRoute.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedRouteId, selectedRoute?.status]);

  function routeStatusLabel(value: RouteStatus): string {
    return t(`routes.status.${value}`);
  }

  async function onRefreshRoutes() {
    if (!taskId) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      const params = new URLSearchParams({ page: "1", page_size: "100", task_id: taskId });
      if (filterStatus !== "all") params.set("status", filterStatus);
      const listed = await apiGet<RouteListOut>(`/api/v1/routes?${params.toString()}`);
      setRoutes(listed.items);
      setSelectedRouteId((prev) => {
        if (prev && listed.items.some((item) => item.id === prev)) return prev;
        return listed.items[0]?.id ?? null;
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onLoadGraph(routeId: string) {
    try {
      const graph = await apiGet<RouteGraphOut>(`/api/v1/routes/${routeId}/graph`);
      setNodes(graph.nodes);
      setEdges(graph.edges);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function onCreateRoute() {
    if (!taskId || !name.trim()) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPost<Route>("/api/v1/routes", {
        task_id: taskId,
        name: name.trim(),
        goal: goal.trim(),
        status,
        priority: priority || null,
        owner: owner.trim() || null
      });
      setName("");
      setGoal("");
      setOwner("");
      setStatus("candidate");
      setPriority("P2");
      setNotice(t("routes.noticeCreated"));
      await onRefreshRoutes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onSaveRouteStatus() {
    if (!selectedRoute) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPatch<Route>(`/api/v1/routes/${selectedRoute.id}`, { status: statusDraft });
      setNotice(t("routes.noticeUpdated"));
      await onRefreshRoutes();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function onCreateNode() {
    if (!selectedRoute || !nodeTitle.trim()) return;
    setLoading(true);
    setError("");
    setNotice("");
    try {
      await apiPost(`/api/v1/routes/${selectedRoute.id}/nodes`, {
        node_type: nodeType,
        title: nodeTitle.trim(),
        description: nodeDescription.trim(),
        status: "todo" as RouteNodeStatus
      });
      setNodeTitle("");
      setNodeDescription("");
      setNotice(t("routes.noticeNodeCreated"));
      await onLoadGraph(selectedRoute.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card routesBoard">
      <h1 className="h1">{t("routes.title")}</h1>
      <p className="meta">{t("routes.subtitle")}</p>
      {!taskId ? <p className="meta">{t("routes.contextRequired")}</p> : null}
      {taskId ? (
        <p className="meta">
          {t("routes.contextTask")}: {taskId}
        </p>
      ) : null}

      {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      {notice ? <p style={{ color: "var(--success)" }}>{notice}</p> : null}

      {taskId ? (
      <section className="routesCreate">
        <input
          className="taskInput"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t("routes.placeholderName")}
        />
        <input
          className="taskInput"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          placeholder={t("routes.placeholderGoal")}
        />
        <select className="taskInput" value={status} onChange={(event) => setStatus(event.target.value as RouteStatus)}>
          {ROUTE_STATUSES.map((item) => (
            <option key={item} value={item}>
              {routeStatusLabel(item)}
            </option>
          ))}
        </select>
        <select
          className="taskInput"
          value={priority}
          onChange={(event) => setPriority(event.target.value as RoutePriority)}
        >
          {ROUTE_PRIORITIES.map((item) => (
            <option key={item || "none"} value={item}>
              {item || "-"}
            </option>
          ))}
        </select>
        <input
          className="taskInput"
          value={owner}
          onChange={(event) => setOwner(event.target.value)}
          placeholder={t("routes.placeholderOwner")}
        />
        <button className="badge" disabled={loading} onClick={onCreateRoute}>
          {t("routes.create")}
        </button>
        <button className="badge" disabled={loading} onClick={onRefreshRoutes}>
          {t("routes.refresh")}
        </button>
      </section>
      ) : null}

      {taskId ? (
      <div className="routesLayout">
        <section className="routesListPanel">
          <div className="taskField">
            <span>{t("routes.filterStatus")}</span>
            <select
              className="taskInput"
              value={filterStatus}
              onChange={(event) => setFilterStatus(event.target.value as RouteStatus | "all")}
            >
              <option value="all">{t("routes.filterAll")}</option>
              {ROUTE_STATUSES.map((item) => (
                <option key={item} value={item}>
                  {routeStatusLabel(item)}
                </option>
              ))}
            </select>
          </div>

          <div className="routesList">
            {routes.length ? (
              routes.map((route) => (
                <button
                  key={route.id}
                  className={`routesRow ${route.id === selectedRouteId ? "routesRowActive" : ""}`}
                  onClick={() => setSelectedRouteId(route.id)}
                >
                  <div className="routesRowTitle">{route.name}</div>
                  <div className="taskMetaLine">
                    <span>{routeStatusLabel(route.status)}</span>
                    <span>{new Date(route.updated_at).toLocaleString()}</span>
                  </div>
                </button>
              ))
            ) : (
              <div className="meta">{t("routes.emptyList")}</div>
            )}
          </div>
        </section>

        <section className="routesDetail">
          {selectedRoute ? (
            <>
              <h2 className="ideasDetailTitle">{t("routes.detail")}</h2>
              <div className="ideasField">
                <span>{t("routes.goal")}</span>
                <div className="ideasTextBlock">{selectedRoute.goal || "-"}</div>
              </div>
              <div className="routesMetaGrid">
                <div className="ideasField">
                  <span>{t("routes.owner")}</span>
                  <div className="meta">{selectedRoute.owner || "-"}</div>
                </div>
                <div className="ideasField">
                  <span>{t("routes.priority")}</span>
                  <div className="meta">{selectedRoute.priority || "-"}</div>
                </div>
              </div>
              <div className="ideasField">
                <span>{t("routes.status")}</span>
                <select
                  className="taskInput"
                  value={statusDraft}
                  onChange={(event) => setStatusDraft(event.target.value as RouteStatus)}
                >
                  {ROUTE_STATUSES.map((item) => (
                    <option key={item} value={item}>
                      {routeStatusLabel(item)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="taskMetaLine">
                <span>
                  {t("routes.updated")}: {new Date(selectedRoute.updated_at).toLocaleString()}
                </span>
              </div>
              <div className="ideasActionRow">
                <button className="badge" disabled={loading} onClick={onSaveRouteStatus}>
                  {t("routes.saveStatus")}
                </button>
              </div>

              <div className="routesNodeCreate">
                <h3 className="changesSubTitle">{t("routes.nodeCreate")}</h3>
                <div className="routesNodeCreateGrid">
                  <select
                    className="taskInput"
                    value={nodeType}
                    onChange={(event) => setNodeType(event.target.value as RouteNodeType)}
                  >
                    {NODE_TYPES.map((item) => (
                      <option key={item} value={item}>
                        {t(`routes.nodeType.${item}`)}
                      </option>
                    ))}
                  </select>
                  <input
                    className="taskInput"
                    value={nodeTitle}
                    onChange={(event) => setNodeTitle(event.target.value)}
                    placeholder={t("routes.nodeTitle")}
                  />
                  <input
                    className="taskInput"
                    value={nodeDescription}
                    onChange={(event) => setNodeDescription(event.target.value)}
                    placeholder={t("routes.nodeDescription")}
                  />
                  <button className="badge" disabled={loading} onClick={onCreateNode}>
                    {t("routes.nodeCreateAction")}
                  </button>
                </div>
              </div>

              <div className="routesGraphBlock">
                <h3 className="changesSubTitle">{t("routes.graphTitle")}</h3>
                <RouteGraphPreview nodes={nodes} edges={edges} t={t} />
              </div>
            </>
          ) : (
            <div className="meta">{t("routes.emptyDetail")}</div>
          )}
        </section>
      </div>
      ) : null}
    </div>
  );
}
