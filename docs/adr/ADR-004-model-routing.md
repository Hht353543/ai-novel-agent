# ADR-004：模型路由与成本

- 状态：Accepted
- 日期：2026-08-13

## Context

不同任务对模型能力要求不同：结构化规划需要强指令跟随，章节正文需要长文本
生成，JSON 解析失败需要修复。全流程用同一模型会造成成本与延迟浪费。

## Decision

默认全流程使用 `deepseek-chat`（单模型，行为可预测）；通过配置支持：

- `DEEPSEEK_MODELS` 逗号分隔降级列表（主模型重试耗尽后按顺序切换）；
- `LLM_MAX_RETRIES` + 指数退避（429/5xx/连接/超时才重试，参数错误不重试）；
- `DEEPSEEK_AUTO_REPAIR_JSON`：JSON 解析失败时用一次额外调用修复；
- Token 预算：`llm/budget.py` 按上下文窗口动态裁剪知识库注入量。

现阶段不引入多模型路由（small/large），因为 DeepSeek 单模型已满足
全部任务；保留接口（`BaseLLM` Protocol），后续可按任务配置不同模型。

## Alternatives

- 立即引入多模型路由：增加配置面与评测面，收益未验证；
- 不设重试：可用性差。

## Consequences

- 成本与 token 记录在日志与评测报告（`evaluation/`）中；
- 模型切换不侵入业务层（Agent 只依赖 `BaseLLM`）。
