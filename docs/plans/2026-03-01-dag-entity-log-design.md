# 2026-03-01 DAG EntityLog 统一日志设计

## 1. 背景与目标
当前任务执行 DAG（节点 `route_nodes`、边 `route_edges`）将说明信息放在 `description` 字段中，语义偏静态，不适合承载执行过程中的阶段性记录。

本设计目标是将“节点/边说明”升级为“多条执行日志”，并统一到单表 `entity_logs`：

1. 支持节点与边都能追加日志。
2. 保存日志时由服务端自动写入时间。
3. 日志支持编辑与删除。
4. DAG 图上对“有日志”状态有明显提示（徽标）。
5. 与现有代码风格保持一致，采用小步可回滚改造。

## 2. 已确认决策（来自本次设计对齐）
1. 历史 `description` 不做迁移，按废弃语义处理。
2. 日志支持编辑与删除（非 append-only）。
3. 日志结构仅包含“内容 + 自动时间”，不引入阶段标签。
4. DAG 图上采用“徽标”提示有日志，不做整体样式强化。
5. 采用方案 2：统一 `EntityLog` 单表（`entity_type + entity_id`），不采用节点/边双表。

## 3. 非目标
1. 本次不引入日志评论/回复、附件、富文本。
2. 本次不实现日志分页与全文检索（先满足当前 DAG 规模）。
3. 本次不清理历史表结构中的 `description` 列（先停止使用，后续再做 schema clean-up）。
4. 本次不扩展到 route/task 级日志实体。

## 4. 数据模型设计

### 4.1 新增表：`entity_logs`
建议字段：

- `id`: `VARCHAR(40)`，主键，格式与现有资源 ID 风格一致（如 `elg_xxx`）。
- `route_id`: `VARCHAR(40)`，非空，指向 `routes.id`。
- `entity_type`: `VARCHAR(20)`，非空，枚举值：`route_node | route_edge`。
- `entity_id`: `VARCHAR(40)`，非空，按 `entity_type` 对应 `route_nodes.id` 或 `route_edges.id`。
- `actor_type`: `VARCHAR(20)`，非空，默认 `human`。
- `actor_id`: `VARCHAR(80)`，非空，默认 `local`。
- `content`: `TEXT`，非空。
- `created_at`: `TIMESTAMPTZ`，非空，默认 `NOW()`。
- `updated_at`: `TIMESTAMPTZ`，非空，默认 `NOW()`。

### 4.2 约束与索引
1. `entity_type` 检查约束：仅允许 `route_node`、`route_edge`。
2. 索引：`(route_id, entity_type, entity_id, created_at DESC)`，优化列表查询。
3. 索引：`(entity_type, entity_id)`，优化单实体日志计数与存在性判断。
4. 应用层校验 `content.strip()` 非空。
5. 应用层强校验：`entity_id` 必须属于 `route_id` 且与 `entity_type` 匹配。

### 4.3 与旧模型关系
1. `route_nodes.description`、`route_edges.description` 字段保留但停止使用。
2. `node_logs` 进入兼容期（只读/迁移来源），新写入统一走 `entity_logs`。

## 5. 迁移与兼容策略

### 5.1 历史数据处理
1. 历史 `description` 不迁移到日志（按已确认决策执行）。
2. 历史 `node_logs` 迁移到 `entity_logs`，避免已有执行日志丢失。

迁移映射：
- `entity_type = 'route_node'`
- `entity_id = node_logs.node_id`
- `route_id` 通过 `node_logs.node_id -> route_nodes.route_id` 回填
- 其余字段同名复制

### 5.2 过渡期策略
1. 后端保留原节点日志 GET 接口可读，内部改查 `entity_logs`。
2. 新增边日志 API 完全基于 `entity_logs`。
3. 前端切换完成后，逐步下线 `description` 编辑入口与 `node_logs` 旧路径实现。

## 6. API 设计
保持现有节点日志路由风格，新增边日志同构接口，并补齐编辑/删除能力。

### 6.1 节点日志
1. `GET /api/v1/routes/{route_id}/nodes/{node_id}/logs`
2. `POST /api/v1/routes/{route_id}/nodes/{node_id}/logs`
3. `PATCH /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`
4. `DELETE /api/v1/routes/{route_id}/nodes/{node_id}/logs/{log_id}`

