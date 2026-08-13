# ADR-005：评测策略

- 状态：Accepted
- 日期：2026-08-13

## Context

“RAG 好不好 / Agent 有没有用”不能靠感觉。需要可重复运行的指标，
且 CI 不能依赖真实 API Key 与费用。

## Decision

建立 `backend/evaluation/`：

- 检索质量：Hit Rate、Precision@K、Context Relevance（真实
  `BudgetRetriever` vs `KeywordRetriever` 对比）；
- Agent 质量：Task Success、Reviewer Detection、质量分（规则/长度/角色一致性）、
  Latency、Tokens、Cost；
- 双模式：`mock`（确定性 LLM，零成本，CI 可跑）/ `real`（DeepSeek API）；
- 报告自动生成到 `evaluation/reports/report.md`，未实测项一律标注
  `Not measured`，禁止编造数字。

## Alternatives

- 只用 LLM-as-judge：成本高、不稳定、难以在 CI 复现；
- 只做单元测试：无法回答“RAG 到底好不好”。

## Trade-offs

规则化质量分与人工/LLM 评分存在偏差，但可复现、可对比、可回归。

## Consequences

- Prompt 修改后必须重跑 benchmark 并更新报告；
- 后续增加向量检索 / 多模型路由时，用同一套数据集对比基线。
