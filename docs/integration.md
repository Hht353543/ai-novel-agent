# 集成指南

## 多 Agent API

新增路由前缀 `/api/agents`，与原有 `/api/novel/*`、`/api/projects` 完全独立，互不影响。
错误约定与原有接口一致：HTTP 200 + 结构化错误体（`success=false`、`status=error`、`error` 详情、`run_id`）。

### POST /api/agents/plan

根据用户需求生成结构化小说规划。

```json
{
  "title": "",
  "genre": "武侠",
  "theme": "无敌流",
  "keywords": "系统流,极道流",
  "requirement": "100万字",
  "extra_requirements": "风格参考古龙",
  "attachment_name": "",
  "attachment_text": "",
  "project_id": ""
}
```

响应包含 `plan`（title / premise / world_setting / main_plot / arcs / characters）、`run_id` 与 `telemetry`。

### POST /api/agents/characters

根据规划生成人物系统。

```json
{ "project_id": "", "plan": { "title": "测试书", "arcs": [] } }
```

响应包含 `characters`（profiles / states / relationships）。

### POST /api/agents/write

根据上下文生成章节正文（不含审校）。

```json
{
  "project_id": "",
  "plan": {},
  "volume_index": 0,
  "chapter_index": 0,
  "context_text": "上文",
  "previous_chapter_text": "",
  "target_length": 800,
  "extra_requirements": "",
  "memory": "",
  "revision_instructions": ""
}
```

响应包含 `chapter`（attempt / content / full_text / memory）。

### POST /api/agents/review

审校章节正文。

```json
{
  "project_id": "",
  "plan": {},
  "chapter_title": "第一章 觉醒",
  "chapter_text": "正文",
  "memory": ""
}
```

响应包含 `review`（passed / score / issues / summary / revision_required）。

### POST /api/agents/pipeline

完整流程：规划 → 人物 → 写作 → 审校 → 必要时修订循环。

```json
{
  "project_id": "",
  "save": false,
  "title": "",
  "genre": "武侠",
  "theme": "无敌流",
  "keywords": "系统流",
  "requirement": "10万字",
  "extra_requirements": "",
  "volume_index": 0,
  "chapter_index": 0,
  "target_length": 800,
  "with_review": true,
  "max_revisions": null
}
```

响应包含 `result`：

- `status`：`success` / `demo` / `revision_exhausted` / `error`；
- `plan` / `characters` / `chapter` / `latest_review`；
- `revision_history`：每次审校-修订记录；
- `telemetry`：llm_calls / rag_calls / revision_attempts / steps / duration_ms；
- `project_id`：`save=true` 或携带 `project_id` 时返回持久化后的项目 ID。

## 前端接入建议

1. 先调 `plan` 生成规划，展示给用户确认；
2. 再调 `characters` 生成人物系统，允许编辑；
3. 写作页可先调 `write` 快速出稿，或用 `pipeline`（含审校循环）一键产出；
4. 审校结果展示在编辑器下方，用户可手动采纳或忽略。

## 配置

新增环境变量（见 `backend/.env.example`）：

- `AGENT_MAX_REVISIONS=2`：审校失败最大修订次数；
- `REVIEW_PASS_SCORE=80`：审校通过分数阈值（0-100）。

## 兼容性

- 原有 `/api/novel/*` 与 `/api/projects/*` 完全不变；
- 项目存储新增字段全部可选，旧项目数据可正常读取；
- 未配置 API Key 时，所有 Agent 端点返回 `status=demo` 的演示结果。
