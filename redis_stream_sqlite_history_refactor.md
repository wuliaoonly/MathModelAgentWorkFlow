# Redis 流式输出 + SQLite 历史消息持久化重构计划

## 0. 背景与当前问题
- 现有实现已经具备：
  - 后端 FastAPI WebSocket：`/task/{task_id}` 形式（当前实现）
  - Redis Pub/Sub：用于实时推送消息
  - 前端任务页：基于 `task_id` 连接 WebSocket，并在断线时重连（当前实现）
- 本重构计划将 WebSocket/Redis/SQLite 的主键维度从 `task_id` 迁移到 `project_id/run_id`
- 现有实现与计划目标之间的主要矛盾在于：
  - 数据层主要依赖 Redis（断线重连有“文件补偿”逻辑），缺少统一的“历史消息”持久化策略
  - 多 agent 的“反思循环”仍偏流程内局部重试，缺少统一 Manager 层的反思检查与回退策略
  - 事件协议/消息类型虽然有 `msg_type/agent_type/tool_name`，但缺少“事件 envelope + trace_id + 事件语义分层”，难以稳定实现“计划/反思/增量输出”的严格区分

## 1. 本次重构的取舍（以你的要求为准）
1. **流式输出仍使用 Redis**  
   - Redis 负责：实时推送、断线重连后的继续接收新事件
2. **数据库只做历史消息持久化**  
   - SQLite 负责：消息回放、断线/重连后补齐历史、历史检索（例如按 project_id/run_id 获取消息流）
   - 其他元数据（如 prompt 版本、模板绑定、artifacts 等）不强制进入数据库（先保持最小化）
3. **采用 `project_id/run_id` 模式（`task_id` 仅作为兼容字段可选）**  
   - Redis/WS/SQLite 以 `project_id/run_id` 作为主键维度
   - 前端可逐步升级到 `project/run`，同时通过兼容层保持消息渲染尽量不变

## 2. 目标架构（面向流式与反思）
### 2.1 运行时数据流
1. 用户创建一个 `project`，并启动一次 `run`（后端生成 `project_id` 与 `run_id`）
2. 后端 Manager 发起多 agent 协同与“反思循环”
3. 每产生一条“事件”（计划、输出片段、反思、修正、状态变化等）：
   - 立即写入 Redis（用于 WebSocket 流式推送）
   - 同步落库到 SQLite（用于回放/补齐历史）
4. 客户端重连：
   - WS 连接建立后，后端从 SQLite 按 `project_id/run_id` 拉取历史消息，并按顺序推送，并且将历史数据交给agent作为继续任务的抓手。
   - 然后继续订阅 Redis 获取新事件

### 2.2 事件协议（保证可实现多 agent 反思）
建议保留现有 `Message` 的核心字段，但新增“事件 envelope”，用于表达语义与追踪：
- `event_id`: 全局唯一（uuid）
- `trace_id`: 同一次任务/同一轮反思链路的追踪 id
- `project_id`: 项目 id
- `run_id`: 运行 id
- `task_id`: 可选兼容字段（若你希望复用现有前端/日志结构）
- `event_type`: 语义类型（建议）
  - `agent.plan`：Manager 或某 agent 的计划/思路片段
  - `agent.chunk`：正文/代码/LaTeX 增量内容
  - `agent.reflection`：反思检查结论
  - `agent.correction`：给子 agent 的修正指令或重试触发
  - `run.status`：开始/进行中/结束/失败
  - `run.error`：错误
- `agent`: 产生该事件的 agent 名称（Coordinator/Modeler/Coder/Writer）
- `payload`: 事件具体内容（与现有 `content/tool_name/...` 兼容）

说明：  
- 你现有前端主要依赖 `msg_type/agent_type/content` 渲染，因此 envelope 的引入需要“兼容层”：
  - 在 Redis/WS 推送时可以同时保留旧字段，或在前端先不改渲染逻辑，仅把新 envelope 作为附加字段。

## 3. 文件结构调整建议（只调整后端目录，不大动业务入口）
当前结构要兼容现状，建议把后端拆成“模块化领域层”，重点是把消息/存储/事件语义从流程逻辑中抽离：

```text
backend/app/
  main.py
  api/
    routers/
      ws_router.py
      modeling_router.py
  core/
    workflow/
      manager.py            # 新增：Manager orchestration + reflection loop
      coordinator.py        # 可复用现有 CoordinatorAgent
      modeler.py            # 可复用现有 ModelerAgent
      coder.py              # 可复用现有 CoderAgent（反思用于失败重试时仍可保留）
      writer.py             # 可复用现有 WriterAgent
    events/
      envelope.py          # EventEnvelope 定义
      types.py              # event_type 常量/枚举
  infra/
    redis/
      redis_stream.py      # Redis 发布/订阅封装（只管流式）
    storage/
      sqlite_db.py         # engine/session 管理
      repositories/
        message_repository.py  # 仅负责历史消息读写（project_id/run_id -> messages）
      models/
        message.py          # SQLite ORM model（最小表）
  schemas/
    request.py
    response.py            # 兼容前端/旧渲染的 Message schema
  services/
    python_runner.py
    latex_service.py
  tools/
    ...
```

