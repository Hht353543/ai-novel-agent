/**
 * 小说项目（大纲 + 章节草稿）存储接口封装。
 */
import type { CharacterCard, NovelOutline } from "./novel";
import { request } from "./client";

/** 单个章节草稿 */
export interface ChapterDraft {
  volume_index: number;
  chapter_index: number;
  chapter_title: string;
  content: string;
}

/** 完整小说项目 */
export interface NovelProject {
  id: string;
  title: string;
  outline: NovelOutline;
  chapters: ChapterDraft[];
  character_cards: CharacterCard[];
  memory: string;
  created_at: string;
  updated_at: string;
}

/** 项目列表摘要 */
export interface ProjectSummary {
  id: string;
  title: string;
  chapter_count: number;
  created_at: string;
  updated_at: string;
}

/** 保存项目请求体 */
export interface ProjectSaveRequest {
  id?: string;
  title?: string;
  outline: NovelOutline;
  chapters: ChapterDraft[];
  character_cards: CharacterCard[];
  memory: string;
}

/** 列出所有已保存项目 */
export async function listProjects(): Promise<ProjectSummary[]> {
  const data = await request<{ projects: ProjectSummary[] }>("/projects", {
    errorLabel: "获取项目列表失败",
    includeErrorText: false,
  });
  return data.projects;
}

/** 保存（新建或更新）项目 */
export async function saveProject(
  payload: ProjectSaveRequest,
): Promise<NovelProject> {
  const data = await request<{ project: NovelProject }>("/projects", {
    method: "POST",
    body: payload,
    errorLabel: "保存项目失败",
  });
  return data.project;
}

/** 按 ID 读取完整项目 */
export async function getProject(id: string): Promise<NovelProject> {
  return request<NovelProject>(`/projects/${encodeURIComponent(id)}`, {
    errorLabel: "读取项目失败",
    includeErrorText: false,
  });
}

/** 删除项目 */
export async function deleteProject(id: string): Promise<void> {
  await request<{ success: boolean }>(`/projects/${encodeURIComponent(id)}`, {
    method: "DELETE",
    errorLabel: "删除项目失败",
    includeErrorText: false,
  });
}
