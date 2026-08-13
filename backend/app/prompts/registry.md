# Prompt Registry

> Prompt 元数据登记表。修改任何 Prompt 模板或构建逻辑时，必须递增对应
> `version` 并登记变更说明，使 Prompt 可独立评测与追溯。

| name | version | model | purpose | variables |
| --- | --- | --- | --- | --- |
| planner | v1 | deepseek-chat | 生成结构化小说规划 | title, genre, theme, keywords, requirement, extra_requirements, attachment, context |
| character | v1 | deepseek-chat | 建立人物系统（档案+状态+关系） | plan, context |
| writer | v1 | deepseek-chat | 生成章节正文 | plan, arc, chapter_outline, characters, memory, context_text, previous_chapter_text, rag_context, extra_requirements, attachment, target_length, revision_instructions, memory_facts, timeline, previous_draft |
| reviewer | v1 | deepseek-chat | 审校章节质量 | plan, chapter_title, chapter_text, characters, memory, rag_context, memory_facts, timeline |
| memory | v1 | deepseek-chat | 提取状态增量与长期事实 | plan, chapter_title, chapter_index, chapter_text, characters, existing_facts |
| timeline | v1 | deepseek-chat | 维护时间线与一致性 | plan, chapter_title, chapter_index, events, existing_entries, chapter_text |
| knowledge_compress | v1 | deepseek-chat | 长原文摘要压缩 | category, chunk, summary_max |

## 变更记录

- 2026-08-13：初始化 Registry，登记 7 个 Prompt（v1）。
