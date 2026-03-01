/* eslint-disable react/jsx-no-bind */
"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { apiDelete, apiGet, apiPatch, apiPost } from "../lib/api";
import { useI18n } from "../i18n";

type FlowStatus = "candidate" | "active" | "parked" | "completed" | "cancelled";
type RawStepType = "start" | "goal" | "idea";
type StepType = "start" | "goal";
type EditableStepType = Exclude<StepType, "start">;
type StepStatus = "waiting" | "execute" | "done";
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

type RawStep = {
  id: string;
  title: string;
  description: string;
  node_type: RawStepType;
  status: StepStatus;
  order_hint: number;
  has_logs: boolean;
};

type Step = Omit<RawStep, "node_type"> & { node_type: StepType };

type StepEdge = {
  id: string;
  from_node_id: string;
  to_node_id: string;
  relation: StepEdgeRelation;
  description: string;
  has_logs: boolean;
};

type FlowGraphOut = {
  route_id: string;
  nodes: RawStep[];
  edges: StepEdge[];
};

type EntityLog = {
  id: string;
  route_id: string;
  entity_type: "route_node" | "route_edge";
  entity_id: string;
  actor_type: "human" | "agent";
  actor_id: string;
  content: string;
  created_at: string;
  updated_at: string;
};

type EntityLogListOut = {
  items: EntityLog[];
};

type DagNodeLayout = {
  node: Step;
  level: number;
  x: number;
  y: number;
};

const DAG_NODE_WIDTH = 172;
const DAG_NODE_HEIGHT = 78;
const DAG_COLUMN_GAP = 58;
const DAG_ROW_GAP = 12;
const DAG_PADDING_X = 16;
const DAG_PADDING_Y = 14;
const EDITABLE_NODE_TYPES: EditableStepType[] = ["goal"];
const DAG_ACTION_PANEL_WIDTH = 304;
const DAG_MIN_ZOOM = 0.48;
const DAG_MAX_ZOOM = 1.8;
const DAG_ZOOM_STEP = 0.14;
const DAG_VIEW_PADDING = 28;

function pickPrimaryFlow(flows: Flow[]): Flow | null {
  return flows.find((item) => item.status === "active") ?? flows[0] ?? null;
}

function normalizeStepState(status: StepStatus): StepStatus {
  return status;
}

function mapEdgeClass(status: StepStatus): string {
  const normalized = normalizeStepState(status);
  if (normalized === "execute") return "taskDagEdgeExecute";
  if (normalized === "done") return "taskDagEdgeDone";
  return "taskDagEdgeWaiting";
}

function mapNodeClass(step: Step, selected: boolean): string {
  const normalized = normalizeStepState(step.status);
  const classes = ["taskDagNode"];
  if (step.node_type === "start") classes.push("taskDagNodeStart");
  if (normalized === "execute") classes.push("taskDagNodeExecute");
  if (normalized === "done") classes.push("taskDagNodeDone");
  if (normalized === "waiting") classes.push("taskDagNodeWaiting");
  if (step.has_logs) classes.push("taskDagNodeHasLogs");
  if (selected) classes.push("taskDagNodeSelected");
  return classes.join(" ");
}

function nodeStatusOptions(nodeType: StepType): StepStatus[] {
  if (nodeType === "start") return ["done"];
  return ["waiting", "execute", "done"];
}

function inferEdgeRelation(predecessorType: StepType | null): CreatableEdgeRelation | null {
  if (!predecessorType) return null;
  if (predecessorType === "start") return "initiate";
  return "handoff";
}

function startStepStatus(_nodeType: EditableStepType): StepStatus {
  return "execute";
}

