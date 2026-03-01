# DAG EntityLog Unified Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将任务执行 DAG 的节点/边 `description` 入口替换为统一的多条执行日志能力（`entity_logs`），并在图上通过徽标清晰显示“有日志”。

**Architecture:** 后端引入统一 `entity_logs` 表（`entity_type + entity_id`），节点与边日志共用一套服务逻辑；路由层提供节点/边对称的日志 CRUD API；`/graph` 返回增加 `has_logs` 供前端渲染徽标。前端 Inspector 从 description 编辑器改为日志面板，按选中目标（节点/边）加载并维护日志列表。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js 14, React 18, TypeScript.

---

## Task 1: 后端 Schema 与模型落地（EntityLog）

**Files:**
- Modify: `backend/src/models.py`
- Modify: `backend/src/db.py`
- Optional (docs if needed): `backend/db/schema.sql`
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

在 `backend/tests/test_routes_api.py` 新增最小失败用例（可先占位），目标是调用边日志接口前返回非 200（接口尚未实现）：

```python
def test_route_edge_logs_crud_placeholder_fails_initially():
    client = make_client()
    # setup route + nodes + edge
    # call GET /api/v1/routes/{route_id}/edges/{edge_id}/logs
    # assert status_code in {404, 405}
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py::test_route_edge_logs_crud_placeholder_fails_initially -v`
Expected: FAIL（接口/能力未就绪）

**Step 3: Write minimal implementation**

1. 在 `backend/src/models.py` 新增 `EntityLog` 模型：

```python
class EntityLog(Base):
    __tablename__ = "entity_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    route_id: Mapped[str] = mapped_column(String(40), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="human")
    actor_id: Mapped[str] = mapped_column(String(80), nullable=False, default="local")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
```

2. 在 `backend/src/db.py` 的 schema ensure 流程中添加 `entity_logs` 建表与索引语句。
3. 添加 `entity_type` 检查约束（Postgres）与 SQLite 兼容校验（应用层兜底）。
4. 保留 `node_logs` 与 `description` 字段（兼容期）。

**Step 4: Run test to verify schema is healthy**

Run: `cd backend && pytest tests/test_routes_api.py::test_route_nodes_edges_and_logs -v`
Expected: PASS（旧能力不回归）

**Step 5: Commit**

```bash
git add backend/src/models.py backend/src/db.py backend/tests/test_routes_api.py
git commit -m "feat(routes): add entity_logs schema and base model"
```

## Task 2: Pydantic Schema 与统一日志 DTO

**Files:**
- Modify: `backend/src/schemas.py`
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

新增用例，断言新日志返回包含 `entity_type/entity_id/updated_at`。

```python
def test_entity_log_response_shape():
    # create node log via API
    # assert keys include entity_type/entity_id/updated_at
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py::test_entity_log_response_shape -v`
Expected: FAIL（当前 NodeLogOut 不含统一字段）

**Step 3: Write minimal implementation**

在 `backend/src/schemas.py` 新增统一日志 schema：

```python
EntityType = Literal["route_node", "route_edge"]

class EntityLogCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)
    actor_type: RouteAssigneeType = "human"
    actor_id: str = Field(default="local", min_length=1)

class EntityLogPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str = Field(min_length=1)

class EntityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    route_id: str
    entity_type: EntityType
    entity_id: str
    actor_type: RouteAssigneeType
    actor_id: str
    content: str
    created_at: datetime
    updated_at: datetime

class EntityLogListOut(BaseModel):
    items: list[EntityLogOut]
```

