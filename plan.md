# MathModeler-Flow 需求文档（Vibe Coding 可直接执行版）

## 1. 项目目标
构建一个“数学建模全流程 AI 协同系统”，由 1 个 Manager Agent 协调 3 个专业 Agent（Modeling/Coding/Thesis），覆盖从题目分析、模型建立、代码求解到论文输出的完整流程，并支持流式交互、历史项目持续开发、Prompt 可配置化、LaTeX 模版导入、一键 Docker 部署。

## 2. 目标用户与典型场景
- 数学建模竞赛学生：需要快速完成建模-编程-论文联动。
- 研究人员：需要复用项目历史，持续迭代同一课题。
- 教学场景：展示 AI 协同建模过程，追踪 Agent 推理痕迹。

典型流程：
1. 用户创建项目并上传题目描述与数据；
2. Manager 规划任务并分配给 3 个 Agent；
3. 前端实时展示流式思考与输出片段；
4. 用户在任意阶段插入补充消息（例如新增约束）；
5. 系统保存历史并支持下次继续开发；
6. 一键导出论文（LaTeX）和代码结果。

## 3. 技术栈与硬性约束
- 后端：Python 3.10+、FastAPI、LiteLLM、SQLAlchemy、WebSocket。
- 前端：Vue 3（Composition API）、Vite、Pinia、Tailwind CSS。
- 数据：SQLite（MVP），预留 PostgreSQL 兼容层。
- 部署：Docker + Docker Compose 一键启动。
- 能力：流式输出、Prompt 导入与热切换、项目历史持久化、LaTeX 模版管理、Python 执行能力。

## 4. 系统总体架构
### 4.1 逻辑架构
- `UI 层（Vue）`：聊天工作区、代码预览、LaTeX 预览、项目管理。
- `API 层（FastAPI）`：HTTP + WebSocket。
- `Agent Orchestrator`：Manager + 三个专业 Agent。
- `执行与工具层`：LiteLLM 客户端、Python Runner、LaTeX 渲染器、模板仓库。
- `存储层`：SQLite（项目、消息、版本、Prompt、模板绑定）。

### 4.2 Agent 协同机制
- Manager Agent：
  - 解析用户需求，制定任务图（Task Graph）。
  - 决策调用 Modeling/Coding/Thesis 的顺序与轮次。
  - 汇总输出并触发反思（Reflection Loop）。
- Modeling Agent：输出问题抽象、符号定义、假设、模型与公式。
- Coding Agent：输出 Python 求解代码、执行结果、误差分析。
- Thesis Agent：输出论文章节草稿、图表说明、LaTeX 结构化文本。

### 4.3 反思机制（Reflection）
每轮子 Agent 输出后，Manager 执行检查：
1. 完整性检查：是否覆盖“建模+代码+论文”当前阶段目标。
2. 一致性检查：模型变量与代码变量是否一致。
3. 可验证性检查：是否有可运行 Python 或可渲染 LaTeX 片段。
4. 不达标则回退：重发修正指令给对应 Agent，最多 `N=3` 轮。

## 5. 功能需求（对应你的 8 点需求）
### FR-1 多 Agent 编排（LiteLLM + Manager + 3 Agent + 流式）
- 必须支持 LiteLLM 统一接入多家模型 API（OpenAI/Anthropic/Gemini/DeepSeek 等）。
- Manager 主导调度，三个子 Agent 按任务类型执行。
- 所有 Agent 输出通过 WebSocket 流式回推前端。
- 支持“思考过程事件”（计划、反思、修正）与“内容事件”（正文、代码、LaTeX）分离。

### FR-2 Prompt 可调与可导入
- 提供 Prompt 配置页：
  - 系统级 Prompt（全局）
  - Agent 级 Prompt（Modeling/Coding/Thesis/Manager）
  - 项目级 Prompt 覆盖（仅当前项目）
- 支持导入 `.yaml/.json/.md` 模板，自动校验字段。
- 支持版本化与回滚。

### FR-3 完整前端页面
- 页面最少包含：
  - 登录前置页（MVP 可匿名）
  - 项目列表页
  - 项目工作区（核心）
  - Prompt 管理页
  - 模板管理页（LaTeX）
  - 历史记录与回放页
- 工作区分栏：
  - 左侧：项目上下文与文件树
  - 中间：多 Agent 聊天流
  - 右侧：代码执行结果 / LaTeX 预览切换

