/**
 * 后端接口封装。
 */

/** 生成小说大纲的请求体 */
export interface NovelGenerateRequest {
  title: string;
  genre: string;
  theme: string;
  keywords: string;
  requirement: string;
  /** 用户自由输入的其他要求（风格、雷区、参考作品等） */
  extra_requirements: string;
  /** 上传的本地 txt 附件文件名（可空） */
  attachment_name: string;
  /** 上传的本地 txt 附件文本内容（可空） */
  attachment_text: string;
}

/** RAG 检索到的单条上下文 */
export interface ContextItem {
  source: string;
  content: string;
  /** 知识库板块（世界观/剧情大纲/人物角色卡/other 等） */
  category?: string;
}

/** 大纲中的角色 */
export interface Character {
  name: string;
  role: string;
  description: string;
}

/** 大纲中的卷计划 */
export interface VolumePlan {
  volume: string;
  chapters: string[];
}

/** 角色卡：精确定义某卷中一个角色的设定 */
export interface CharacterCard {
  volume_index: number;
  name: string;
  role: string;
  age: string;
  appearance: string;
  personality: string;
  background: string;
  goals: string;
  speech_style: string;
  notes: string;
}

/** AI 生成的小说大纲 */
export interface NovelOutline {
  title: string;
  summary: string;
  world: string;
  characters: Character[];
  volume_plan: VolumePlan[];
}

/** 生成接口响应 */
export interface NovelGenerateResponse {
  success: boolean;
  status: "success" | "demo" | "error";
  message: string;
  context: ContextItem[];
  outline: NovelOutline;
}

/** 章节正文生成 / 续写 / 重写请求体 */
export interface ChapterGenerateRequest {
  outline: NovelOutline;
  volume_index: number;
  chapter_index: number;
  chapter_title: string;
  /** 已确认 / 人工编辑过的上文 */
  context_text: string;
  /** 前一章正文（结尾部分），用于跨章衔接（可空） */
  previous_chapter_text: string;
  /** generate=首次生成 / continue=文末续写 / rewrite=从修改处重写 */
  mode: "generate" | "continue" | "rewrite";
  /** 期望生成字数 */
  target_length: number;
  /** 当前卷角色卡（生成时按卡片定义角色） */
  character_cards: CharacterCard[];
  /** 正文写作额外要求 */
  extra_requirements: string;
  /** 上传的本地 txt 附件文件名（可空） */
  attachment_name: string;
  /** 上传的本地 txt 附件文本内容（可空） */
  attachment_text: string;
}

/** 章节正文生成接口响应 */
export interface ChapterGenerateResponse {
  success: boolean;
  status: "success" | "demo" | "error";
  message: string;
  /** 本次新生成的正文 */
  content: string;
  /** 上文 + 新生成内容，可直接替换编辑器全文 */
  full_text: string;
}

/** 按卷生成角色卡的请求 */
export interface CharacterCardsGenerateRequest {
  outline: NovelOutline;
  volume_index: number;
  volume_label: string;
}

/** 按卷生成角色卡的响应 */
export interface CharacterCardsGenerateResponse {
  success: boolean;
  status: "success" | "demo" | "error";
  message: string;
  character_cards: CharacterCard[];
}

/** 章节标题生成请求 */
export interface TitlesGenerateRequest {
  outline: NovelOutline;
  volume_index: number;
  volume_label: string;
  /** volume=按卷生成前10章标题 / chapter=根据正文生成单章标题 */
  mode: "volume" | "chapter";
  chapter_index: number;
  chapter_text: string;
  existing_titles: string[];
}

/** 章节标题生成响应 */
export interface TitlesGenerateResponse {
  success: boolean;
  status: "success" | "demo" | "error";
  message: string;
  titles: string[];
}

const BASE_URL = "/api";

/**
 * 调用后端生成小说大纲。
 * @throws Error 网络错误或后端返回错误时抛出
 */
export async function generateNovel(
  request: NovelGenerateRequest,
): Promise<NovelGenerateResponse> {
  const response = await fetch(`${BASE_URL}/novel/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`后端请求失败 (${response.status}): ${text.slice(0, 200)}`);
  }

  return (await response.json()) as NovelGenerateResponse;
}

/**
 * 仅检索知识库（调试用）。
 */
export async function retrieveContext(
  request: NovelGenerateRequest,
): Promise<{ context: ContextItem[] }> {
  const response = await fetch(`${BASE_URL}/novel/retrieve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`检索失败 (${response.status})`);
  }
  return (await response.json()) as { context: ContextItem[] };
}

/**
 * 调用后端生成 / 续写 / 重写章节正文。
 * @throws Error 网络错误或后端返回错误时抛出
 */
export async function generateChapter(
  request: ChapterGenerateRequest,
): Promise<ChapterGenerateResponse> {
  const response = await fetch(`${BASE_URL}/novel/chapter/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`后端请求失败 (${response.status}): ${text.slice(0, 200)}`);
  }

  return (await response.json()) as ChapterGenerateResponse;
}

/**
 * 调用后端按卷生成角色卡。
 * @throws Error 网络错误或后端返回错误时抛出
 */
export async function generateCharacterCards(
  request: CharacterCardsGenerateRequest,
): Promise<CharacterCardsGenerateResponse> {
  const response = await fetch(
    `${BASE_URL}/novel/character-cards/generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`角色卡生成失败 (${response.status}): ${text.slice(0, 200)}`);
  }

  return (await response.json()) as CharacterCardsGenerateResponse;
}

/**
 * 调用后端生成章节标题（按卷前10章 / 根据正文单章）。
 * @throws Error 网络错误或后端返回错误时抛出
 */
export async function generateTitles(
  request: TitlesGenerateRequest,
): Promise<TitlesGenerateResponse> {
  const response = await fetch(`${BASE_URL}/novel/titles/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`标题生成失败 (${response.status}): ${text.slice(0, 200)}`);
  }

  return (await response.json()) as TitlesGenerateResponse;
}
