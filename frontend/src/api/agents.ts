/**
 * 多 Agent Pipeline API 封装（异步启动 + 轮询进度）。
 */
import type { NovelOutline } from "./novel";
import { request } from "./client";

export interface PipelinePayload {
  project_id?: string;
  save?: boolean;
  title: string;
  genre: string;
  theme: string;
  keywords: string;
  requirement: string;
  extra_requirements: string;
  attachment_name: string;
  attachment_text: string;
  volume_index?: number;
  chapter_index?: number;
  target_length?: number;
  with_review?: boolean;
}

export interface SequencePayload extends PipelinePayload {
  start_chapter?: number;
  end_chapter?: number;
}

export interface RunProgressStep {
  step: string;
  status: "running" | "done" | "error";
  agent: string;
  message: string;
  timestamp: string;
}

export interface ReviewResultPayload {
  passed: boolean;
  score: number;
  issues: Array<{
    type: string;
    severity: string;
    description: string;
    suggestion: string;
  }>;
  summary: string;
  revision_required: boolean;
}

export interface PipelineChapterPayload {
  attempt: number;
  content: string;
  full_text: string;
  memory: string;
}

export interface PipelineResultPayload {
  run_id: string;
  project_id: string;
  status: string;
  message: string;
  plan: Record<string, unknown> | null;
  outline: NovelOutline | null;
  chapter: PipelineChapterPayload | null;
  latest_review: ReviewResultPayload | null;
  revision_history: unknown[];
  timeline: unknown[];
  memory_facts: unknown[];
  telemetry: Record<string, unknown>;
}

export interface SequenceChapterPayload {
  chapter_index: number;
  chapter_title: string;
  status: string;
  message: string;
  chapter: PipelineChapterPayload | null;
  latest_review: ReviewResultPayload | null;
}

export interface SequenceResultPayload {
  run_id: string;
  project_id: string;
  status: string;
  message: string;
  plan: Record<string, unknown> | null;
  outline: NovelOutline | null;
  chapters: SequenceChapterPayload[];
  timeline: unknown[];
  memory_facts: unknown[];
  telemetry: Record<string, unknown>;
}

export interface PipelineRunState {
  run_id: string;
  kind: "pipeline" | "sequence";
  status: string;
  current_agent: string;
  message: string;
  revision_attempts: number;
  progress: RunProgressStep[];
  start_time: string;
  end_time: string;
  error: {
    agent: string;
    operation: string;
    error_type: string;
    message: string;
    run_id: string;
  } | null;
  result: PipelineResultPayload | SequenceResultPayload | null;
}

export interface RunStartResponse {
  run_id: string;
  status: string;
}

/** 异步启动单章 Pipeline */
export async function startPipelineAsync(
  payload: PipelinePayload,
): Promise<RunStartResponse> {
  return request<RunStartResponse>("/agents/pipeline/async", {
    method: "POST",
    body: payload,
    errorLabel: "启动 Pipeline 失败",
  });
}

/** 异步启动连续章节 Sequence */
export async function startSequenceAsync(
  payload: SequencePayload,
): Promise<RunStartResponse> {
  return request<RunStartResponse>("/agents/sequence/async", {
    method: "POST",
    body: payload,
    errorLabel: "启动连续创作失败",
  });
}

/** 获取一次运行的实时状态 */
export async function getPipelineRun(
  runId: string,
): Promise<PipelineRunState> {
  return request<PipelineRunState>(
    `/agents/runs/${encodeURIComponent(runId)}`,
    { errorLabel: "获取 Pipeline 进度失败", includeErrorText: false },
  );
}
