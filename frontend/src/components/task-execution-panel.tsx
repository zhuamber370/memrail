/* eslint-disable react/jsx-no-bind */
"use client";

import { useEffect, useMemo, useState } from "react";

import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import { useI18n } from "../i18n";

type FlowStatus = "candidate" | "active" | "parked" | "completed" | "cancelled";
type StepType = "start" | "goal" | "idea";
type EditableStepType = Exclude<StepType, "start">;
type StepStatus = "waiting" | "execute" | "done" | "removed" | "todo" | "in_progress" | "cancelled";
type StepEdgeRelation = "refine" | "initiate" | "handoff";
type CreatableEdgeRelation = StepEdgeRelation;
type TaskStatus = "todo" | "in_progress" | "done" | "cancelled";

type Flow = {
  id: string;
  name: string;
  status: FlowStatus;
  updated_at: string;
};

type FlowListOut = {
  items: Flow[];
};

type Step = {
  id: string;
  title: string;
  description: string;
  node_type: StepType;
  status: StepStatus;
  order_hint: number;
};

type StepEdge = {
  id: string;
  from_node_id: string;
  to_node_id: string;
  relation: StepEdgeRelation;
};

type FlowGraphOut = {
  route_id: string;
  nodes: Step[];
  edges: StepEdge[];
};

type DagNodeLayout = {
  node: Step;
  level: number;
  x: number;
  y: number;
};

const DAG_NODE_WIDTH = 210;
const DAG_NODE_HEIGHT = 84;
const DAG_COLUMN_GAP = 86;
const DAG_ROW_GAP = 18;
const DAG_PADDING_X = 20;
const DAG_PADDING_Y = 16;
const EDITABLE_NODE_TYPES: EditableStepType[] = ["goal", "idea"];

function pickPrimaryFlow(flows: Flow[]): Flow | null {
  return flows.find((item) => item.status === "active") ?? flows[0] ?? null;
}

function normalizeStepState(status: StepStatus): StepStatus {
  if (status === "todo") return "waiting";
  if (status === "in_progress") return "execute";
  if (status === "cancelled") return "removed";
  return status;
}

function mapEdgeClass(status: StepStatus): string {
  const normalized = normalizeStepState(status);
  if (normalized === "execute") return "taskDagEdgeExecute";
  if (normalized === "done") return "taskDagEdgeDone";
  if (normalized === "removed") return "taskDagEdgeRemoved";
  return "taskDagEdgeWaiting";
}

function mapNodeClass(step: Step, selected: boolean): string {
  const normalized = normalizeStepState(step.status);
  const classes = ["taskDagNode"];
  if (step.node_type === "start") classes.push("taskDagNodeStart");
  if (normalized === "execute") classes.push("taskDagNodeExecute");
  if (normalized === "done") classes.push("taskDagNodeDone");
  if (normalized === "removed") classes.push("taskDagNodeRemoved");
  if (normalized === "waiting") classes.push("taskDagNodeWaiting");
  if (selected) classes.push("taskDagNodeSelected");
  return classes.join(" ");
}

function statusOptions(step: Step): StepStatus[] {
  if (step.node_type === "start") return ["done"];
  if (step.node_type === "goal") return ["waiting", "execute", "done"];
  return ["todo", "in_progress", "done", "cancelled"];
}

function createStatusOptions(nodeType: EditableStepType): StepStatus[] {
  if (nodeType === "goal") return ["waiting", "execute"];
  return ["todo", "in_progress"];
}

function defaultCreateStatus(nodeType: EditableStepType): StepStatus {
  return nodeType === "goal" ? "waiting" : "todo";
}

function inferEdgeRelation(predecessorType: StepType | null, nextType: EditableStepType): CreatableEdgeRelation | null {
  const normalizedPredecessor = predecessorType === "start" ? "idea" : predecessorType;
  if (!normalizedPredecessor) return null;
  if (normalizedPredecessor === "goal" && nextType === "goal") return null;
  if (normalizedPredecessor === "idea" && nextType === "idea") return "refine";
  if (normalizedPredecessor === "idea" && nextType === "goal") return "initiate";
  return "handoff";
}

function startStepStatus(nodeType: EditableStepType): StepStatus {
  if (nodeType === "goal") return "execute";
  return "in_progress";
}