### FR-4 支持用户插入补充消息与消息列表
- 用户可在任意执行阶段插入“补充消息”（如新增约束、修订目标）。
- 消息必须落库，且记录来源（user/manager/modeling/coding/thesis/system）。
- 支持消息筛选、折叠、跳转到关联版本。

### FR-5 项目历史保留与继续开发
- 每个项目保留：
  - 全量消息历史
  - Agent 产出快照（代码、模型说明、论文草稿）
  - Prompt 版本与模板版本
- 支持“从任意历史节点继续开发（fork 分支）”。

### FR-6 支持 LaTeX、Python，预设 LaTeX 模板导入
- 系统内置竞赛论文模板（国赛/美赛可扩展）。
- 支持上传 `.tex` 模板并绑定项目。
- 支持 LaTeX 片段实时预览。
- 支持 Python 代码执行（沙箱或受限执行环境），返回 stdout/stderr。

### FR-7 Docker 一键部署
- `docker compose up -d` 后可直接访问前后端。
- 包含：
  - backend 容器
  - frontend 容器
  - 持久化 volume（db/data/templates）
- 提供 `.env.example` 与启动检查脚本。

### FR-8 Python + Vue 开发
- 后端必须 Python + FastAPI。
- 前端必须 Vue 3 + Vite + Pinia。
- API 与类型约束明确，前后端并行开发。

## 6. 非功能需求
- 性能：
  - WebSocket 首包延迟 < 2s（不含模型推理耗时）。
  - UI 流式刷新不卡顿（1000 条消息内可用）。
- 可观测性：
  - 每轮 Agent 调用含 trace_id。
  - 后端日志包含 agent_name/model/provider/token_usage。
- 稳定性：
  - API 调用失败可自动重试（指数退避，最多 2 次）。
  - WebSocket 断线重连，支持会话恢复。
- 安全性：
  - API key 仅后端持有，不下发前端。
  - Python 执行环境限制危险系统调用（MVP 先做白名单模块）。

## 7. 项目目录（落地版）
```text
MathModeler-Flow/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── manager.py
│   │   │   ├── modeling.py
│   │   │   ├── coding.py
│   │   │   ├── thesis.py
│   │   │   └── reflection.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── litellm_client.py
│   │   │   └── logger.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   ├── session.py
│   │   │   └── crud.py
│   │   ├── prompts/
│   │   │   ├── default/
│   │   │   └── loader.py
│   │   ├── routers/
│   │   │   ├── projects.py
│   │   │   ├── prompts.py
│   │   │   ├── templates.py
│   │   │   └── websocket.py
│   │   ├── schemas/
│   │   │   ├── project.py
│   │   │   ├── message.py
│   │   │   └── prompt.py
│   │   ├── services/
│   │   │   ├── orchestrator.py
│   │   │   ├── python_runner.py
│   │   │   └── latex_service.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── http.ts
│   │   │   └── ws.ts
│   │   ├── components/
│   │   │   ├── AgentMessageList.vue
│   │   │   ├── PromptEditor.vue
│   │   │   ├── CodePanel.vue
│   │   │   ├── LatexPreview.vue
│   │   │   └── ProjectHistory.vue
│   │   ├── stores/
│   │   │   ├── project.ts
│   │   │   ├── chat.ts
│   │   │   └── prompt.ts
│   │   ├── views/
│   │   │   ├── ProjectListView.vue
│   │   │   ├── WorkspaceView.vue
│   │   │   ├── PromptView.vue
│   │   │   └── TemplateView.vue
│   │   └── router/index.ts
│   ├── package.json
│   └── vite.config.ts
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── templates/
│   ├── mcm_icm_default.tex
│   └── cumbcm_default.tex
└── data/
    ├── app.db
    └── files/
```

## 8. 数据库设计（SQLite MVP）
### 8.1 核心表
- `projects`
  - id, name, description, status, created_at, updated_at
- `messages`
  - id, project_id, role, agent_name, content, message_type, parent_id, created_at
- `runs`
  - id, project_id, run_status, started_at, ended_at, trace_id
- `prompt_versions`
  - id, scope(global/agent/project), target_name, content, version, created_at
- `template_versions`
  - id, name, file_path, version, metadata_json, created_at
- `artifacts`
  - id, project_id, kind(code/latex/report/model), content, run_id, created_at

## 9. API 与 WebSocket 约定
### 9.1 HTTP API（示例）
- `POST /api/projects` 创建项目
- `GET /api/projects` 项目列表
- `GET /api/projects/{id}` 项目详情
- `POST /api/projects/{id}/messages` 插入用户补充消息
- `GET /api/projects/{id}/history` 获取历史与快照
- `POST /api/prompts/import` 导入 Prompt 模板
- `POST /api/templates/import` 导入 LaTeX 模板
- `POST /api/projects/{id}/run` 启动一次协同任务

