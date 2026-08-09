# Agents（第二阶段）

当前版本未实现 Agent，仅保留扩展目录。

计划中的 Agent：

| 文件 | 职责 |
| --- | --- |
| `planner_agent.py` | 基于大纲模板规划全书结构 |
| `character_agent.py` | 设计人物弧光与关系网 |
| `writer_agent.py` | 按章节生成正文 |
| `reviewer_agent.py` | 检查爽点节奏、逻辑一致性并给出修改建议 |

所有 Agent 将复用 `backend/app/rag`、`backend/app/llm` 与 `backend/app/services` 的既有能力。
