/**
 * 小说项目（大纲 + 章节草稿）存储接口封装。
 */
import type { CharacterCard, NovelOutline } from "./novel";

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
}

const BASE_URL = "/api";

/** 列出所有已保存项目 */
export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await fetch(`${BASE_URL}/projects`, { method: "GET" });
  if (!response.ok) {
    throw new Error(`获取项目列表失败 (${response.status})`);
  }
  const data = (await response.json()) as { projects: ProjectSummary[] };
  return data.projects;
}

/** 保存（新建或更新）项目 */
export async function saveProject(
  request: ProjectSaveRequest,
): Promise<NovelProject> {
  const response = await fetch(`${BASE_URL}/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`保存项目失败 (${response.status}): ${text.slice(0, 200)}`);
  }
  const data = (await response.json()) as { project: NovelProject };
  return data.project;
}

/** 按 ID 读取完整项目 */
export async function getProject(id: string): Promise<NovelProject> {
  const response = await fetch(`${BASE_URL}/projects/${encodeURIComponent(id)}`, {
    method: "GET",
  });
  if (!response.ok) {
    throw new Error(`读取项目失败 (${response.status})`);
  }
  return (await response.json()) as NovelProject;
}

/** 删除项目 */
export async function deleteProject(id: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/projects/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`删除项目失败 (${response.status})`);
  }
}