function normalizeStepForDag(step: RawStep): Step {
  if (step.node_type === "idea") {
    return {
      ...step,
      node_type: "goal",
      status: "waiting"
    };
  }
  return {
    ...step,
    node_type: step.node_type
  };
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
  const [newStepTitle, setNewStepTitle] = useState("");
  const [newStepStatus, setNewStepStatus] = useState<StepStatus>("waiting");
  const [newPredecessorNodeId, setNewPredecessorNodeId] = useState("");
  const [nodeMenuOpenFor, setNodeMenuOpenFor] = useState<string | null>(null);
  const [inlineActionMode, setInlineActionMode] = useState<"add" | null>(null);

  const [loadingFlows, setLoadingFlows] = useState(false);
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [startingTask, setStartingTask] = useState(false);
  const [creatingStep, setCreatingStep] = useState(false);
  const [savingStatus, setSavingStatus] = useState(false);
  const [savingInspector, setSavingInspector] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: DAG_VIEW_PADDING, y: DAG_VIEW_PADDING });
  const [isPanning, setIsPanning] = useState(false);
  const [shouldAutoFitDag, setShouldAutoFitDag] = useState(true);
  const [entityLogs, setEntityLogs] = useState<EntityLog[]>([]);
  const [newLogDraft, setNewLogDraft] = useState("");
  const [editingLogId, setEditingLogId] = useState("");
  const [editingLogDraft, setEditingLogDraft] = useState("");
  const [loadingInspectorLogs, setLoadingInspectorLogs] = useState(false);

  const dagViewportRef = useRef<HTMLDivElement | null>(null);
  const nodeMenuPanelRef = useRef<HTMLDivElement | null>(null);
  const panSessionRef = useRef<{
    pointerId: number;
    startClientX: number;
    startClientY: number;
    originPanX: number;
    originPanY: number;
  } | null>(null);

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

  const inspectorTarget = useMemo(() => {
    if (!selectedStep) return null;
    return { kind: "node", node: selectedStep } as const;
  }, [selectedStep]);

  const inspectorLogsBasePath = useMemo(() => {
    if (!selectedFlowId || !inspectorTarget) return "";
    return `/api/v1/routes/${selectedFlowId}/nodes/${inspectorTarget.node.id}/logs`;
  }, [inspectorTarget, selectedFlowId]);

  const predecessorNode = useMemo(
    () => stepById.get(newPredecessorNodeId) ?? null,
    [stepById, newPredecessorNodeId]
  );

  const inferredEdgeType = useMemo(
    () => inferEdgeRelation(predecessorNode?.node_type ?? null),
    [predecessorNode?.node_type]
  );

  const successorsByStepId = useMemo(() => {
    const map = new Map<string, number>();
    for (const edge of edges) {
      map.set(edge.from_node_id, (map.get(edge.from_node_id) ?? 0) + 1);
    }
    return map;
  }, [edges]);

  const selectedStepHasSuccessor = useMemo(
    () => (selectedStep ? (successorsByStepId.get(selectedStep.id) ?? 0) > 0 : false),
    [selectedStep, successorsByStepId]
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

    const baseOrder = new Map<string, number>();
    let baseOrderCursor = 0;
    levels.forEach(({ nodes }) => {
      nodes.forEach((node) => {
        baseOrder.set(node.id, baseOrderCursor);
        baseOrderCursor += 1;
      });
    });

    const dependentsByStepId = new Map<string, string[]>();
    for (const edge of edges) {
      dependentsByStepId.set(edge.from_node_id, [...(dependentsByStepId.get(edge.from_node_id) ?? []), edge.to_node_id]);
    }

    const sortByAnchors = (
      nodes: Step[],
      anchorRows: Map<string, number>,
      anchorIdsForNode: (nodeId: string) => string[]
    ) => {
      return [...nodes].sort((left, right) => {
        const leftRows = anchorIdsForNode(left.id)
          .map((nodeId) => anchorRows.get(nodeId))
          .filter((value): value is number => value !== undefined);
        const rightRows = anchorIdsForNode(right.id)
          .map((nodeId) => anchorRows.get(nodeId))
          .filter((value): value is number => value !== undefined);

        const leftScore = leftRows.length ? leftRows.reduce((acc, value) => acc + value, 0) / leftRows.length : Number.NaN;
        const rightScore = rightRows.length ? rightRows.reduce((acc, value) => acc + value, 0) / rightRows.length : Number.NaN;

        const leftHasScore = Number.isFinite(leftScore);
        const rightHasScore = Number.isFinite(rightScore);
        if (leftHasScore && rightHasScore && leftScore !== rightScore) return leftScore - rightScore;
        if (leftHasScore && !rightHasScore) return -1;
        if (!leftHasScore && rightHasScore) return 1;

        return (baseOrder.get(left.id) ?? 0) - (baseOrder.get(right.id) ?? 0);
      });
    };

    for (let sweep = 0; sweep < 2; sweep += 1) {
      for (let levelIndex = 1; levelIndex < levels.length; levelIndex += 1) {
        const parentRows = new Map<string, number>();
        for (let parentLevelIndex = 0; parentLevelIndex < levelIndex; parentLevelIndex += 1) {
          levels[parentLevelIndex].nodes.forEach((node, rowIndex) => {
            parentRows.set(node.id, rowIndex);
          });
        }
        levels[levelIndex].nodes = sortByAnchors(
          levels[levelIndex].nodes,
          parentRows,
          (nodeId) => dependenciesByStepId.get(nodeId) ?? []
        );
      }

      for (let levelIndex = levels.length - 2; levelIndex >= 0; levelIndex -= 1) {
        const childRows = new Map<string, number>();
        for (let childLevelIndex = levelIndex + 1; childLevelIndex < levels.length; childLevelIndex += 1) {
          levels[childLevelIndex].nodes.forEach((node, rowIndex) => {
            childRows.set(node.id, rowIndex);
          });
        }
        levels[levelIndex].nodes = sortByAnchors(
          levels[levelIndex].nodes,
          childRows,
          (nodeId) => dependentsByStepId.get(nodeId) ?? []
        );
      }
    }

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
  }, [sortedSteps, dependenciesByStepId, stepById, edges]);

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

  const selectedDagNode = useMemo(
    () => (selectedStep ? dagNodes.positionedById.get(selectedStep.id) ?? null : null),
    [selectedStep, dagNodes.positionedById]
  );

  const inlinePanelPosition = useMemo(() => {
    if (!selectedDagNode) return null;
    const desiredX = selectedDagNode.x + DAG_NODE_WIDTH + 12;
    const fallbackX = selectedDagNode.x - DAG_ACTION_PANEL_WIDTH - 12;
    const maxX = Math.max(dagNodes.width - DAG_ACTION_PANEL_WIDTH - 8, 8);
    const x = desiredX + DAG_ACTION_PANEL_WIDTH <= dagNodes.width ? desiredX : Math.max(fallbackX, 8);
    return { x: Math.min(Math.max(x, 8), maxX), y: selectedDagNode.y };
  }, [selectedDagNode, dagNodes.width]);

  const inspectorTargetKey = useMemo(() => {
    if (!inspectorTarget) return "";
    return `node:${inspectorTarget.node.id}`;
  }, [inspectorTarget]);

  const clampZoom = useCallback((value: number) => {
    return Math.min(DAG_MAX_ZOOM, Math.max(DAG_MIN_ZOOM, value));
  }, []);

  const fitDagViewport = useCallback(() => {
    const viewport = dagViewportRef.current;
    if (!viewport || !dagNodes.positioned.length) return;
    const availableWidth = Math.max(viewport.clientWidth - DAG_VIEW_PADDING * 2, 120);
    const availableHeight = Math.max(viewport.clientHeight - DAG_VIEW_PADDING * 2, 120);
    const fitZoom = clampZoom(Math.min(availableWidth / dagNodes.width, availableHeight / dagNodes.height));
    const nextPanX = (viewport.clientWidth - dagNodes.width * fitZoom) / 2;
    const nextPanY = (viewport.clientHeight - dagNodes.height * fitZoom) / 2;
    setZoom(fitZoom);
    setPan({ x: nextPanX, y: nextPanY });
  }, [clampZoom, dagNodes.height, dagNodes.positioned.length, dagNodes.width]);

  const changeZoom = useCallback((delta: number) => {
    const viewport = dagViewportRef.current;
    if (!viewport) return;
    const centerX = viewport.clientWidth / 2;
    const centerY = viewport.clientHeight / 2;
    setZoom((currentZoom) => {
      const nextZoom = clampZoom(currentZoom + delta);
      if (nextZoom === currentZoom) return currentZoom;
      setPan((currentPan) => {
        const worldX = (centerX - currentPan.x) / currentZoom;
        const worldY = (centerY - currentPan.y) / currentZoom;
        return {
          x: centerX - worldX * nextZoom,
          y: centerY - worldY * nextZoom
        };
      });
      return nextZoom;
    });
  }, [clampZoom]);

  const resetDagViewport = useCallback(() => {
    setZoom(1);
    setPan({ x: DAG_VIEW_PADDING, y: DAG_VIEW_PADDING });
  }, []);

  const onDagPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const target = event.target as HTMLElement;
      if (
        target.closest(".taskDagNode") ||
        target.closest(".taskDagInlinePanel") ||
        target.closest(".taskDagToolbar") ||
        target.closest(".taskDagInspector")
      ) {
        return;
      }
      panSessionRef.current = {
        pointerId: event.pointerId,
        startClientX: event.clientX,
        startClientY: event.clientY,
        originPanX: pan.x,
        originPanY: pan.y
      };
      event.currentTarget.setPointerCapture(event.pointerId);
      setIsPanning(true);
    },
    [pan.x, pan.y]
  );

  const onDagPointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const session = panSessionRef.current;
    if (!session || session.pointerId !== event.pointerId) return;
    const deltaX = event.clientX - session.startClientX;
    const deltaY = event.clientY - session.startClientY;
    setPan({
      x: session.originPanX + deltaX,
      y: session.originPanY + deltaY
    });
  }, []);

  const endDagPanSession = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const session = panSessionRef.current;
    if (!session || session.pointerId !== event.pointerId) return;
    panSessionRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setIsPanning(false);
  }, []);

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
      setSteps(result.nodes.map(normalizeStepForDag));
      setEdges(result.edges);
    } catch (e) {
      setError((e as Error).message);
      setSteps([]);
      setEdges([]);
    } finally {
      setLoadingGraph(false);
    }
  }

  async function loadInspectorLogs(logBasePath: string) {
    if (!logBasePath) {
      setEntityLogs([]);
      return;
    }
    setLoadingInspectorLogs(true);
    setError("");
    try {
      const result = await apiGet<EntityLogListOut>(logBasePath);
      setEntityLogs(result.items);
    } catch (e) {
      setError((e as Error).message);
      setEntityLogs([]);
    } finally {
      setLoadingInspectorLogs(false);
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
      setShouldAutoFitDag(true);
      resetDagViewport();
      return;
    }
    setShouldAutoFitDag(true);
    void loadGraph(selectedFlowId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFlowId, resetDagViewport]);

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
    if (!selectedStep) {
      setNodeMenuOpenFor(null);
      setInlineActionMode(null);
      return;
    }
    setNodeMenuOpenFor(null);
    setInlineActionMode(null);
  }, [selectedStep?.id]);

  useEffect(() => {
    if (!inspectorTarget || !inspectorLogsBasePath) {
      setEntityLogs([]);
      setNewLogDraft("");
      setEditingLogId("");
      setEditingLogDraft("");
      return;
    }
    setNewLogDraft("");
    setEditingLogId("");
    setEditingLogDraft("");
    void loadInspectorLogs(inspectorLogsBasePath);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inspectorLogsBasePath, inspectorTargetKey]);

  useEffect(() => {
    if (!shouldAutoFitDag || !dagNodes.positioned.length) return;
    fitDagViewport();
    setShouldAutoFitDag(false);
  }, [dagNodes.positioned.length, fitDagViewport, shouldAutoFitDag]);

  useEffect(() => {
    const isNodeMenuOpen = Boolean(nodeMenuOpenFor) || inlineActionMode !== null;
    if (!isNodeMenuOpen) return;

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;
      if (nodeMenuPanelRef.current?.contains(target)) return;
      if (target.closest(".taskDagNodeMenuTrigger")) return;
      setNodeMenuOpenFor(null);
      setInlineActionMode(null);
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setNodeMenuOpenFor(null);
      setInlineActionMode(null);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [inlineActionMode, nodeMenuOpenFor]);

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
      relation: payload.relation,
      description: ""
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

      const startEdgeRelation = inferEdgeRelation("start") ?? "initiate";

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

  function onSelectNode(nodeId: string) {
    setSelectedStepId(nodeId);
    setNewPredecessorNodeId(nodeId);
    setInlineActionMode(null);
    setNodeMenuOpenFor(null);
  }

  function onOpenNodeMenu(nodeId: string) {
    setSelectedStepId(nodeId);
    setInlineActionMode(null);
    setNodeMenuOpenFor((prev) => (prev === nodeId ? null : nodeId));
  }

  function onOpenAddStepPanel(nodeId: string) {
    setSelectedStepId(nodeId);
    setNewPredecessorNodeId(nodeId);
    setNewStepTitle("");
    setNodeMenuOpenFor(null);
    setInlineActionMode("add");
  }

  async function onAddStep() {
    if (!selectedFlowId || !newPredecessorNodeId || !newStepTitle.trim()) return;
    if (!inferredEdgeType) {
      setError(t("tasks.execution.predecessorHint"));
      return;
    }
    setCreatingStep(true);
    setError("");
    try {
      await createNodeWithEdge({
        routeId: selectedFlowId,
        nodeType: "goal",
        title: newStepTitle.trim(),
        status: newStepStatus,
        predecessorNodeId: newPredecessorNodeId,
        relation: inferredEdgeType
      });
      setNewStepTitle("");
      setInlineActionMode(null);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setCreatingStep(false);
    }
  }

  async function onSetStepStatus(stepId: string, nextStatus: StepStatus) {
    if (!selectedFlowId) return;
    const step = stepById.get(stepId);
    if (!step || step.status === nextStatus) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiPatch(`/api/v1/routes/${selectedFlowId}/nodes/${step.id}`, { status: nextStatus });
      setNodeMenuOpenFor(null);
      setInlineActionMode(null);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  async function onRenameStep(stepId: string) {
    if (!selectedFlowId) return;
    const step = stepById.get(stepId);
    if (!step) return;
    const nextTitle = window.prompt(t("tasks.execution.renamePrompt"), step.title)?.trim() ?? "";
    if (!nextTitle || nextTitle === step.title) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiPatch(`/api/v1/routes/${selectedFlowId}/nodes/${step.id}`, { title: nextTitle });
      setInlineActionMode(null);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  async function onDeleteStep(stepId: string) {
    if (!selectedFlowId) return;
    const step = stepById.get(stepId);
    if (!step) return;
    if (step.node_type === "start") return;
    const hasSuccessor = (successorsByStepId.get(step.id) ?? 0) > 0;
    if (hasSuccessor) {
      setError(t("tasks.execution.deleteLeafOnly"));
      return;
    }
    if (!window.confirm(t("tasks.execution.deleteConfirm"))) return;
    setSavingStatus(true);
    setError("");
    try {
      await apiDelete(`/api/v1/routes/${selectedFlowId}/nodes/${step.id}`);
      setNodeMenuOpenFor(null);
      setInlineActionMode(null);
      setSelectedStepId("");
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingStatus(false);
    }
  }

  async function onAppendInspectorLog() {
    if (!selectedFlowId || !inspectorLogsBasePath || !newLogDraft.trim()) return;
    setSavingInspector(true);
    setError("");
    try {
      await apiPost(inspectorLogsBasePath, {
        content: newLogDraft.trim(),
        actor_type: "human",
        actor_id: "local"
      });
      setNewLogDraft("");
      await loadInspectorLogs(inspectorLogsBasePath);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingInspector(false);
    }
  }

  function onStartEditInspectorLog(log: EntityLog) {
    setEditingLogId(log.id);
    setEditingLogDraft(log.content);
  }

  async function onSaveInspectorLog(logId: string) {
    if (!selectedFlowId || !inspectorLogsBasePath || !editingLogDraft.trim()) return;
    setSavingInspector(true);
    setError("");
    try {
      await apiPatch(`${inspectorLogsBasePath}/${logId}`, { content: editingLogDraft.trim() });
      setEditingLogId("");
      setEditingLogDraft("");
      await loadInspectorLogs(inspectorLogsBasePath);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingInspector(false);
    }
  }

  async function onDeleteInspectorLog(logId: string) {
    if (!selectedFlowId || !inspectorLogsBasePath) return;
    setSavingInspector(true);
    setError("");
    try {
      await apiDelete(`${inspectorLogsBasePath}/${logId}`);
      if (editingLogId === logId) {
        setEditingLogId("");
        setEditingLogDraft("");
      }
      await loadInspectorLogs(inspectorLogsBasePath);
      await loadGraph(selectedFlowId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSavingInspector(false);
    }
  }

  const isExecutionSparse = !flows.length || !dagNodes.positioned.length;

  return (
    <section className={`taskExecPanel taskExecPanelV3${isExecutionSparse ? " taskExecPanelSparse" : ""}`}>
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

            <p className="meta taskDagComposerHint">{t("tasks.execution.selectNodeHint")}</p>
            <p className="meta taskDagComposerHint">{t("tasks.execution.panHint")}</p>

            {dagNodes.positioned.length ? (
              <div className="taskDagWorkspace">
                <div className="taskDagSurface">
                  <div className="taskDagToolbar">
                    <div className="taskDagToolset">
                      <button
                        className="badge"
                        type="button"
                        onClick={() => changeZoom(-DAG_ZOOM_STEP)}
                        aria-label={t("tasks.execution.zoomOut")}
                      >
                        -
                      </button>
                      <button
                        className="badge"
                        type="button"
                        onClick={resetDagViewport}
                        aria-label={t("tasks.execution.resetView")}
                      >
                        100%
                      </button>
                      <button className="badge" type="button" onClick={fitDagViewport}>
                        {t("tasks.execution.fitView")}
                      </button>
                      <button
                        className="badge"
                        type="button"
                        onClick={() => changeZoom(DAG_ZOOM_STEP)}
                        aria-label={t("tasks.execution.zoomIn")}
                      >
                        +
                      </button>
                    </div>
                    <span className="meta taskDagZoomReadout">{Math.round(zoom * 100)}%</span>
                  </div>

                  <div
                    ref={dagViewportRef}
                    className={`taskDagViewport ${isPanning ? "taskDagViewportPanning" : ""}`}
                    onPointerDown={onDagPointerDown}
                    onPointerMove={onDagPointerMove}
                    onPointerUp={endDagPanSession}
                    onPointerCancel={endDagPanSession}
                    role="presentation"
                  >
                    <div
                      className="taskDagStage"
                      style={{
                        width: `${dagNodes.width}px`,
                        height: `${dagNodes.height}px`,
                        transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`
                      }}
                    >
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
                              <g key={edge.id}>
                                <path
                                  d={d}
                                  className={`taskDagEdge ${mapEdgeClass(edge.toStatus)}`}
                                />
                              </g>
                            );
                          })}
                        </svg>

                        {dagNodes.positioned.map(({ node, x, y }) => {
                          const isSelected = selectedStep?.id === node.id;
                          return (
                            <div
                              key={node.id}
                              className={mapNodeClass(node, isSelected)}
                              style={{ left: `${x}px`, top: `${y}px`, width: `${DAG_NODE_WIDTH}px`, height: `${DAG_NODE_HEIGHT}px` }}
                              role="button"
                              tabIndex={0}
                              onClick={() => onSelectNode(node.id)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                  event.preventDefault();
                                  onSelectNode(node.id);
                                }
                              }}
                            >
                              {isSelected ? (
                                <button
                                  className="taskDagNodeMenuTrigger"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    onOpenNodeMenu(node.id);
                                  }}
                                  aria-label={t("tasks.execution.nodeMenuAria")}
                                  disabled={savingStatus || savingInspector}
                                >
                                  ...
                                </button>
                              ) : null}
                              {node.has_logs ? (
                                <span className="taskDagLogBadge" aria-label={t("tasks.execution.logBadge")}>
                                  {t("tasks.execution.logBadge")}
                                </span>
                              ) : null}
                              <div className="taskDagNodeTitle">{node.title}</div>
                              <div className="taskDagNodeMeta">
                                <span>{t(`routes.nodeType.${node.node_type}`)}</span>
                                <span>{t(`routes.nodeStatus.${node.status}`)}</span>
                              </div>
                            </div>
                          );
                        })}

                        {selectedStep &&
                        selectedDagNode &&
                        inlinePanelPosition &&
                        (nodeMenuOpenFor === selectedStep.id || inlineActionMode !== null) ? (
                          <div
                            ref={nodeMenuPanelRef}
                            className="taskDagInlinePanel"
                            style={{ left: `${inlinePanelPosition.x}px`, top: `${inlinePanelPosition.y}px` }}
                          >
                            {nodeMenuOpenFor === selectedStep.id && inlineActionMode === null ? (
                              <div className="taskDagInlineMenu">
                                <button
                                  className="taskDagInlineMenuBtn"
                                  onClick={() => onOpenAddStepPanel(selectedStep.id)}
                                  disabled={savingStatus || creatingStep}
                                >
                                  + {t("tasks.execution.addStep")}
                                </button>
                                <div className="taskDagInlineMenuSection">
                                  <span className="taskDagInlineMenuLabel">{t("tasks.execution.setStatusAction")}</span>
                                  <div className="taskDagInlineStatusGrid">
                                    {nodeStatusOptions(selectedStep.node_type).map((status) => (
                                      <button
                                        key={status}
                                        className={`taskDagInlineStatusBtn${
                                          selectedStep.status === status ? " taskDagInlineStatusBtnActive" : ""
                                        }`}
                                        onClick={() => {
                                          void onSetStepStatus(selectedStep.id, status);
                                        }}
                                        disabled={savingStatus || selectedStep.status === status}
                                      >
                                        {t(`routes.nodeStatus.${status}`)}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                                <button
                                  className="taskDagInlineMenuBtn"
                                  onClick={() => {
                                    setNodeMenuOpenFor(null);
                                    void onRenameStep(selectedStep.id);
                                  }}
                                  disabled={savingStatus}
                                >
                                  {t("tasks.execution.renameAction")}
                                </button>
                                <button
                                  className="taskDagInlineMenuBtn"
                                  onClick={() => {
                                    setNodeMenuOpenFor(null);
                                    void onDeleteStep(selectedStep.id);
                                  }}
                                  disabled={savingStatus || selectedStep.node_type === "start" || selectedStepHasSuccessor}
                                  title={selectedStepHasSuccessor ? t("tasks.execution.deleteLeafOnly") : undefined}
                                >
                                  {t("tasks.delete")}
                                </button>
                              </div>
                            ) : null}

                            {inlineActionMode === "add" ? (
                              <div className="taskDagInlineEditor">
                                <h4 className="taskSectionTitle">{t("tasks.execution.addStep")}</h4>
                                <div className="taskDagInlineForm">
                                  <input
                                    className="taskInput"
                                    value={newStepTitle}
                                    onChange={(event) => setNewStepTitle(event.target.value)}
                                    placeholder={t("tasks.execution.stepTitlePlaceholder")}
                                  />
                                  <select
                                    className="taskInput"
                                    value={newStepStatus}
                                    onChange={(event) => setNewStepStatus(event.target.value as StepStatus)}
                                  >
                                    {nodeStatusOptions("goal").map((status) => (
                                      <option key={status} value={status}>
                                        {t(`routes.nodeStatus.${status}`)}
                                      </option>
                                    ))}
                                  </select>
                                </div>
                                <div className="taskDagInlineActions">
                                  <button
                                    className="badge"
                                    disabled={creatingStep || !newStepTitle.trim() || !newPredecessorNodeId}
                                    onClick={onAddStep}
                                  >
                                    {t("tasks.execution.addAction")}
                                  </button>
                                  <button
                                    className="badge"
                                    onClick={() => setInlineActionMode(null)}
                                    disabled={creatingStep}
                                  >
                                    {t("tasks.cancel")}
                                  </button>
                                </div>
                              </div>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </div>

                <aside className="taskDagInspector">
                  <h4 className="taskSectionTitle">{t("tasks.execution.inspectorTitle")}</h4>
                  {inspectorTarget ? (
                    <>
                      <div className="taskDagInspectorMeta">
                        <p className="taskDagInspectorLine">
                          <span className="changesSummaryKey">{t("tasks.execution.inspectorNode")}:</span> {inspectorTarget.node.title}
                        </p>
                        <p className="taskDagInspectorLine">
                          <span className="changesSummaryKey">{t("routes.nodeType")}:</span>{" "}
                          {t(`routes.nodeType.${inspectorTarget.node.node_type}`)}
                        </p>
                        <p className="taskDagInspectorLine">
                          <span className="changesSummaryKey">{t("tasks.execution.stepStatus")}:</span>{" "}
                          {t(`routes.nodeStatus.${inspectorTarget.node.status}`)}
                        </p>
                      </div>
                      <div className="taskDagLogComposer">
                        <label className="taskField">
                          <span>{t("tasks.execution.logs")}</span>
                          <textarea
                            className="taskInput taskTextArea"
                            value={newLogDraft}
                            onChange={(event) => setNewLogDraft(event.target.value)}
                            placeholder={t("tasks.execution.logPlaceholderNode")}
                          />
                        </label>
                        <div className="taskDagInspectorActions">
                          <button
                            className="badge"
                            onClick={onAppendInspectorLog}
                            disabled={savingInspector || !newLogDraft.trim()}
                          >
                            {t("tasks.execution.addLog")}
                          </button>
                        </div>
                      </div>
                      {loadingInspectorLogs ? (
                        <p className="meta">{t("tasks.execution.loadingLogs")}</p>
                      ) : entityLogs.length ? (
                        <div className="taskDagLogList">
                          {entityLogs.map((log) => {
                            const isEditing = editingLogId === log.id;
                            return (
                              <article key={log.id} className="taskDagLogItem">
                                <div className="taskDagLogHeader">
                                  <span className="taskDagLogActor">{log.actor_id}</span>
                                  <time className="taskDagLogTime">
                                    {new Date(log.updated_at || log.created_at).toLocaleString()}
                                  </time>
                                </div>
                                {isEditing ? (
                                  <textarea
                                    className="taskInput taskTextArea taskDagLogEditInput"
                                    value={editingLogDraft}
                                    onChange={(event) => setEditingLogDraft(event.target.value)}
                                  />
                                ) : (
                                  <p className="taskDagLogContent">{log.content}</p>
                                )}
                                <div className="taskDagLogActions">
                                  {isEditing ? (
                                    <>
                                      <button
                                        className="badge"
                                        onClick={() => {
                                          void onSaveInspectorLog(log.id);
                                        }}
                                        disabled={savingInspector || !editingLogDraft.trim()}
                                      >
                                        {t("tasks.execution.saveLog")}
                                      </button>
                                      <button
                                        className="badge"
                                        onClick={() => {
                                          setEditingLogId("");
                                          setEditingLogDraft("");
                                        }}
                                        disabled={savingInspector}
                                      >
                                        {t("tasks.cancel")}
                                      </button>
                                    </>
                                  ) : (
                                    <>
                                      <button
                                        className="badge"
                                        onClick={() => onStartEditInspectorLog(log)}
                                        disabled={savingInspector}
                                      >
                                        {t("tasks.execution.editLog")}
                                      </button>
                                      <button
                                        className="badge"
                                        onClick={() => {
                                          void onDeleteInspectorLog(log.id);
                                        }}
                                        disabled={savingInspector}
                                      >
                                        {t("tasks.delete")}
                                      </button>
                                    </>
                                  )}
                                </div>
                              </article>
                            );
                          })}
                        </div>
                      ) : (
                        <p className="meta">{t("tasks.execution.noLogs")}</p>
                      )}
                    </>
                  ) : (
                    <p className="meta">{t("tasks.execution.inspectorEmpty")}</p>
                  )}
                </aside>
              </div>
            ) : (
              <p className="meta">{loadingGraph ? t("tasks.execution.loadingMap") : t("routes.graphEmpty")}</p>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}