同时保留现有 `NodeLog*` 以便平滑过渡（后续 task 里逐步替换）。

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_routes_api.py::test_entity_log_response_shape -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/schemas.py backend/tests/test_routes_api.py
git commit -m "feat(routes): add unified entity log schemas"
```

## Task 3: RouteGraphService 统一日志服务实现

**Files:**
- Modify: `backend/src/services/route_service.py`
- Modify: `backend/src/models.py` (imports only if required)
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

新增节点与边日志 CRUD 全流程测试（create/list/patch/delete + 404/422/409 路径）。

```python
def test_entity_logs_crud_for_node_and_edge():
    # setup route graph
    # append node log -> list -> patch -> delete
    # append edge log -> list -> patch -> delete
    # assert status codes and payload
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py::test_entity_logs_crud_for_node_and_edge -v`
Expected: FAIL

**Step 3: Write minimal implementation**

在 `RouteGraphService` 中新增统一方法：

```python
def append_entity_log(self, route_id: str, entity_type: str, entity_id: str, payload: EntityLogCreate) -> EntityLog: ...
def list_entity_logs(self, route_id: str, entity_type: str, entity_id: str) -> list[EntityLog]: ...
def patch_entity_log(self, route_id: str, entity_type: str, entity_id: str, log_id: str, payload: EntityLogPatch) -> Optional[EntityLog]: ...
def delete_entity_log(self, route_id: str, entity_type: str, entity_id: str, log_id: str) -> bool: ...
```

关键校验：
1. `entity_type` 非法 -> `ValueError("ROUTE_ENTITY_TYPE_UNSUPPORTED")`
2. `entity_id` 与 `route_id` 不匹配 -> `ValueError("ROUTE_ENTITY_CROSS_ROUTE")`
3. `content.strip()` 为空 -> `ValueError("ROUTE_LOG_CONTENT_EMPTY")`
4. `log_id` 归属不匹配 -> `ROUTE_ENTITY_LOG_NOT_FOUND`

兼容方法：
- 现有 `append_node_log` / `list_node_logs` 可内部调用统一方法并映射 `entity_type='route_node'`。

**Step 4: Run tests to verify it passes**

Run: `cd backend && pytest tests/test_routes_api.py -k "entity_logs_crud_for_node_and_edge or append_typed_node_log" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/services/route_service.py backend/tests/test_routes_api.py
git commit -m "feat(routes): implement unified entity log service"
```

## Task 4: Routes API 增加边日志与日志编辑删除接口

**Files:**
- Modify: `backend/src/routes/routes.py`
- Modify: `backend/src/schemas.py` (imports / response models)
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

新增用例断言以下路由可用：
- `PATCH /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`
- `DELETE /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`
- `GET/POST/PATCH/DELETE /api/v1/routes/{route_id}/edges/{edge_id}/logs...`

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py::test_entity_log_routes_exposed -v`
Expected: FAIL

**Step 3: Write minimal implementation**

在 `backend/src/routes/routes.py`：
1. 节点日志：补齐 patch/delete。
2. 边日志：新增 get/post/patch/delete。
3. 错误码映射新增：
   - `ROUTE_ENTITY_TYPE_UNSUPPORTED` -> 422
   - `ROUTE_ENTITY_CROSS_ROUTE` -> 409
   - `ROUTE_LOG_CONTENT_EMPTY` -> 422
   - `ROUTE_ENTITY_LOG_NOT_FOUND` -> 404

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_routes_api.py::test_entity_log_routes_exposed -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/routes/routes.py backend/src/schemas.py backend/tests/test_routes_api.py
git commit -m "feat(routes): expose node/edge entity log CRUD endpoints"
```

## Task 5: Graph 输出 `has_logs` 字段

**Files:**
- Modify: `backend/src/schemas.py`
- Modify: `backend/src/services/route_service.py`
- Modify: `backend/src/routes/routes.py` (if response mapping needed)
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

新增测试：无日志时 `has_logs=false`，新增日志后对应 node/edge 变为 `true`。

```python
def test_route_graph_marks_has_logs_for_node_and_edge():
    # create graph
    # assert has_logs false
    # append node + edge logs
    # assert has_logs true
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py::test_route_graph_marks_has_logs_for_node_and_edge -v`
Expected: FAIL

**Step 3: Write minimal implementation**

1. `RouteNodeOut` / `RouteEdgeOut` 增加 `has_logs: bool = False`。
2. `get_graph` 中按 route 批量查询 `entity_logs`，生成：
   - node `has_logs` map（`entity_type='route_node'`）
   - edge `has_logs` map（`entity_type='route_edge'`）
3. 返回 graph 时把布尔值注入 node/edge。

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_routes_api.py::test_route_graph_marks_has_logs_for_node_and_edge -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/schemas.py backend/src/services/route_service.py backend/src/routes/routes.py backend/tests/test_routes_api.py
git commit -m "feat(routes): add has_logs marker to graph nodes and edges"
```

## Task 6: 前端 Inspector 从 description 改为日志面板

**Files:**
- Modify: `frontend/src/components/task-execution-panel.tsx`
- Modify: `frontend/src/i18n.tsx`
- Modify: `frontend/app/globals.css`

**Step 1: Write the failing check (UI expectation)**

由于当前前端无自动化测试，先定义手工验收脚本（记录在 PR 描述或计划执行记录）：
1. 选中节点可新增日志并看到时间。
2. 选中边可新增日志并看到时间。
3. 每条日志可编辑、可删除。
4. 不再出现 “Save Description” 按钮。

**Step 2: Run baseline build to capture current state**

Run: `cd frontend && npm run build`
Expected: PASS（基线可编译）

**Step 3: Write minimal implementation**

