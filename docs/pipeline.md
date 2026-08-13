# Pipeline 运行与进度

## 启动方式

### 同步（一次性拿到结果）

- `POST /api/agents/pipeline`：单章完整流程；
- `POST /api/agents/sequence`：连续章节（`start_chapter` ~ `end_chapter`）。

### 异步（前端显示进度）

- `POST /api/agents/pipeline/async` → 返回 `run_id`；
- `POST /api/agents/sequence/async` → 返回 `run_id`；
- `GET /api/agents/runs/{run_id}` → 轮询 `PipelineRunState`；
- `GET /api/agents/runs` → 最近运行列表。

## RunState

`PipelineRunState` 包含：

- `status`：CREATED / PLANNING / CHARACTER_DESIGN / WRITING / REVIEWING /
  REVISING / UPDATING_MEMORY / COMPLETED / FAILED；
- `current_agent` / `message` / `revision_attempts`；
- `progress`：逐步记录（step、status、agent、message、timestamp）；
- `result`：完成后包含完整 `PipelineResult` / `SequenceResult`；
- `error`：失败时的结构化错误。

运行状态保存在进程内 `RunStore`（TTL 1 小时、上限 100 条），服务重启后历史丢失。

## 前端一键 Pipeline

大纲生成页新增“一键 Pipeline（多 Agent）”：

1. 选择连续章数（1~3）；
2. 点击后异步启动（单章走 pipeline，多章走 sequence）；
3. 面板实时显示：当前阶段、当前 Agent、修订次数、最终审校评分；
4. 完成后自动保存项目，可一键进入章节写作。

## Reviewer 增量修订

- 修订时把**上一稿全文**（截断到 `AGENT_REVISION_DRAFT_MAX_CHARS`，默认 4000）与修订意见一起交给 Writer；
- 目标是从“整章重写”改为“针对问题局部修改”；
- `RevisionAttempt` 记录 attempt / base_version / instructions / review，
  `ChapterDraft.version` 为章节版本号，为 Diff / 回滚预留空间。

## 连续章节创作

`POST /api/agents/sequence` 一次调用完成：

```text
Planner → Character（只执行一次）
  ├─ 第 1 章：Writer → Reviewer → Memory/Timeline 更新
  ├─ 第 2 章：携带上一章结尾 + 最新人物状态/记忆/时间线
  └─ 第 3 章：同上
```

每章之间自动传递：前一章结尾（2500 字）、人物状态、长期事实、时间线；
`save=true` 时逐章合并进项目（按卷/章索引 upsert，保留已有章节）。
