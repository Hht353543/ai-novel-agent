# 系统架构

AI 网文作者 Agent：基于 DeepSeek API + 本地知识库的网络小说创作系统。

## 总体架构

```text
前端 Vue3 + Vite + TypeScript
        │  HTTP / JSON / SSE
        ▼
FastAPI 后端
  ├─ api/novel.py        原有单 Agent 快速路径（大纲 / 章节 / 标题 / 角色卡 / 检索）
  ├─ api/projects.py     项目保存 / 列表 / 读取 / 删除
  ├─ api/agents.py       多 Agent 入口（plan / characters / write / review / pipeline）
  ├─ agents/             多 Agent 层（协议 / Context / Agent / 编排器）
  ├─ services/           业务编排（大纲、章节、标题、角色卡、项目、知识库压缩）
  ├─ prompts/            DeepSeek Prompt 模板
  ├─ rag/                RAG 检索（loader / retriever / cache / chunker）
  ├─ llm/                LLM Provider（BaseLLM / DeepSeek / Mock）+ 容错 JSON 解析
  └─ schemas/            Pydantic 数据模型
```

## 多 Agent 层

```mermaid
flowchart TD
    User[用户请求] --> API[/api/agents/*]
    API --> Orch[NovelOrchestrator]
    Orch --> Ctx[AgentContext<br/>LLM / RAG / 状态 / 遥测]
    Orch --> P[PlannerAgent]
    P -->|NovelPlan| C
    Orch --> Ch[CharacterAgent]
    Ch -->|CharacterSystem| C
    Orch --> W[WriterAgent]
    W -->|ChapterResult| R[ReviewerAgent]
    R -->|ReviewResult| Decide{通过?}
    Decide -->|否 且 未达上限| W
    Decide -->|是| Out[最终章节]
    Out --> M[MemoryAgent]
    M -->|状态增量 / 事实| S[State/Memory 层]
    M -->|事件| T[TimelineAgent]
    T -->|时间线| S
    S --> Out2[最终章节 + 状态/记忆/时间线]
    Out2 --> Persist[(NovelProject 扩展字段)]
```

## 分层职责

- `NovelService / ChapterService`：原有单 Agent 快速路径，保持行为不变。
- `NovelOrchestrator`：多 Agent 编排入口，负责创建 Context、按序调用 Agent、驱动修订循环、持久化。
- `BaseAgent`：统一执行模板（输入校验 → 运行 → 输出校验），统一错误与遥测。
- Agent：只通过构造注入的 `BaseLLM` / `RetrievalProvider` 访问基础设施，不直接操作数据库。
- `AgentContext`：所有状态显式传递，禁止隐式全局变量。
- `RunStore`：Pipeline/Sequence 运行状态（进度、当前 Agent、修订次数），供前端轮询。

## 数据流

1. API 收到请求 → `NovelOrchestrator.new_context()` 生成 run_id 与 Context。
2. PlannerAgent 检索知识库并生成 `NovelPlan`。
3. CharacterAgent 根据规划生成 `CharacterSystem`（档案 + 状态 + 关系）。
4. WriterAgent 从 Context 取规划、章节大纲、人物状态、记忆、前文与 RAG 结果生成正文。
5. ReviewerAgent 审校并输出 `ReviewResult`；未通过且未达 `AGENT_MAX_REVISIONS` 时带修订意见重写。
6. MemoryAgent 提取状态增量与长期事实并应用，TimelineAgent 更新时间线。
7. 通过或达到上限后，`save=true` 时把结果合并进项目存储（保留已有章节与角色卡）。

连续章节场景：`POST /api/agents/sequence` 每章重复 4~7 步，自动继承上一章结尾、
人物状态、长期事实与时间线。

详细说明见 [multi-agent.md](multi-agent.md)。
