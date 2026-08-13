# ADR-001：Agent 编排架构

- 状态：Accepted
- 日期：2026-08-13

## Context

小说创作需要 规划 → 人物 → 写作 → 审校 → 记忆 → 时间线 多阶段协作，
阶段间有依赖（写作依赖规划与人物），也有反馈循环（审校失败触发修订）。
若用单个 LLM 调用完成全部任务，上下文过长且无法对中间产物做校验。

## Decision

采用自研编排器（`NovelOrchestrator`）+ 显式 `AgentContext` 状态传递：

- 每个 Agent 是独立类，通过 `AgentRegistry` 按名称创建，禁止 if/elif 硬编码；
- 中间状态（规划、人物、记忆、时间线）显式放在 `AgentContext`，禁止全局变量；
- 审校失败走 修订 → 复审 循环，达到上限返回最高分版本并标记
  `revision_exhausted`；
- 异步执行 + `RunStore` 进度追踪，前端可轮询。

## Alternatives

- **LangGraph / LangChain**：引入框架会掩盖状态与编排细节，且本项目需要
  完全掌控 token 预算与上下文结构；框架收益低于学习/调试成本。
- **单 Agent 长 Prompt**：无法并行、无法分步校验、修订成本高。

## Trade-offs

自研编排器初期代码量更大，但换来：状态可见、可单测、可评估、可面试讲清原理。

## Consequences

- 新增 Agent 只需实现 `BaseAgent` 并注册；
- 状态演进受 `AgentContext` 约束，避免隐式全局状态；
- 编排顺序（哪些串行、哪些可并行）成为可讨论的架构决策。