### 6.2 边日志
1. `GET /api/v1/routes/{route_id}/edges/{edge_id}/logs`
2. `POST /api/v1/routes/{route_id}/edges/{edge_id}/logs`
3. `PATCH /api/v1/routes/{route_id}/edges/{edge_id}/logs/{log_id}`
4. `DELETE /api/v1/routes/{route_id}/edges/{edge_id}/logs/{log_id}`

### 6.3 请求与返回约定
创建日志请求：
- `content`（必填）
- `actor_type`（可选，默认 `human`）
- `actor_id`（可选，默认 `local`）

更新日志请求：
- `content`（必填，更新后内容）

返回字段：
- `id`、`route_id`、`entity_type`、`entity_id`
- `content`
- `actor_type`、`actor_id`
- `created_at`、`updated_at`

### 6.4 Graph 返回增强（徽标驱动）
在 `GET /api/v1/routes/{route_id}/graph` 返回中，节点与边各增加：
- `has_logs: boolean`

可选扩展（本期不强制）：
- `log_count: int`

## 7. 前端交互设计（Task Execution Panel）

### 7.1 Inspector 区域
将“描述编辑器”替换为“日志面板”：
1. 顶部输入框：新增日志。
2. 列表区：展示日志（按 `created_at desc`）。
3. 每条日志提供“编辑”“删除”动作。

节点选中时调用节点日志接口；边选中时调用边日志接口。

### 7.2 DAG 徽标显示
1. 节点：在节点卡片右上角显示 `LOG` 或圆点徽标，当 `has_logs=true`。
2. 边：在线段中点关系标签附近显示小徽标，当 `has_logs=true`。
3. 不更改节点/边主状态样式（执行/等待/完成配色保持不变）。

### 7.3 旧 description 行为
1. 不再展示 description 输入框。
2. 不再触发 `patch node/edge description` 请求。

## 8. 错误处理与校验
1. `404`: route/node/edge/log 不存在。
2. `422`: `content` 为空（trim 后）。
3. `409`: `entity_type + entity_id` 与 `route_id` 不匹配。
4. 编辑/删除日志时必须验证日志归属当前 route + entity，避免跨实体误操作。

## 9. 测试策略

### 9.1 后端
1. `entity_logs` 节点日志 CRUD 测试。
2. `entity_logs` 边日志 CRUD 测试。
3. 日志编辑/删除异常路径测试（404/422/409）。
4. `graph.has_logs` 正确性测试（节点和边）。
5. 兼容回归：现有路由图节点/边创建、关系推断不回归。
6. 若 change service 接入日志动作，补充 dry-run/commit/rollback 行为测试。

### 9.2 前端
1. Inspector 在“节点/边”切换时正确加载对应日志。
2. 新增日志后列表即时刷新，时间显示正确。
3. 编辑/删除日志后 UI 与服务端一致。
4. DAG 徽标显示与 `has_logs` 一致。

## 10. 上线与回滚

### 10.1 分阶段上线
1. Phase A：上线 `entity_logs` + 新 API + graph `has_logs`。
2. Phase B：前端切换到日志面板与徽标显示。
3. Phase C：清理 `description` 编辑路径与旧日志链路。

### 10.2 回滚策略
1. 前端异常：回滚前端到旧 UI，不影响新表存在。
2. 后端异常：临时禁用边日志入口，保留节点读能力。

## 11. 风险与缓解
1. 风险：`entity_logs` 无数据库级多态外键。  
   缓解：服务层统一做 route + entity 强校验，测试覆盖跨路由与跨实体场景。
2. 风险：迁移期间双路径并存导致行为漂移。  
   缓解：明确写路径单一（仅 `entity_logs`），旧路径只读并尽快移除。
3. 风险：graph 查询增加 `has_logs` 可能带来性能波动。  
   缓解：使用聚合查询 + 索引，按 route 维度批量计算。

## 12. 验收标准（DoD）
1. 节点与边都可新增/编辑/删除日志。
2. 日志创建自动带 `created_at`，编辑更新 `updated_at`。
3. DAG 图上节点/边有日志时出现明显徽标。
4. Inspector 不再使用 description 作为执行记录入口。
5. 关键 API 与前端交互测试通过。

