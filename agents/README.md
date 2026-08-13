# Agents（第二阶段）

多 Agent 小说创作系统已实现，**实际代码位于 `backend/app/agents/`**（根目录 `agents/` 仅保留占位说明）。

| 模块 | 职责 |
| --- | --- |
| `backend/app/agents/protocol.py` | Agent 协议与数据结构（NovelPlan / CharacterSystem / ReviewResult 等） |
| `backend/app/agents/context.py` | AgentContext 与遥测 |
| `backend/app/agents/base.py` | BaseAgent 基类与 AgentError |
| `backend/app/agents/registry.py` | Agent 注册表与工厂 |
| `backend/app/agents/planner_agent.py` | 大纲规划 Agent |
| `backend/app/agents/character_agent.py` | 人物设计 Agent |
| `backend/app/agents/writer_agent.py` | 章节写作 Agent |
| `backend/app/agents/reviewer_agent.py` | 质量审校 Agent |
| `backend/app/agents/orchestrator.py` | 编排器（含 Writer ↔ Reviewer 修订循环） |
| `backend/app/api/agents.py` | `/api/agents/*` 路由 |

所有 Agent 复用 `backend/app/rag`、`backend/app/llm` 与 `backend/app/services` 的既有能力。
详细说明见 `docs/multi-agent.md`。
