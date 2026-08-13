# ADR-003：Memory 架构

- 状态：Accepted
- 日期：2026-08-13

## Context

长篇连载需要跨章一致性：人物状态变化、已发生事件、伏笔、关系演变。
把全部章节塞进上下文不可行（token 成本与注意力稀释）。

## Decision

区分四类记忆，分别用不同机制承载：

- **工作记忆**：`AgentContext` 字段（当前章节、上一章摘要）；
- **滚动记忆**：`chapter.memory`（LLM 增量摘要，保留事件线+角色状态）；
- **长期事实**：`MemoryFact[]`（分类 + importance + dedup_key，按重要性截断）；
- **时间线**：`TimelineEntry[]`（事件序列 + 一致性检查警告）。

`MemoryAgent` 从章节提取状态增量与事实，`TimelineAgent` 维护时间线；
状态增量由 `state_engine` 规则化应用，非法字段直接校验失败。

## Alternatives

- 全部章节进上下文：token 爆炸且旧信息被稀释；
- 仅滚动摘要：长尾事实（伏笔、关系）丢失。

## Trade-offs

多级记忆增加 Agent 调用次数（成本+延迟），换取跨章一致性可验证。

## Consequences

- 记忆写入集中到 Tool 层（retrieve_memory / save_memory / update_character）；
- 可评测“有记忆 vs 无记忆”对一致性的影响（见 `evaluation/`）。
