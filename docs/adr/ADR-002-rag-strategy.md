# ADR-002：RAG 策略

- 状态：Accepted
- 日期：2026-08-13

## Context

知识库是本地 txt 小说原文（世界观 / 剧情大纲 / 人物角色卡 / other）。
此前按板块把原文直接截断注入 Prompt，查询相关性未被利用。

## Decision

保留“按板块预算注入”为默认（`BudgetRetriever`，行为稳定、零额外依赖），
同时提供轻量关键字检索（`KeywordRetriever`：文件名/正文命中打分 + Top-K），
由 `RAG_RETRIEVER` 配置切换；上下文总预算由 `llm/budget.py` 统一控制。
不引入向量数据库（本地小知识库收益低，且违背“轻量可运行”定位）。

## Alternatives

- **Embedding + 向量库**：需要下载模型/运行服务，冷启动成本高；当知识库
  增长到数十万字符后再评估。
- **全文 LLM 压缩**：保留为可选（`KNOWLEDGE_COMPRESS`），首次开销大。

## Trade-offs

关键字检索召回率低于向量检索，但零依赖、可解释、评测成本低。

## Consequences

- 检索质量用 `evaluation/` 的 Hit Rate / Precision@K / Context Relevance 度量；
- 后续引入向量检索时，只需实现 `RetrievalProvider` 协议并接入 Benchmark 对比。
