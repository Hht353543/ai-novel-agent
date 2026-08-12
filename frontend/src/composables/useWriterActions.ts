/**
 * 章节写作页的全部业务编排动作。
 *
 * 从 ChapterWriterView.vue 抽出：项目 CRUD、章节生成（流式 + 回退）、
 * 标题生成、审校、角色卡管理、草稿同步与页面生命周期。
 * 视图只保留模板与事件接线。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  generateChapter,
  generateCharacterCards,
  generateTitles,
  reviewChapter,
  streamChapter,
  type ChapterGenerateRequest,
  type CharacterCard,
  type NovelOutline,
  type ReviewIssue,
} from "../api/novel";
import {
  deleteProject,
  getProject,
  listProjects,
  saveProject,
  type NovelProject,
} from "../api/project";
import {
  chapterDraftPrefix,
  LAST_PROJECT_KEY,
  OUTLINE_KEY,
  safeRemoveItem,
  safeSetItem,
} from "../utils/storage";
import { useWriterState } from "./useWriterState";

// 跨章衔接时携带的上一章结尾字符数
const PREVIOUS_CHAPTER_TAIL_CHARS = 2500;

/** 生成模式的中文名称（纯函数，便于测试） */
export function modeName(mode: string): string {
  if (mode === "rewrite") return "从光标处重写";
  if (mode === "continue") return "从文末续写";
  return "章节开头";
}

/** 把流式增量拼到基底文本上（纯函数，便于测试） */
export function joinStream(baseText: string, streamed: string): string {
  return baseText ? `${baseText.replace(/\s+$/, "")}\n\n${streamed}` : streamed;
}

export interface ChapterPayloadInput {
  outline: NovelOutline;
  volumeIndex: number;
  chapterIndex: number;
  chapterTitle: string;
  contextText: string;
  previousChapterText: string;
  mode: "generate" | "continue" | "rewrite";
  targetLength: number;
  characterCards: CharacterCard[];
  extraRequirements: string;
  attachmentName: string;
  attachmentText: string;
  memory: string;
}

/** 组装章节生成请求体（纯函数，便于测试） */
export function buildChapterPayload(input: ChapterPayloadInput): ChapterGenerateRequest {
  return {
    outline: input.outline,
    volume_index: input.volumeIndex,
    chapter_index: input.chapterIndex,
    chapter_title: input.chapterTitle,
    context_text: input.contextText,
    previous_chapter_text: input.previousChapterText,
    mode: input.mode,
    target_length: input.targetLength,
    character_cards: input.characterCards,
    extra_requirements: input.extraRequirements.trim(),
    attachment_name: input.attachmentName,
    attachment_text: input.attachmentText,
    memory: input.memory,
  };
}