export function TaskExecutionPanel({ taskId, onTaskStarted }: { taskId: string; onTaskStarted?: (status: TaskStatus) => void }) {
  const { t } = useI18n();

  const [flows, setFlows] = useState<Flow[]>([]);
  const [selectedFlowId, setSelectedFlowId] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [edges, setEdges] = useState<StepEdge[]>([]);
  const [selectedStepId, setSelectedStepId] = useState("");
  const [error, setError] = useState("");

  const [startGoalTitle, setStartGoalTitle] = useState("");
  const [startStepType, setStartStepType] = useState<EditableStepType>("goal");
  const [newStepType, setNewStepType] = useState<EditableStepType>("goal");
  const [newStepTitle, setNewStepTitle] = useState("");
  const [newStepStatus, setNewStepStatus] = useState<StepStatus>("waiting");
  const [newPredecessorNodeId, setNewPredecessorNodeId] = useState("");

  const [loadingFlows, setLoadingFlows] = useState(false);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [startingTask, setStartingTask] = useState(false);
  const [creatingStep, setCreatingStep] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);

  const sortedSteps = useMemo(
    () => [...steps].sort((a, b) => a.order_hint - b.order_hint || a.title.localeCompare(b.title)),
    [steps]
  );

  const stepById = useMemo(() => {
    const map = new Map<string, Step>();
    for (const step of sortedSteps) map.set(step.id, step);
    return map;
  }, [sortedSteps]);

  const dependenciesByStepId = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const edge of edges) {
      map.set(edge.to_node_id, [...(map.get(edge.to_node_id) ?? []), edge.from_node_id]);
    }
    return map;
  }, [edges]);

  const startNode = useMemo(
    () => sortedSteps.find((step) => step.node_type === "start") ?? null,
    [sortedSteps]
  );

  const goalSteps = useMemo(
    () => sortedSteps.filter((step) => step.node_type === "goal"),
    [sortedSteps]
  );

  const activeGoal = goalSteps.find((step) => normalizeStepState(step.status) === "execute") ?? null;
  const lastDoneGoal = [...goalSteps].reverse().find((step) => normalizeStepState(step.status) === "done") ?? null;
  const firstGoal = goalSteps[0] ?? null;
  const currentFocusGoal = activeGoal ?? lastDoneGoal ?? firstGoal ?? null;

  const selectedStep = useMemo(
    () =>
      sortedSteps.find((step) => step.id === selectedStepId) ??
      currentFocusGoal ??
      startNode ??
      null,
    [sortedSteps, selectedStepId, currentFocusGoal?.id, startNode?.id]
  );

  const selectedStepStatuses = useMemo(
    () => (selectedStep ? statusOptions(selectedStep) : []),
    [selectedStep]
  );

  const selectedStepStatusValue = useMemo(() => {
    if (!selectedStep) return "waiting";
    if (selectedStepStatuses.includes(selectedStep.status)) return selectedStep.status;
    return selectedStepStatuses[0] ?? "waiting";
  }, [selectedStep, selectedStepStatuses]);

  const createStepStatuses = useMemo(
    () => createStatusOptions(newStepType),
    [newStepType]
  );

  const predecessorNode = useMemo(
    () => stepById.get(newPredecessorNodeId) ?? null,
    [stepById, newPredecessorNodeId]
  );

  const inferredEdgeType = useMemo(
    () => inferEdgeRelation(predecessorNode?.node_type ?? null, newStepType),
    [predecessorNode?.node_type, newStepType]
  );

  const currentStatusText = useMemo(() => {
    if (activeGoal) {
      return `${activeGoal.title} · ${t("routes.nodeStatus.execute")}`;
    }
    const current = lastDoneGoal ?? firstGoal;
    if (!current) return t("tasks.execution.noCurrentStep");
    return `${current.title} · ${t(`routes.nodeStatus.${normalizeStepState(current.status)}`)}`;
  }, [activeGoal, lastDoneGoal, firstGoal, t]);

  const dagNodes = useMemo(() => {
    const graphNodes = sortedSteps;
    if (!graphNodes.length) {
      return {
        positioned: [] as DagNodeLayout[],
        positionedById: new Map<string, DagNodeLayout>(),
        width: DAG_NODE_WIDTH + DAG_PADDING_X * 2,
        height: DAG_NODE_HEIGHT + DAG_PADDING_Y * 2
      };
    }

    const nodeIdSet = new Set(graphNodes.map((item) => item.id));
    const levelMemo = new Map<string, number>();

    const computeLevel = (nodeId: string, trail = new Set<string>()): number => {
      if (levelMemo.has(nodeId)) return levelMemo.get(nodeId) as number;
      if (trail.has(nodeId)) return 0;
      trail.add(nodeId);
      const node = stepById.get(nodeId);
      if (!node || node.node_type === "start") {
        levelMemo.set(nodeId, 0);
        trail.delete(nodeId);
        return 0;
      }
      const parents = (dependenciesByStepId.get(nodeId) ?? []).filter((candidateId) => nodeIdSet.has(candidateId));
      if (!parents.length) {
        levelMemo.set(nodeId, 0);
        trail.delete(nodeId);
        return 0;
      }
      const level = Math.max(...parents.map((parentId) => computeLevel(parentId, trail))) + 1;
      levelMemo.set(nodeId, level);
      trail.delete(nodeId);
      return level;
    };

    for (const node of graphNodes) {
      computeLevel(node.id);
    }

    const levelMap = new Map<number, Step[]>();
    for (const node of graphNodes) {
      const level = levelMemo.get(node.id) ?? 0;
      levelMap.set(level, [...(levelMap.get(level) ?? []), node]);
    }

    const levels = [...levelMap.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([level, levelNodes]) => {
        const sorted = [...levelNodes].sort(
          (a, b) => a.order_hint - b.order_hint || a.title.localeCompare(b.title)
        );
        return { level, nodes: sorted };
      });

    const positioned: DagNodeLayout[] = [];
    for (const { level, nodes } of levels) {
      nodes.forEach((node, index) => {
        positioned.push({
          node,
          level,
          x: DAG_PADDING_X + level * (DAG_NODE_WIDTH + DAG_COLUMN_GAP),
          y: DAG_PADDING_Y + index * (DAG_NODE_HEIGHT + DAG_ROW_GAP)
        });
      });
    }

    const positionedById = new Map<string, DagNodeLayout>();
    positioned.forEach((item) => positionedById.set(item.node.id, item));

    const maxLevel = Math.max(...positioned.map((item) => item.level), 0);
    const maxRows = Math.max(...levels.map((item) => item.nodes.length), 1);

    return {
      positioned,
      positionedById,
      width: DAG_PADDING_X * 2 + (maxLevel + 1) * DAG_NODE_WIDTH + maxLevel * DAG_COLUMN_GAP,
      height: DAG_PADDING_Y * 2 + maxRows * DAG_NODE_HEIGHT + (maxRows - 1) * DAG_ROW_GAP
    };
  }, [sortedSteps, dependenciesByStepId, stepById]);

  const dagEdges = useMemo(() => {
    const rendered: Array<StepEdge & { toStatus: StepStatus }> = [];
    for (const edge of edges) {
      const from = dagNodes.positionedById.get(edge.from_node_id);
      const to = dagNodes.positionedById.get(edge.to_node_id);
      if (!from || !to) continue;
      rendered.push({
        ...edge,
        toStatus: stepById.get(edge.to_node_id)?.status ?? "waiting"
      });
    }
    return rendered;
  }, [edges, dagNodes.positionedById, stepById]);

  const edgeSummaries = useMemo(() => {
    const labelByRelation: Record<StepEdgeRelation, string> = {
      refine: t("tasks.execution.edgeType.refine"),
      initiate: t("tasks.execution.edgeType.initiate"),
      handoff: t("tasks.execution.edgeType.handoff")
    };

    return edges
      .map((edge) => {
        const fromTitle = stepById.get(edge.from_node_id)?.title;
        const toTitle = stepById.get(edge.to_node_id)?.title;
        if (!fromTitle || !toTitle) return null;
        return `${fromTitle} -> ${toTitle} · ${labelByRelation[edge.relation] ?? edge.relation}`;
      })
      .filter((item): item is string => Boolean(item));
  }, [edges, stepById, t]);

  async function loadFlows() {
    setLoadingFlows(true);
    setError("");
    try {
      const result = await apiGet<FlowListOut>(
        `/api/v1/routes?page=1&page_size=100&task_id=${encodeURIComponent(taskId)}`
      );
      setFlows(result.items);
      const primary = pickPrimaryFlow(result.items);
      setSelectedFlowId(primary?.id ?? "");
    } catch (e) {
      setError((e as Error).message);
      setFlows([]);
      setSelectedFlowId("");
    } finally {
      setLoadingFlows(false);
    }
  }

  async function loadGraph(routeId: string) {
    setLoadingGraph(true);
    setError("");
    try {
      const result = await apiGet<FlowGraphOut>(`/api/v1/routes/${routeId}/graph`);
      setSteps(result.nodes);
      setEdges(result.edges);
    } catch (e) {
      setError((e as Error).message);
      setSteps([]);
      setEdges([]);
    } finally {
      setLoadingGraph(false);
    }
  }

  useEffect(() => {
    void loadFlows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  useEffect(() => {
    if (!selectedFlowId) {
      setSteps([]);
      setEdges([]);
      setSelectedStepId("");
      return;
    }
    void loadGraph(selectedFlowId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFlowId]);

  useEffect(() => {
    if (!sortedSteps.length) {
      setSelectedStepId("");
      return;
    }
    setSelectedStepId((prev) => {
      if (prev && sortedSteps.some((step) => step.id === prev)) return prev;
      return currentFocusGoal?.id ?? startNode?.id ?? sortedSteps[0].id;
    });
  }, [sortedSteps, currentFocusGoal?.id, startNode?.id]);

  useEffect(() => {
    if (!sortedSteps.length) {
      setNewPredecessorNodeId("");
      return;
    }
    setNewPredecessorNodeId((prev) => {
      if (prev && sortedSteps.some((step) => step.id === prev)) return prev;
      return selectedStep?.id ?? startNode?.id ?? sortedSteps[0].id;
    });
  }, [sortedSteps, selectedStep?.id, startNode?.id]);

  useEffect(() => {
    if (!createStepStatuses.includes(newStepStatus)) {
      setNewStepStatus(defaultCreateStatus(newStepType));
    }
  }, [createStepStatuses, newStepStatus, newStepType]);

  async function createNodeWithEdge(payload: {
    routeId: string;
    nodeType: EditableStepType;
    title: string;
    status: StepStatus;
    predecessorNodeId: string;
    relation: CreatableEdgeRelation;
    orderHint?: number;
  }) {
    const created = await apiPost<Step>(`/api/v1/routes/${payload.routeId}/nodes`, {
      node_type: payload.nodeType,
      title: payload.title,
      description: "",
      status: payload.status,
      order_hint: payload.orderHint ?? 0,
      assignee_type: "human"
    });

    await apiPost(`/api/v1/routes/${payload.routeId}/edges`, {
      from_node_id: payload.predecessorNodeId,
      to_node_id: created.id,
      relation: payload.relation
    });
  }

  async function onStartTask() {
    if (!startGoalTitle.trim()) return;
    setStartingTask(true);
    setError("");
    try {
      const createdFlow = await apiPost<Flow>("/api/v1/routes", {
        task_id: taskId,
        name: `${startGoalTitle.trim()} Flow`,
        goal: startGoalTitle.trim(),
        status: "active"
      });

      const createdStart = await apiPost<Step>(`/api/v1/routes/${createdFlow.id}/nodes`, {
        node_type: "start",
        title: t("tasks.execution.startNodeTitle"),
        description: "",
        status: "done",
        order_hint: 1,
        assignee_type: "human"
      });

      const startEdgeRelation = inferEdgeRelation("start", startStepType);
      if (!startEdgeRelation) {
        throw new Error(t("tasks.execution.edgeRuleGoalToGoal"));
      }

      await createNodeWithEdge({
        routeId: createdFlow.id,
        nodeType: startStepType,
        title: startGoalTitle.trim(),
        status: startStepStatus(startStepType),
        predecessorNodeId: createdStart.id,
        relation: startEdgeRelation,
        orderHint: 2
      });

      await apiPatch(`/api/v1/tasks/${taskId}`, { status: "in_progress" });
      setStartGoalTitle("");
      await loadFlows();
      setSelectedFlowId(createdFlow.id);
      onTaskStarted?.("in_progress");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStartingTask(false);
    }
  }

  async function onAddStep() {
    if (!selectedFlowId || !newPredecessorNodeId || !newStepTitle.trim()) return;
    if (!inferredEdgeType) {
      setError(t("tasks.execution.edgeRuleGoalToGoal"));
      return;
    }
    setCreatingStep(true);
    setError("");
    try {
      await createNodeWithEdge({
        routeId: selectedFlowId,
        nodeType: newStepType,
        title: newStepTitle.trim(),
        status: newStepStatus,
        predecessorNodeId: newPredecessorNodeId,
        relation: inferredEdgeType
      });
      setNewStepTitle("");
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreatingStep(false);
    }
  }

  async function onUpdateStepStatus(stepId: string, status: StepStatus) {
    if (!selectedFlowId) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiPatch(`/api/v1/routes/${selectedFlowId}/nodes/${stepId}`, { status });
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  async function onRenameStep() {
    if (!selectedFlowId || !selectedStep) return;
    const nextTitle = window.prompt(t("tasks.execution.renamePrompt"), selectedStep.title)?.trim() ?? "";
    if (!nextTitle || nextTitle === selectedStep.title) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiPatch(`/api/v1/routes/${selectedFlowId}/nodes/${selectedStep.id}`, { title: nextTitle });
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  async function onDeleteStep() {
    if (!selectedFlowId || !selectedStep) return;
    if (selectedStep.node_type === "start") return;
    if (!window.confirm(t("tasks.execution.deleteConfirm"))) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiDelete(`/api/v1/routes/${selectedFlowId}/nodes/${selectedStep.id}`);
      setSelectedStepId("");
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  return (
    <section className="taskExecPanel taskExecPanelV3">
      <div className="taskExecFlowBar">
        <span className="meta">{t("tasks.execution.title")}</span>
      </div>
      {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}

      {!flows.length ? (
        <div className="taskExecStartBox">
          <p className="meta">{t("tasks.execution.startHint")}</p>
          <div className="taskExecStartRow">
            <select
              className="taskInput"
              value={startStepType}
              onChange={(event) => setStartStepType(event.target.value as EditableStepType)}
              aria-label={t("tasks.execution.startType")}
            >
              {EDITABLE_NODE_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`routes.nodeType.${type}`)}
                </option>
              ))}
            </select>
            <input
              className="taskInput"
              value={startGoalTitle}
              onChange={(event) => setStartGoalTitle(event.target.value)}
              placeholder={t("tasks.execution.startGoalPlaceholder")}
            />
            <button className="badge" disabled={startingTask || loadingFlows} onClick={onStartTask}>
              {t("tasks.execution.startAction")}
            </button>
          </div>
        </div>
      ) : null}

      {loadingFlows ? <p className="meta">{t("tasks.execution.loadingFlows")}</p> : null}

      {flows.length ? (
        <>
          <p className="taskExecStatusLine">
            <span className="changesSummaryKey">{t("tasks.execution.currentNode")}:</span> {currentStatusText}
          </p>

          <div className="taskExecDagCard">
            <div className="taskDagLegend">
              <span className="taskDagLegendItem taskDagLegendExecute">{t("routes.nodeStatus.execute")}</span>
              <span className="taskDagLegendItem taskDagLegendWaiting">{t("routes.nodeStatus.waiting")}</span>
              <span className="taskDagLegendItem taskDagLegendDone">{t("routes.nodeStatus.done")}</span>
            </div>

            {dagNodes.positioned.length ? (
              <div className="taskDagViewport">
                <div
                  className="taskDagCanvas"
                  style={{
                    width: `${dagNodes.width}px`,
                    height: `${dagNodes.height}px`
                  }}
                >
                  <svg className="taskDagEdges" viewBox={`0 0 ${dagNodes.width} ${dagNodes.height}`} preserveAspectRatio="none">
                    {dagEdges.map((edge) => {
                      const from = dagNodes.positionedById.get(edge.from_node_id);
                      const to = dagNodes.positionedById.get(edge.to_node_id);
                      if (!from || !to) return null;
                      const x1 = from.x + DAG_NODE_WIDTH;
                      const y1 = from.y + DAG_NODE_HEIGHT / 2;
                      const x2 = to.x;
                      const y2 = to.y + DAG_NODE_HEIGHT / 2;
                      const midX = x1 + (x2 - x1) / 2;
                      const d = `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`;
                      return (
                        <path
                          key={edge.id}
                          d={d}
                          className={`taskDagEdge ${mapEdgeClass(edge.toStatus)}`}
                        />
                      );
                    })}
                  </svg>

                  {dagNodes.positioned.map(({ node, x, y }) => (
                    <button
                      key={node.id}
                      className={mapNodeClass(node, selectedStep?.id === node.id)}
                      style={{ left: `${x}px`, top: `${y}px`, width: `${DAG_NODE_WIDTH}px`, height: `${DAG_NODE_HEIGHT}px` }}
                      onClick={() => setSelectedStepId(node.id)}
                    >
                      <div className="taskDagNodeTitle">{node.title}</div>
                      <div className="taskDagNodeMeta">
                        <span>{t(`routes.nodeType.${node.node_type}`)}</span>
                        <span>{t(`routes.nodeStatus.${node.status}`)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <p className="meta">{loadingGraph ? t("tasks.execution.loadingMap") : t("routes.graphEmpty")}</p>
            )}

            <div className="taskExecLinksBlock">
              <div className="taskSectionTitle">{t("tasks.execution.edgeSummary")}</div>
              <div className="taskExecLinks">
                {edgeSummaries.length ? (
                  edgeSummaries.map((summary) => <span key={summary} className="badge">{summary}</span>)
                ) : (
                  <span className="meta">{t("tasks.execution.edgeEmpty")}</span>
                )}
              </div>
            </div>
          </div>

          {selectedStep ? (
            <div className="taskExecNodeStatusBar">
              <div className="taskExecNodeStatusMain">
                <span className="meta">
                  {t("tasks.execution.stepStatus")}: {selectedStep.title}
                </span>
                <select
                  className="taskInput taskExecNodeStatusSelect"
                  value={selectedStepStatusValue}
                  onChange={(event) => onUpdateStepStatus(selectedStep.id, event.target.value as StepStatus)}
                  disabled={savingStatus}
                >
                  {selectedStepStatuses.map((status) => (
                    <option key={status} value={status}>
                      {t(`routes.nodeStatus.${status}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="taskExecNodeActions">
                <button className="badge" onClick={onRenameStep} disabled={savingStatus}>
                  {t("tasks.execution.renameAction")}
                </button>
                <button
                  className="badge"
                  onClick={onDeleteStep}
                  disabled={savingStatus || selectedStep.node_type === "start"}
                >
                  {t("tasks.delete")}
                </button>
              </div>
            </div>
          ) : null}

          <div className="taskExecCreateStep">
            <h4 className="taskSectionTitle">{t("tasks.execution.addStep")}</h4>
            <div className="taskExecCreateGrid">
              <select
                className="taskInput"
                value={newStepType}
                onChange={(event) => setNewStepType(event.target.value as EditableStepType)}
              >
                {EDITABLE_NODE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`routes.nodeType.${type}`)}
                  </option>
                ))}
              </select>

              <input
                className="taskInput"
                value={newStepTitle}
                onChange={(event) => setNewStepTitle(event.target.value)}
                placeholder={t("tasks.execution.stepTitlePlaceholder")}
              />

              <select
                className="taskInput"
                value={newPredecessorNodeId}
                onChange={(event) => setNewPredecessorNodeId(event.target.value)}
              >
                {sortedSteps.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.title}
                  </option>
                ))}
              </select>

              <select
                className="taskInput"
                value={newStepStatus}
                onChange={(event) => setNewStepStatus(event.target.value as StepStatus)}
              >
                {createStepStatuses.map((status) => (
                  <option key={status} value={status}>
                    {t(`routes.nodeStatus.${status}`)}
                  </option>
                ))}
              </select>

              <button
                className="badge"
                disabled={creatingStep || !newStepTitle.trim() || !newPredecessorNodeId || !inferredEdgeType}
                onClick={onAddStep}
              >
                {t("tasks.execution.addAction")}
              </button>
            </div>

            <p className="meta">
              {t("tasks.execution.edgeSummary")}:{" "}
              {inferredEdgeType ? t(`tasks.execution.edgeType.${inferredEdgeType}`) : t("tasks.execution.edgeRuleGoalToGoal")}
            </p>

            <p className="meta">{t("tasks.execution.predecessorHint")}</p>
          </div>
        </>
      ) : null}
    </section>
  );
}
