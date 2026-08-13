# 记忆与状态层

## Memory 与 RAG 的边界

- **RAG**：负责“根据当前任务从知识库检索相关知识”，检索对象是外部参考小说 txt；
- **Memory**：负责“系统长期保存什么”，保存对象是本书已发生的事实、人物状态、时间线。

两者职责分离：RAG 结果只作为写作参考，Memory 结果作为**必须遵守的事实约束**。

## MemoryAgent

`backend/app/agents/memory_agent.py` 在每章完成后运行，输出 `MemoryUpdate`：

- `state_deltas`：人物状态增量（`CharacterStateDelta`，字段级 old/new/reason）；
- `facts`：长期事实（人物/地点/世界观/事件/关系/伏笔/物品/秘密/身份）；
- `events`：本章关键事件摘要（供 TimelineAgent 使用）。

事实按 `dedup_key`（category + 内容）去重，按 importance 排序后截断到
`AGENT_MEMORY_MAX_FACTS`（默认 30）。

## CharacterState 持续演化

流程：章节生成 → MemoryAgent 提取增量 → `state_engine.apply_character_state_deltas`
规则化应用（标量 set / 列表 set|add|remove）→ 持久化到项目。

第 1 章：境界=后天一重、位置=青云镇；第 10 章：境界=先天、位置=泰岳。
每次变化都记录 `CharacterStateUpdateRecord`（含章节、字段、old/new、原因），
为后续 Diff / 回滚预留数据。

## TimelineAgent

`backend/app/agents/timeline_agent.py` 维护全书时间线：

- 输入：已有时间线、本章事件、正文节选；
- 输出：合并后的完整时间线（按 sequence 排序）+ 一致性警告；
- 规则化合并：模型漏掉旧条目时按 sequence 保留旧条目，防止时间线丢失。

警告会记录日志（如“上一章说昨天，本章说十天前”）。

## 配置

| 环境变量 | 默认 | 说明 |
| --- | --- | --- |
| `AGENT_MEMORY_ENABLED` | true | 是否执行 MemoryAgent |
| `AGENT_TIMELINE_ENABLED` | true | 是否执行 TimelineAgent |
| `AGENT_MEMORY_MAX_FACTS` | 30 | 长期事实上限 |
| `AGENT_TIMELINE_MAX_ENTRIES` | 50 | 时间线上限 |

## 成本控制

- 每章新增 2 次轻量 LLM 调用（Memory + Timeline），可通过上述开关关闭；
- 输入节选有上限（6000 / 4000 字符），事实与时间线只保留高价值子集；
- 旧版滚动摘要（`MEMORY_ENABLED`）在 Pipeline 中仅在 MemoryAgent 关闭时作为回退。