### 9.2 WebSocket 事件协议
- 连接：`/ws/projects/{project_id}`
- 入站事件：
  - `user.append_message`
  - `run.start`
  - `run.stop`
- 出站事件：
  - `agent.plan`
  - `agent.token`（流式 token）
  - `agent.chunk`（结构化片段：markdown/code/latex）
  - `agent.reflection`
  - `run.status`
  - `run.error`

事件统一字段：
- `event_id`
- `trace_id`
- `project_id`
- `agent`
- `timestamp`
- `payload`

## 10. Prompt 规范
支持 `YAML/JSON`，标准字段：
- `name`
- `scope`
- `agent`
- `system_prompt`
- `developer_prompt`
- `constraints`
- `output_schema`
- `version`

导入校验：
1. 必填字段完整；
2. scope 与 agent 一致；
3. 版本号递增；
4. 不通过则返回结构化错误信息。

## 11. LaTeX 与 Python 能力设计
### 11.1 LaTeX
- 支持模板加载、变量替换、章节拼装。
- 前端实时预览（先 KaTeX/MathJax，后续再加完整编译）。
- 导出 `.tex` 文件，后续可扩展 PDF 编译容器。

### 11.2 Python
- 执行入口：`services/python_runner.py`
- 受限运行：
  - 限时（如 15s）
  - 限内存（容器级）
  - 模块白名单（numpy/pandas/scipy/matplotlib）
- 返回结构：
  - `stdout`
  - `stderr`
  - `exit_code`
  - `artifacts`（图像或结果文件路径）

## 12. 前端页面详细需求
- `ProjectListView`
  - 创建/删除/进入项目，展示最后更新时间。
- `WorkspaceView`
  - 消息流、输入框、补充消息、运行控制按钮、状态栏。
- `PromptView`
  - Prompt 编辑、导入、版本切换、差异对比。
- `TemplateView`
  - LaTeX 模板列表、上传、预览、绑定项目。
- `HistoryView（可合并到 Workspace 侧栏）`
  - 时间线、版本快照、从历史节点继续开发。

## 13. Docker 部署要求
### 13.1 Compose 服务
- `backend`：暴露 `8000`
- `frontend`：暴露 `5173` 或 `80`
- `volumes`：
  - `./data:/app/data`
  - `./templates:/app/templates`
- `env_file`：加载 `.env`

### 13.2 一键命令
- 开发环境：`docker compose up --build`
- 生产环境（MVP）：`docker compose up -d`

## 14. 里程碑计划（建议 4 周）
- M1（第 1 周）：后端骨架 + LiteLLM 流式 + Manager 基础调度 + WS 打通。
- M2（第 2 周）：三 Agent 联动 + 反思机制 + 消息落库 + 项目历史。
- M3（第 3 周）：前端完整页面 + Prompt/模板管理 + LaTeX/Python 面板。
- M4（第 4 周）：Docker 一键部署 + 回归测试 + 文档完善。

## 15. 验收标准（Definition of Done）
- 可以创建项目并发起一次完整建模流程。
- 可以看到 Manager 与 3 Agent 的流式输出与反思日志。
- 可以在执行中插入补充消息并影响后续输出。
- 可以保存历史并从历史节点继续开发。
- 可以导入 Prompt 与 LaTeX 模板并生效。
- 可以执行 Python 代码并查看结果。
- 可以 `docker compose up` 后直接访问完整系统。

## 16. 第一阶段立即开发任务（今天就可开工）
1. 初始化目录与 `backend/requirements.txt`、`frontend/package.json`。
2. 完成 `core/litellm_client.py`（统一 `chat` + `stream_chat`）。
3. 完成 `agents/manager.py`（调度 + 简易反思循环）。
4. 完成 `routers/websocket.py`（连接、事件分发、流式推送）。
5. 建立 SQLite 模型（projects/messages/runs）。
6. 前端搭建 `WorkspaceView + AgentMessageList + ws.ts` 最小可用版。
7. 提供 `docker-compose.yml`，确保后端和前端都能启动。

## 17. 开发规范
- Python 全量类型注解，异步逻辑统一 `async/await`。
- 前端状态统一 Pinia，WebSocket 与 HTTP 分层。
- 所有 Agent 调用写结构化日志（JSON 格式优先）。
- 所有配置可环境变量化（模型名、API Base、超时、重试）。
