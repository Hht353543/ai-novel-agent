import { ref } from "vue";
import type { CharacterCard } from "../api/novel";
import type { ChapterDraft } from "../api/project";
import {
  chapterAttachKey,
  chapterCardsKey,
  chapterDraftKey,
  chapterExtraKey,
  copyProjectKeys,
  generateProjectKey,
  migrateLegacyProjectKeys,
  OUTLINE_PROJECT_KEY,
  safeSetItem,
} from "../utils/storage";

/**
 * 草稿存储：以项目标识为前缀管理章节草稿 / 额外要求 / 附件键、
 * 角色卡备份与一次性旧键迁移。
 */
export function useDraftStorage() {
  const projectKey = ref("");
  const chaptersMap = ref<Record<string, ChapterDraft>>({});
  // 草稿写入防抖间隔（毫秒）
  const DRAFT_SAVE_DEBOUNCE_MS = 500;
  // 单章草稿大小提示阈值（字符）
  const MAX_DRAFT_CHARS = 100_000;
  let draftTimer: ReturnType<typeof setTimeout> | undefined;
  let pendingDraft: {
    volumeIndex: number;
    chapterIndex: number;
    chapterTitle: string;
    content: string;
  } | null = null;

  function setProjectKey(key: string): void {
    projectKey.value = key;
  }

  /** 恢复/创建未保存大纲的本地项目标识，并设为当前标识 */
  function ensureOutlineProjectKey(): string {
    let key = localStorage.getItem(OUTLINE_PROJECT_KEY);
    if (!key) {
      key = generateProjectKey();
      safeSetItem(OUTLINE_PROJECT_KEY, key);
    }
    projectKey.value = key;
    return key;
  }

  function draftKey(volumeIndex: number, chapterIndex: number): string {
    return chapterDraftKey(projectKey.value, volumeIndex, chapterIndex);
  }

  function extraKey(volumeIndex: number, chapterIndex: number): string {
    return chapterExtraKey(projectKey.value, volumeIndex, chapterIndex);
  }

  function attachKey(volumeIndex: number, chapterIndex: number): string {
    return chapterAttachKey(projectKey.value, volumeIndex, chapterIndex);
  }

  function cardsKey(): string {
    return chapterCardsKey(projectKey.value);
  }

  function saveDraft(
    volumeIndex: number,
    chapterIndex: number,
    chapterTitle: string,
    content: string,
  ): void {
    const entry: ChapterDraft = {
      volume_index: volumeIndex,
      chapter_index: chapterIndex,
      chapter_title: chapterTitle,
      content,
    };
    chaptersMap.value[`${volumeIndex}_${chapterIndex}`] = entry;
    safeSetItem(draftKey(volumeIndex, chapterIndex), content);
  }

  /** 防抖保存草稿：连续键入只落盘最后一次（500ms 内） */
  function saveDraftDebounced(
    volumeIndex: number,
    chapterIndex: number,
    chapterTitle: string,
    content: string,
  ): void {
    pendingDraft = { volumeIndex, chapterIndex, chapterTitle, content };
    if (content.length > MAX_DRAFT_CHARS) {
      console.warn(
        "章节草稿超过 10 万字符，本地存储可能受限，建议及时点击「保存项目」。",
      );
    }
    if (draftTimer !== undefined) clearTimeout(draftTimer);
    draftTimer = setTimeout(() => {
      draftTimer = undefined;
      if (pendingDraft) {
        const p = pendingDraft;
        pendingDraft = null;
        saveDraft(p.volumeIndex, p.chapterIndex, p.chapterTitle, p.content);
      }
    }, DRAFT_SAVE_DEBOUNCE_MS);
  }

  /** 强制落盘待写入的草稿（切章 / 保存 / 关闭页面前调用） */
  function flushDraft(): void {
    if (draftTimer !== undefined) {
      clearTimeout(draftTimer);
      draftTimer = undefined;
    }
    if (pendingDraft) {
      const p = pendingDraft;
      pendingDraft = null;
      saveDraft(p.volumeIndex, p.chapterIndex, p.chapterTitle, p.content);
    }
  }

  function getChapterDraft(
    volumeIndex: number,
    chapterIndex: number,
  ): ChapterDraft | undefined {
    return chaptersMap.value[`${volumeIndex}_${chapterIndex}`];
  }

  function readDraft(volumeIndex: number, chapterIndex: number): string {
    return (
      getChapterDraft(volumeIndex, chapterIndex)?.content ??
      localStorage.getItem(draftKey(volumeIndex, chapterIndex)) ??
      ""
    );
  }

  function readExtra(volumeIndex: number, chapterIndex: number): string {
    return localStorage.getItem(extraKey(volumeIndex, chapterIndex)) ?? "";
  }

  function saveExtra(
    volumeIndex: number,
    chapterIndex: number,
    value: string,
  ): void {
    safeSetItem(extraKey(volumeIndex, chapterIndex), value);
  }

  function readCards(): CharacterCard[] | null {
    const raw = localStorage.getItem(cardsKey());
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as unknown;
      return Array.isArray(parsed) ? (parsed as CharacterCard[]) : null;
    } catch {
      return null;
    }
  }

  function saveCards(cards: CharacterCard[]): void {
    safeSetItem(cardsKey(), JSON.stringify(cards));
  }

  function resetChaptersMap(): void {
    chaptersMap.value = {};
  }

  function setChaptersMapEntry(
    volumeIndex: number,
    chapterIndex: number,
    draft: ChapterDraft,
  ): void {
    chaptersMap.value[`${volumeIndex}_${chapterIndex}`] = draft;
  }

  /** 一次性只读迁移：旧「书名」键数据复制到当前项目标识 */
  function migrateLegacy(title: string): void {
    migrateLegacyProjectKeys(projectKey.value, title);
  }

  /** 未保存大纲保存为服务端项目后：复制本地草稿并切换到服务端 id */
  function promoteToProject(projectId: string): void {
    if (projectKey.value && projectKey.value !== projectId) {
      copyProjectKeys(projectKey.value, projectId);
    }
    projectKey.value = projectId;
  }

  return {
    projectKey,
    chaptersMap,
    setProjectKey,
    ensureOutlineProjectKey,
    draftKey,
    extraKey,
    attachKey,
    cardsKey,
    saveDraft,
    saveDraftDebounced,
    flushDraft,
    getChapterDraft,
    readDraft,
    readExtra,
    saveExtra,
    readCards,
    saveCards,
    resetChaptersMap,
    setChaptersMapEntry,
    migrateLegacy,
    promoteToProject,
  };
}