export function useWriterActions() {
  const {
    outline,
    text,
    volumeIndex,
    chapterIndex,
    cursorPos,
    targetLength,
    extraReq,
    loading,
    saving,
    message,
    isError,
    projectId,
    projectList,
    showProjectList,
    characterCards,
    viewMode,
    cardVolumeIndex,
    generatingCards,
    generatingTitle,
    memory,
    storage,
    projectKey,
    attachment: chapterAttachment,
    restoreAttachment,
  } = useWriterState();

  const reviewing = ref(false);
  const reviewIssues = ref<ReviewIssue[]>([]);

  const currentChapterTitle = computed(() => {
    if (!outline.value) return "";
    const vol = outline.value.volume_plan[volumeIndex.value];
    if (!vol) return "";
    return vol.chapters[chapterIndex.value] || `第${chapterIndex.value + 1}章`;
  });

  const currentCardVolumeLabel = computed(() => {
    if (!outline.value) return "第 1 卷";
    const vol = outline.value.volume_plan[cardVolumeIndex.value];
    return vol?.volume || `第${cardVolumeIndex.value + 1}卷`;
  });

  /** 当前选中的角色卡卷（角色卡面板展示用） */
  const volumeCards = computed(() =>
    characterCards.value.filter((c) => c.volume_index === cardVolumeIndex.value),
  );

  /** 当前正在编辑章节所属卷的角色卡（生成正文时使用） */
  const chapterVolumeCards = computed(() =>
    characterCards.value.filter((c) => c.volume_index === volumeIndex.value),
  );

  /** 取前一章正文的结尾部分（用于跨章衔接），没有则返回空串 */
  function getPreviousChapterText(): string {
    if (!outline.value || !projectKey.value) return "";
    let pv = volumeIndex.value;
    let pc = chapterIndex.value - 1;
    if (pc < 0) {
      if (pv <= 0) return "";
      pv -= 1;
      const prevVol = outline.value.volume_plan[pv];
      if (!prevVol) return "";
      pc = prevVol.chapters.length - 1;
    }
    const draft = storage.readDraft(pv, pc);
    if (!draft.trim()) return "";
    // 只取结尾约 2500 字，既保证衔接又控制 Prompt 长度
    return draft.trim().slice(-PREVIOUS_CHAPTER_TAIL_CHARS);
  }

  /** 把编辑器当前内容同步到内存 chaptersMap 与 localStorage（双保险） */
  function syncCurrentToMap(): void {
    storage.flushDraft();
    if (!outline.value || !projectKey.value) return;
    storage.saveDraft(
      volumeIndex.value,
      chapterIndex.value,
      currentChapterTitle.value,
      text.value,
    );
  }

  function loadDraft(): void {
    restoreAttachment();
    extraReq.value = storage.readExtra(volumeIndex.value, chapterIndex.value);
    text.value = storage.readDraft(volumeIndex.value, chapterIndex.value);
    cursorPos.value = text.value.length;
  }

  function selectChapter(vi: number, ci: number): void {
    syncCurrentToMap();
    volumeIndex.value = vi;
    chapterIndex.value = ci;
    message.value = "";
    reviewIssues.value = [];
    loadDraft();
  }

  function recordCursor(position: number): void {
    cursorPos.value = position ?? text.value.length;
  }

  // ---------- 项目保存 / 打开 ----------

  async function refreshProjectList(): Promise<void> {
    try {
      projectList.value = await listProjects();
      showProjectList.value = true;
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "获取项目列表失败";
    }
  }

  function applyProject(project: NovelProject): void {
    projectId.value = project.id;
    storage.setProjectKey(project.id);
    outline.value = project.outline;
    storage.resetChaptersMap();
    for (const c of project.chapters) {
      storage.setChaptersMapEntry(c.volume_index, c.chapter_index, c);
    }
    characterCards.value = [...(project.character_cards || [])];
    memory.value = project.memory || "";
    // 一次性只读迁移：旧版本按书名存草稿，目标键不存在时复制到新项目标识。
    // 不覆盖新数据、不删除旧键（历史同名项目数据本就无法区分归属）。
    storage.migrateLegacy(project.outline.title);
    // 合并本地的实时草稿：只匹配当前项目标识，避免同名项目串数据；
    // 刷新前尚未“保存项目”的编辑以 localStorage 为准，避免后端旧版本覆盖最近键入的内容。
    const prefix = chapterDraftPrefix(project.id);
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key || !key.startsWith(prefix)) continue;
      const match = key.slice(prefix.length).match(/^(\d+)_(\d+)$/);
      if (!match) continue;
      const vi = Number(match[1]);
      const ci = Number(match[2]);
      const vol = project.outline.volume_plan[vi];
      storage.setChaptersMapEntry(vi, ci, {
        volume_index: vi,
        chapter_index: ci,
        chapter_title: vol?.chapters[ci] || `第${ci + 1}章`,
        content: localStorage.getItem(key) ?? "",
      });
    }
    volumeIndex.value = 0;
    chapterIndex.value = 0;
    cardVolumeIndex.value = 0;
    loadDraft();
    safeSetItem(LAST_PROJECT_KEY, project.id);

    // 合并本地的实时角色卡备份（刷新前未保存的编辑优先）
    const localCards = storage.readCards();
    if (localCards && localCards.length) {
      characterCards.value = localCards;
    }
  }

  async function openProject(id: string): Promise<void> {
    try {
      const project = await getProject(id);
      applyProject(project);
      showProjectList.value = false;
      isError.value = false;
      message.value = `已打开《${project.title}》`;
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "读取项目失败";
    }
  }

  async function onSaveProject(): Promise<void> {
    if (!outline.value) return;
    syncCurrentToMap();
    saving.value = true;
    message.value = "";
    isError.value = false;
    try {
      const chapters = Object.values(storage.chaptersMap.value)
        .filter((c) => c.content.trim())
        .sort(
          (a, b) =>
            a.volume_index - b.volume_index || a.chapter_index - b.chapter_index,
        );
      const saved = await saveProject({
        id: projectId.value || undefined,
        title: outline.value.title,
        outline: outline.value,
        chapters,
        character_cards: characterCards.value,
        memory: memory.value,
      });
      projectId.value = saved.id;
      // 未保存大纲升级为服务端项目后，把本地标识下的草稿复制到服务端 id（只补缺、不删除）
      storage.promoteToProject(saved.id);
      safeSetItem(LAST_PROJECT_KEY, saved.id);
      message.value = `保存成功：共 ${chapters.length} 章内容`;
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "保存项目失败";
    } finally {
      saving.value = false;
    }
  }

  async function onDeleteProject(id: string): Promise<void> {
    if (!window.confirm("确定删除该项目？删除后不可恢复。")) return;
    try {
      await deleteProject(id);
      projectList.value = projectList.value.filter((p) => p.id !== id);
      if (id === projectId.value) {
        projectId.value = "";
        safeRemoveItem(LAST_PROJECT_KEY);
      }
      message.value = "项目已删除";
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "删除项目失败";
    }
  }

  // ---------- 正文生成 ----------

  async function callGenerate(
    mode: "generate" | "continue" | "rewrite",
    contextText: string,
    confirmText: string,
  ): Promise<void> {
    if (!outline.value) return;
    if (confirmText && !window.confirm(confirmText)) return;

    loading.value = true;
    message.value = "";
    isError.value = false;
    const requestPayload = buildChapterPayload({
      outline: outline.value,
      volumeIndex: volumeIndex.value,
      chapterIndex: chapterIndex.value,
      chapterTitle: currentChapterTitle.value,
      contextText,
      previousChapterText: getPreviousChapterText(),
      mode,
      targetLength: targetLength.value,
      characterCards: chapterVolumeCards.value,
      extraRequirements: extraReq.value,
      attachmentName: chapterAttachment.value?.name ?? "",
      attachmentText: chapterAttachment.value?.content ?? "",
      memory: memory.value,
    });

    // 流式基础文本：generate 从空开始；continue/rewrite 以 contextText 为基底
    const baseText = mode === "generate" ? "" : contextText;
    let streamed = "";
    let streamEnded = false;

    const applyStreamed = (): void => {
      text.value = joinStream(baseText, streamed);
      cursorPos.value = text.value.length;
      syncCurrentToMap();
    };

    try {
      await streamChapter(requestPayload, {
        onDelta: (piece) => {
          streamed += piece;
          text.value = joinStream(baseText, streamed);
        },
        onMeta: (meta) => {
          streamEnded = true;
          if (meta.status === "success") {
            if (meta.memory !== undefined) memory.value = meta.memory;
            applyStreamed();
            message.value = `已生成约 ${meta.content_len ?? streamed.length} 字（${modeName(mode)}）。`;
          } else if (meta.status === "demo") {
            if (meta.memory !== undefined) memory.value = meta.memory;
            applyStreamed();
            message.value = meta.message || "演示模式";
          } else {
            isError.value = true;
            message.value = meta.message || "流式生成失败";
          }
        },
      });
      // 流正常结束但未收到 meta 事件时的兜底
      if (!streamEnded) {
        applyStreamed();
        message.value = `已生成约 ${streamed.length} 字（${modeName(mode)}）。`;
      }
    } catch (err) {
      // 网络/流中断：回退到旧的非流式接口
      try {
        const result = await generateChapter(requestPayload);
        if (!result.success) {
          isError.value = true;
          message.value = result.message || "生成失败，请检查后端服务";
          return;
        }
        text.value = result.full_text || result.content;
        memory.value = result.memory || memory.value;
        cursorPos.value = text.value.length;
        syncCurrentToMap();
        message.value =
          result.status === "demo"
            ? result.message
            : `已生成约 ${result.content.length} 字（${modeName(mode)}）。`;
      } catch (fallbackErr) {
        isError.value = true;
        message.value =
          fallbackErr instanceof Error ? fallbackErr.message : "生成失败，请检查后端服务";
      }
    } finally {
      loading.value = false;
    }
  }

  function onGenerate(): void {
    void callGenerate(
      "generate",
      "",
      text.value.trim()
        ? "当前章节已有内容，重新生成会覆盖全部内容，确定继续吗？"
        : "",
    );
  }

  function onContinue(): void {
    void callGenerate("continue", text.value, "");
  }

  function onRewrite(): void {
    if (!text.value.trim()) {
      message.value = "请先写一些内容，再把光标放到修改处。";
      isError.value = true;
      return;
    }
    const before = text.value.slice(0, cursorPos.value);
    if (!before.trim()) {
      message.value = "光标位置太靠前，请把光标放在修改处之后再点击重写。";
      isError.value = true;
      return;
    }
    void callGenerate(
      "rewrite",
      before,
      "将丢弃光标之后的内容并重新生成，确定继续吗？",
    );
  }

  /** 根据当前正文重新生成本章标题 */
  async function onGenerateTitleFromText(): Promise<void> {
    if (!outline.value) return;
    if (!text.value.trim()) {
      message.value = "请先写正文，再根据正文生成标题。";
      isError.value = true;
      return;
    }
    if (!window.confirm("将根据当前正文重新生成本章标题并替换目录，确定继续吗？")) {
      return;
    }
    generatingTitle.value = true;
    message.value = "";
    isError.value = false;
    try {
      const vi = volumeIndex.value;
      const ci = chapterIndex.value;
      const resp = await generateTitles({
        outline: outline.value,
        volume_index: vi,
        volume_label:
          outline.value.volume_plan[vi]?.volume || `第${vi + 1}卷`,
        mode: "chapter",
        chapter_index: ci,
        chapter_text: text.value,
        existing_titles: [],
      });
      if (!resp.success) {
        isError.value = true;
        message.value = resp.message || "标题生成失败";
        return;
      }
      const title = resp.titles[0]?.trim();
      if (!title) {
        isError.value = true;
        message.value = "返回的标题为空";
        return;
      }
      // 全书连续章号
      let start = 1;
      for (let i = 0; i < vi; i++) {
        start += outline.value.volume_plan[i].chapters.length;
      }
      const newLabel = `第${start + ci}章 ${title}`;
      outline.value.volume_plan[vi].chapters[ci] = newLabel;
      syncCurrentToMap(); // 同步章节草稿中的 chapter_title
      safeSetItem(OUTLINE_KEY, JSON.stringify(outline.value));
      message.value =
        resp.status === "demo"
          ? resp.message
          : `已更新标题：${newLabel}（记得点「保存项目」同步到存储）`;
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "标题生成失败";
    } finally {
      generatingTitle.value = false;
    }
  }

  /** 审校当前章节（一致性/爽点/错字/设定冲突） */
  async function onReviewChapter(): Promise<void> {
    if (!outline.value) return;
    if (!text.value.trim()) {
      message.value = "请先写正文，再审校本章。";
      isError.value = true;
      return;
    }
    reviewing.value = true;
    message.value = "";
    isError.value = false;
    try {
      const resp = await reviewChapter({
        outline: outline.value,
        chapter_title: currentChapterTitle.value,
        chapter_text: text.value,
        memory: memory.value,
      });
      if (resp.status === "success") {
        reviewIssues.value = resp.issues;
        message.value = resp.issues.length
          ? `审校完成：发现 ${resp.issues.length} 条问题`
          : "审校完成：未发现问题";
      } else {
        isError.value = true;
        message.value = resp.message || "审校失败";
      }
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "审校失败";
    } finally {
      reviewing.value = false;
    }
  }

  // ---------- 角色卡 ----------

  function switchToChapter(): void {
    viewMode.value = "chapter";
  }

  function switchToCards(): void {
    // 打开角色卡视图时，默认定位到当前正在编辑的卷
    cardVolumeIndex.value = volumeIndex.value;
    viewMode.value = "cards";
  }

  async function onGenerateCards(): Promise<void> {
    if (!outline.value) return;
    const vi = cardVolumeIndex.value;
    if (
      volumeCards.value.length &&
      !window.confirm("AI 生成会覆盖本卷现有角色卡，确定继续吗？")
    ) {
      return;
    }
    generatingCards.value = true;
    message.value = "";
    isError.value = false;
    try {
      const resp = await generateCharacterCards({
        outline: outline.value,
        volume_index: vi,
        volume_label: currentCardVolumeLabel.value,
      });
      if (!resp.success) {
        isError.value = true;
        message.value = resp.message || "角色卡生成失败";
        return;
      }
      const cardsWithVolume = resp.character_cards.map((c) => ({
        ...c,
        volume_index: vi,
      }));
      characterCards.value = [
        ...characterCards.value.filter((c) => c.volume_index !== vi),
        ...cardsWithVolume,
      ];
      message.value =
        resp.status === "demo"
          ? resp.message
          : `已生成 ${cardsWithVolume.length} 张角色卡，可继续编辑。`;
    } catch (err) {
      isError.value = true;
      message.value = err instanceof Error ? err.message : "角色卡生成失败";
    } finally {
      generatingCards.value = false;
    }
  }

  function onAddCard(): void {
    characterCards.value.push({
      volume_index: cardVolumeIndex.value,
      name: "",
      role: "",
      age: "",
      appearance: "",
      personality: "",
      background: "",
      goals: "",
      speech_style: "",
      notes: "",
    });
  }

  function onRemoveCard(card: CharacterCard): void {
    if (!window.confirm(`确定删除角色卡「${card.name || "未命名角色"}」？`)) return;
    characterCards.value = characterCards.value.filter((c) => c !== card);
  }

  // ---------- 生命周期与实时落盘 ----------

  function handleBeforeUnload(): void {
    syncCurrentToMap();
  }

  onMounted(async () => {
    // 刷新/关闭前把正在编辑的内容同步到 localStorage，防止输入丢失
    window.addEventListener("beforeunload", handleBeforeUnload);
    // 1) 优先恢复上次保存的项目（大纲 + 章节一起调出）
    const lastId = localStorage.getItem(LAST_PROJECT_KEY);
    if (lastId) {
      try {
        const project = await getProject(lastId);
        applyProject(project);
        return;
      } catch {
        safeRemoveItem(LAST_PROJECT_KEY);
      }
    }
    // 2) 兜底：从大纲页带过来的 outline（尚未保存过项目）
    try {
      const raw = localStorage.getItem(OUTLINE_KEY);
      outline.value = raw ? (JSON.parse(raw) as NovelOutline) : null;
    } catch {
      outline.value = null;
    }
    if (outline.value) {
      memory.value = "";
      // 未保存大纲使用本地项目标识；没有则生成一个并持久化
      storage.ensureOutlineProjectKey();
      // 一次性只读迁移：旧「书名」键数据复制到新标识（只补缺、不覆盖、不删除）
      storage.migrateLegacy(outline.value.title);
      loadDraft();
      // 恢复本地的角色卡实时备份
      const localCards = storage.readCards();
      if (localCards) {
        characterCards.value = localCards;
      }
    }
  });

  onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", handleBeforeUnload);
  });

  // 输入实时落盘：每次键入都同步到 localStorage / chaptersMap，
  // 这样即使刷新或意外关闭页面也不会丢失未保存的内容。
  watch(text, () => {
    if (outline.value && projectKey.value) {
      storage.saveDraftDebounced(
        volumeIndex.value,
        chapterIndex.value,
        currentChapterTitle.value,
        text.value,
      );
    }
  });

  // 角色卡实时备份：编辑角色卡后即使不点保存，刷新也不会丢
  watch(
    characterCards,
    () => {
      if (outline.value && projectKey.value) {
        storage.saveCards(characterCards.value);
      }
    },
    { deep: true },
  );

  // 其他要求实时保存：刷新不丢
  watch(extraReq, () => {
    if (outline.value && projectKey.value) {
      storage.saveExtra(volumeIndex.value, chapterIndex.value, extraReq.value);
    }
  });

  return {
    currentChapterTitle,
    currentCardVolumeLabel,
    volumeCards,
    reviewing,
    reviewIssues,
    selectChapter,
    recordCursor,
    refreshProjectList,
    openProject,
    onSaveProject,
    onDeleteProject,
    onGenerate,
    onContinue,
    onRewrite,
    onGenerateTitleFromText,
    onReviewChapter,
    switchToChapter,
    switchToCards,
    onGenerateCards,
    onAddCard,
    onRemoveCard,
  };
}