## 4. 数据库（SQLite）最小化设计：只保留历史消息
### 4.1 表设计（最小）
建议至少一张表：
- `messages`
  - `id`: uuid（对应 `event_id` 或内部 id）
  - `project_id`: string
  - `run_id`: string
  - `trace_id`: string nullable
  - `event_type`: string
  - `agent`: string nullable
  - `msg_type`: 兼容旧逻辑（system/agent/user/tool）
  - `agent_type`: 兼容旧逻辑（Coordinator/Modeler/Coder/Writer）
  - `tool_name`: 兼容旧逻辑
  - `content`: text nullable
  - `payload_json`: text（把 payload/扩展字段统一存 json）
  - `created_at`: datetime

### 4.2 写入策略
- 每产生一条事件：
  1) Redis publish（保证实时）
  2) SQLite insert（保证回放）
- 失败容忍策略：
  - Redis 成功后，SQLite 写失败不阻断主流程（只写日志并允许后续补写）

## 5. Redis 与 WS：保持现有流式能力，但把“断线补历史”从文件迁移到 SQLite
现状：
- `backend/app/routers/ws_router.py` 中对重连做了“从 `logs/messages/{task_id}.json` 读取历史”的补偿。

目标：
- 把“文件补偿”替换为：
  - WS 连接建立后，调用 `MessageRepository.list_by_run_id(project_id, run_id)` 拉取历史
  - 按时间顺序推送到前端
- Redis 订阅仍保持（用于接收新事件）。

## 6. 多 agent 反思循环：新增 Manager 层的 Reflection Loop（但仍输出到 Redis）
当前反思更偏 `CoderAgent` 的失败重试。

建议实现一个最小可用的 Reflection Loop：
1. 每个阶段结束后（例如：Coordinator 输出完成 / Modeler 输出完成 / 某章节 coder 输出完成 / writer 输出完成）：
   - Manager 调用 reflection checker（LLM 或规则校验二选一，先从规则开始）
2. checker 产出：
   - `pass/fail`
   - `diagnostics`（问题点）
   - `correction_prompt`（给对应子 agent 的修正指令）
3. 不通过则：
   - 通过 Redis 推送 `agent.reflection` 事件
   - 通过 Redis 推送 `agent.correction` 事件
   - 触发最多 `N=3` 次回退重做
4. checker 通过后进入下一阶段

### 6.1 检查目标（与 plan.md 对齐但最小化）
- 完整性：本阶段是否生成了必须字段（例如模型说明、代码响应、writer 章节内容）
- 一致性：变量/符号/章节 key 是否能对上（先做简单字符串对齐）
- 可验证性：是否包含能运行的代码块或可渲染的 LaTeX/Markdown

## 7. 实施步骤（建议按周/里程碑推进）
### M1（第 1 阶段）：SQLite 历史消息落地
1. 引入 SQLite ORM（SQLAlchemy）并创建 `messages` 最小表
2. 修改后端消息发布路径：
   - 将 `redis_manager.publish_message(...)` 增强为“同时写 SQLite”
3. WS 重连逻辑：
   - 从 `logs/messages/*.json` 切换为从 SQLite 按 `project_id/run_id` 拉取历史并推送
4. 前端保持不变（兼容旧字段即可）

交付验证：
- 启动一次 run，断开后重连，历史消息仍完整呈现

### M2（第 2 阶段）：Manager 统一反思与事件语义
1. 新增 `core/workflow/manager.py`：
   - 负责 orchestrate 四个 agent 的 stage
   - 负责 reflection loop（最小可用）
2. 在 reflection loop 中产出事件 envelope（或至少添加 event_type 字段）
3. 将现有固定流程替换为 Manager 驱动（尽量复用已有 agent 实现）

交付验证：
- 出现 code/写作不满足格式时，能触发反思并重试，且前端能看到 `agent.reflection/agent.correction`

### M3（第 3 阶段）：可观测性与稳定性
1. trace_id/log：为每次 run 与每轮 reflection 生成 trace_id
2. token_usage 与 errors：把关键错误也写入历史消息表（便于回放）
3. 可选：为 event_type 增加前端渲染策略（先不强制）

交付验证：
- 能从 SQLite 回放看到完整链路，包括失败原因与修正建议

## 8. 回滚与兼容策略
- 兼容策略：
  - Redis/WS 仍尽量保持旧的 `Message` 字段，使前端渲染不需要立即大改
- 回滚策略：
  - 在 SQLite 落地后先保留旧文件写入（双写阶段），当确认稳定后再移除文件补偿

## 9. 你需要我继续确认的两个点（避免方向走偏）
1. SQLite “仅保留历史消息”是否允许保留 `run` 的最小元数据（例如 run_status、标题摘要）？  
   - 如果不允许，我会把这些元数据也只存在 Redis/内存/文件，并保证消息表能做回放
2. 对前端是否允许做到“新字段可用但旧字段仍可用”（即消息 envelope 作为附加字段）？  
   - 如果允许，我会以最小改动完成事件语义增强