1. 删除 `inspectorDescriptionDraft` 相关状态和保存逻辑。
2. 新增 `entityLogs`、`newLogDraft`、`editingLogId` 等状态。
3. 按 `inspectorTarget.kind` 分流调用节点/边日志 API。
4. Inspector 渲染“新增日志 + 日志列表 + 编辑/删除”。
5. 文案替换（`description` -> `logs`）。

关键接口调用：
- Node: `/api/v1/routes/${selectedFlowId}/nodes/${nodeId}/logs`
- Edge: `/api/v1/routes/${selectedFlowId}/edges/${edgeId}/logs`

**Step 4: Run build to verify it passes**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/components/task-execution-panel.tsx frontend/src/i18n.tsx frontend/app/globals.css
git commit -m "feat(frontend): replace DAG description editor with entity log panel"
```

## Task 7: DAG 徽标渲染（节点与边）

**Files:**
- Modify: `frontend/src/components/task-execution-panel.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/src/i18n.tsx` (optional labels)

**Step 1: Write the failing check (manual)**

手工验收脚本：
1. 无日志节点/边不显示徽标。
2. 新增日志后目标节点/边出现徽标。
3. 删除最后一条日志后徽标消失。

**Step 2: Run baseline build**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 3: Write minimal implementation**

1. 在节点卡片右上角渲染 `taskDagLogBadge`（条件：`node.has_logs`）。
2. 在边关系标签附近渲染 `taskDagEdgeLogBadge`（条件：`edge.has_logs`）。
3. 样式保持醒目但不覆盖状态色体系。

**Step 4: Run build and manual verification**

Run: `cd frontend && npm run build`
Expected: PASS

Manual check:
1. 启动：`cd frontend && npm run dev`
2. 进入任务 DAG 页面执行上述 3 条验收脚本。

**Step 5: Commit**

```bash
git add frontend/src/components/task-execution-panel.tsx frontend/app/globals.css frontend/src/i18n.tsx
git commit -m "feat(frontend): show DAG log badges for nodes and edges"
```

## Task 8: 兼容层与文档更新

**Files:**
- Modify: `backend/src/services/route_service.py`
- Modify: `backend/src/routes/routes.py`
- Modify: `backend/README.md`
- Modify: `skill/openclaw_skill.py`
- Test: `backend/tests/test_routes_api.py`

**Step 1: Write the failing test**

新增兼容测试：
- 旧节点日志 GET 仍可读。
- skill snapshot `include_logs` 不报错。

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_routes_api.py -k "node_log and compatibility" -v`
Expected: FAIL

**Step 3: Write minimal implementation**

1. 旧节点日志接口保持可用（内部走统一服务）。
2. `skill/openclaw_skill.py` 的 `get_node_logs` 可继续调用原 URL，返回结构不变。
3. `backend/README.md` 更新日志接口说明（标注 node/edge 与统一存储）。

**Step 4: Run tests to verify it passes**

Run:
- `cd backend && pytest tests/test_routes_api.py -v`
- `cd backend && pytest -q`

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/services/route_service.py backend/src/routes/routes.py backend/README.md skill/openclaw_skill.py backend/tests/test_routes_api.py
git commit -m "chore(routes): keep node log compatibility over entity log backend"
```

## Task 9: 端到端验证与收尾

**Files:**
- Modify (if needed): `docs/reports/` 下新增验收记录

**Step 1: Run backend verification**

Run: `cd backend && pytest tests/test_routes_api.py -v`
Expected: PASS（新增/旧有路由图测试均通过）

**Step 2: Run frontend verification**

Run: `cd frontend && npm run build`
Expected: PASS

**Step 3: Manual acceptance checklist**

1. 节点日志：增删改查可用。
2. 边日志：增删改查可用。
3. 创建日志自动写入 `created_at`。
4. 编辑日志后 `updated_at` 变化。
5. DAG 徽标显示与日志存在性一致。
6. Inspector 不再暴露 description 保存入口。

**Step 4: Final commit (if verification docs changed)**

```bash
git add docs/reports
# only if new/updated verification notes exist
git commit -m "docs: add DAG entity log verification notes"
```

**Step 5: Prepare merge handoff**

输出变更摘要（API 变更点、兼容行为、已执行验证命令）。

## Plan Constraints & Guidance

1. DRY: 节点和边日志逻辑必须复用统一服务函数，不允许复制粘贴两份实现。
2. YAGNI: 本期不加标签、分页、附件、搜索。
3. TDD: 每个后端能力先写失败测试，再实现最小代码。
4. Frequent commits: 每个 Task 至少一个独立 commit。
5. Skills 建议：`@test-driven-development`、`@verification-before-completion`、`@requesting-code-review`。

