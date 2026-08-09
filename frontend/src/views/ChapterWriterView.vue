<template>
  <div class="writer">
    <div class="toolbar">
      <router-link to="/" class="back-link">← 返回大纲生成</router-link>
      <h2 v-if="outline">{{ outline.title || "未命名小说" }}</h2>
      <div class="toolbar-actions">
        <button class="btn small" @click="refreshProjectList">打开项目</button>
        <button
          class="btn small primary"
          :disabled="saving || !outline"
          @click="onSaveProject"
        >
          {{ saving ? "保存中…" : "保存项目" }}
        </button>
      </div>
    </div>

    <div v-if="outline" class="layout">
      <!-- 左侧：章节导航 -->
      <aside class="sidebar">
        <div v-for="(vol, vi) in outline.volume_plan" :key="vi" class="volume">
          <h4>{{ vol.volume }}</h4>
          <button
            v-for="(chapter, ci) in vol.chapters"
            :key="ci"
            class="chapter-btn"
            :class="{ active: vi === volumeIndex && ci === chapterIndex }"
            @click="selectChapter(vi, ci)"
          >
            {{ chapter }}
          </button>
        </div>
      </aside>

      <!-- 右侧：可编辑正文 -->
      <main class="editor-panel">
        <div class="tabs">
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'chapter' }"
            @click="switchToChapter"
          >
            正文编辑
          </button>
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'cards' }"
            @click="switchToCards"
          >
            角色卡
          </button>
        </div>

        <template v-if="viewMode === 'chapter'">
          <div class="chapter-head">
            <h3>{{ currentChapterTitle }}</h3>
            <span class="word-count">已写 {{ text.length }} 字</span>
          </div>

          <textarea
            ref="editorRef"
            v-model="text"
            class="editor"
            placeholder="选择左侧章节，点击「生成本章开头」；也可以直接在这里手动写作。"
            @click="recordCursor"
            @keyup="recordCursor"
            @select="recordCursor"
          ></textarea>

          <div class="actions">
            <label class="length-picker">
              生成字数
              <select v-model.number="targetLength">
                <option :value="300">300</option>
                <option :value="600">600</option>
                <option :value="800" selected>800</option>
                <option :value="1200">1200</option>
                <option :value="2000">2000</option>
              </select>
            </label>
            <button class="btn" :disabled="loading" @click="onGenerate">生成本章开头</button>
            <button class="btn" :disabled="loading" @click="onContinue">从文末续写</button>
            <button class="btn primary" :disabled="loading" @click="onRewrite">
              {{ loading ? "生成中…" : "从光标处重写" }}
            </button>
            <button
              class="btn"
              :disabled="generatingTitle"
              @click="onGenerateTitleFromText"
            >
              {{ generatingTitle ? "生成中…" : "根据正文生成标题" }}
            </button>
          </div>

          <div class="extra-row">
            <label>
              其他要求（可选，生成时优先遵循）
              <input
                v-model="extraReq"
                type="text"
                placeholder="如：风格参考古龙，节奏明快；本章结尾留钩子；主角不要说教……"
              />
            </label>
          </div>

          <div class="extra-row attach-row">
            <span class="attach-label">
              本地 txt 附件（可选，内容视为最高优先级素材/要求）
            </span>
            <div class="attach-controls">
              <label v-if="!chapterAttachment" class="attach-btn">
                选择 txt 文件
                <input
                  type="file"
                  accept=".txt,text/plain"
                  @change="onAttachFile"
                />
              </label>
              <template v-else>
                <span class="attach-name">{{ chapterAttachment.name }}</span>
                <button class="attach-remove" @click="removeAttachment">移除</button>
              </template>
            </div>
          </div>

          <p class="hint">
            编辑正文后，把光标放在修改处，点击「从光标处重写」：光标前的内容会作为上文，
            重新生成光标之后的部分并替换。生成正文时会按本卷角色卡约束角色言行。
          </p>
        </template>

        <div v-else class="cards-panel">
          <div class="chapter-head">
            <h3>角色卡 · {{ currentCardVolumeLabel }}</h3>
            <div class="card-toolbar">
              <select v-model.number="cardVolumeIndex">
                <option
                  v-for="(vol, vi) in outline?.volume_plan || []"
                  :key="vi"
                  :value="vi"
                >
                  第{{ vi + 1 }}卷 {{ vol.volume }}
                </option>
              </select>
              <button
                class="btn"
                :disabled="generatingCards"
                @click="onGenerateCards"
              >
                {{ generatingCards ? "生成中…" : "AI 生成本卷角色卡" }}
              </button>
              <button class="btn" @click="onAddCard">添加角色卡</button>
            </div>
          </div>

          <div v-if="volumeCards.length" class="card-list">
            <details
              v-for="(card, i) in volumeCards"
              :key="i"
              class="card-item"
              :open="i === 0"
            >
              <summary>
                {{ card.name || "未命名角色" }}
                <span class="card-role">{{ card.role || "角色" }}</span>
              </summary>
              <div class="card-fields">
                <label>姓名<input v-model="card.name" type="text" /></label>
                <label>定位<input v-model="card.role" type="text" placeholder="按剧情实际需要填写，如主角/反派/搭档/长辈/配角" /></label>
                <label>年龄<input v-model="card.age" type="text" /></label>
                <label>外貌<textarea v-model="card.appearance" rows="2"></textarea></label>
                <label>性格<textarea v-model="card.personality" rows="3"></textarea></label>
                <label>背景<textarea v-model="card.background" rows="3"></textarea></label>
                <label>目标动机<textarea v-model="card.goals" rows="2"></textarea></label>
                <label>说话风格<textarea v-model="card.speech_style" rows="2"></textarea></label>
                <label>备注<textarea v-model="card.notes" rows="2"></textarea></label>
                <button class="delete-btn" @click="onRemoveCard(card)">删除该角色卡</button>
              </div>
            </details>
          </div>
          <p v-else class="cards-empty">
            本卷还没有角色卡。点击「AI 生成本卷角色卡」自动生成，或「添加角色卡」手动填写。
            编辑后的角色卡会随「保存项目」一起持久化，并在生成正文时约束角色设定。
          </p>
        </div>

        <p v-if="message" class="message" :class="{ error: isError }">{{ message }}</p>
      </main>
    </div>

    <div v-else class="empty">
      <p>还没有打开任何项目。</p>
      <button class="btn primary open-btn" @click="refreshProjectList">
        打开已保存的项目
      </button>
      <p>或先 <router-link to="/">生成大纲</router-link>，再进入章节写作。</p>
    </div>

    <!-- 已保存项目列表 -->
    <div v-if="showProjectList" class="modal-mask" @click.self="showProjectList = false">
      <div class="modal">
        <div class="modal-head">
          <h3>已保存的项目</h3>
          <button class="btn small" @click="showProjectList = false">关闭</button>
        </div>
        <div v-if="projectList.length" class="project-list">
          <div
            v-for="p in projectList"
            :key="p.id"
            class="project-item"
            @click="openProject(p.id)"
          >
            <div class="project-info">
              <strong>{{ p.title }}</strong>
              <span>{{ p.chapter_count }} 章 · {{ formatTime(p.updated_at) }}</span>
            </div>
            <button class="delete-btn" @click.stop="onDeleteProject(p.id)">删除</button>
          </div>
        </div>
        <p v-else class="modal-empty">暂无已保存的项目。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  generateCharacterCards,
  generateChapter,
  generateTitles,
  type CharacterCard,
  type NovelOutline,
} from "../api/novel";
import {
  deleteProject,
  getProject,
  listProjects,
  saveProject,
  type ChapterDraft,
  type NovelProject,
  type ProjectSummary,
} from "../api/project";
import { safeRemoveItem, safeSetItem } from "../utils/storage";

const OUTLINE_KEY = "novel_outline";
const LAST_PROJECT_KEY = "novel_last_project_id";

const outline = ref<NovelOutline | null>(null);
const text = ref("");
const volumeIndex = ref(0);
const chapterIndex = ref(0);
const cursorPos = ref(0);
const targetLength = ref(800);
const extraReq = ref("");
// 本章生成的本地 txt 附件
const chapterAttachment = ref<{ name: string; content: string } | null>(null);
const loading = ref(false);
const saving = ref(false);
const message = ref("");
const isError = ref(false);
const editorRef = ref<HTMLTextAreaElement | null>(null);

// 项目存储状态
const projectId = ref("");
const projectList = ref<ProjectSummary[]>([]);
const showProjectList = ref(false);
// 当前项目所有章节草稿：key = `${volume_index}_${chapter_index}`
const chaptersMap = ref<Record<string, ChapterDraft>>({});
// 角色卡：项目级数组，按 volume_index 区分卷
const characterCards = ref<CharacterCard[]>([]);
// 视图模式：chapter=正文编辑 / cards=角色卡
const viewMode = ref<"chapter" | "cards">("chapter");
const cardVolumeIndex = ref(0);
const generatingCards = ref(false);
const generatingTitle = ref(false);

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

/** 当前卷的角色卡（按 cardVolumeIndex 过滤） */
const volumeCards = computed(() =>
  characterCards.value.filter((c) => c.volume_index === cardVolumeIndex.value),
);

/** 当前正在编辑章节所属卷的角色卡（按 volumeIndex 过滤，生成正文时使用） */
const chapterVolumeCards = computed(() =>
  characterCards.value.filter((c) => c.volume_index === volumeIndex.value),
);

function chapterKey(vi: number, ci: number): string {
  return `${vi}_${ci}`;
}

function draftKey(): string {
  const title = outline.value?.title || "novel";
  return `novel_chapter_${title}_${volumeIndex.value}_${chapterIndex.value}`;
}

function extraKey(): string {
  const title = outline.value?.title || "novel";
  return `novel_extra_${title}_${volumeIndex.value}_${chapterIndex.value}`;
}

function attachKey(): string {
  const title = outline.value?.title || "novel";
  return `novel_attach_${title}_${volumeIndex.value}_${chapterIndex.value}`;
}

/** 取前一章正文的结尾部分（用于跨章衔接），没有则返回空串 */
function getPreviousChapterText(): string {
  if (!outline.value) return "";
  let pv = volumeIndex.value;
  let pc = chapterIndex.value - 1;
  if (pc < 0) {
    if (pv <= 0) return "";
    pv -= 1;
    const prevVol = outline.value.volume_plan[pv];
    if (!prevVol) return "";
    pc = prevVol.chapters.length - 1;
  }
  const draft = chaptersMap.value[chapterKey(pv, pc)];
  const text =
    draft?.content ??
    localStorage.getItem(
      `novel_chapter_${outline.value.title || "novel"}_${pv}_${pc}`,
    ) ??
    "";
  if (!text.trim()) return "";
  // 只取结尾约 2500 字，既保证衔接又控制 Prompt 长度
  return text.trim().slice(-2500);
}

/** 把编辑器当前内容同步到内存 chaptersMap 与 localStorage（双保险） */
function syncCurrentToMap(): void {
  if (!outline.value) return;
  chaptersMap.value[chapterKey(volumeIndex.value, chapterIndex.value)] = {
    volume_index: volumeIndex.value,
    chapter_index: chapterIndex.value,
    chapter_title: currentChapterTitle.value,
    content: text.value,
  };
  safeSetItem(draftKey(), text.value);
}

function loadDraft(): void {
  const draft = chaptersMap.value[chapterKey(volumeIndex.value, chapterIndex.value)];
  try {
    const raw = localStorage.getItem(attachKey());
    chapterAttachment.value = raw
      ? (JSON.parse(raw) as { name: string; content: string })
      : null;
  } catch {
    chapterAttachment.value = null;
  }
  extraReq.value = localStorage.getItem(extraKey()) ?? "";
  const saved = draft?.content ?? localStorage.getItem(draftKey()) ?? "";
  text.value = saved;
  cursorPos.value = text.value.length;
}

function selectChapter(vi: number, ci: number): void {
  syncCurrentToMap();
  volumeIndex.value = vi;
  chapterIndex.value = ci;
  message.value = "";
  loadDraft();
}

function recordCursor(): void {
  cursorPos.value = editorRef.value?.selectionStart ?? text.value.length;
}

/** 读取本地 txt 附件内容 */
function onAttachFile(event: Event): void {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".txt")) {
    message.value = "请选择 .txt 文本文件";
    isError.value = true;
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    chapterAttachment.value = {
      name: file.name,
      content: String(reader.result ?? ""),
    };
    safeSetItem(attachKey(), JSON.stringify(chapterAttachment.value));
    message.value = "";
  };
  reader.onerror = () => {
    isError.value = true;
    message.value = "读取附件失败，请重试";
  };
  reader.readAsText(file, "utf-8");
  input.value = "";
}

function removeAttachment(): void {
  chapterAttachment.value = null;
  safeRemoveItem(attachKey());
}

// ---------- 项目保存 / 打开 ----------

function formatTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

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
  outline.value = project.outline;
  chaptersMap.value = {};
  for (const c of project.chapters) {
    chaptersMap.value[chapterKey(c.volume_index, c.chapter_index)] = c;
  }
  characterCards.value = [...(project.character_cards || [])];
  // 合并本地的实时草稿：刷新前尚未“保存项目”的编辑以 localStorage 为准，
  // 避免后端旧版本覆盖最近键入的内容。
  const prefix = `novel_chapter_${project.outline.title || "novel"}_`;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (!key || !key.startsWith(prefix)) continue;
    const match = key.slice(prefix.length).match(/^(\d+)_(\d+)$/);
    if (!match) continue;
    const vi = Number(match[1]);
    const ci = Number(match[2]);
    const vol = project.outline.volume_plan[vi];
    chaptersMap.value[chapterKey(vi, ci)] = {
      volume_index: vi,
      chapter_index: ci,
      chapter_title: vol?.chapters[ci] || `第${ci + 1}章`,
      content: localStorage.getItem(key) ?? "",
    };
  }
  volumeIndex.value = 0;
  chapterIndex.value = 0;
  cardVolumeIndex.value = 0;
  loadDraft();
  safeSetItem(LAST_PROJECT_KEY, project.id);

  // 合并本地的实时角色卡备份（刷新前未保存的编辑优先）
  const cardsKey = `novel_cards_${project.outline.title || "novel"}`;
  const localCards = localStorage.getItem(cardsKey);
  if (localCards) {
    try {
      const parsed = JSON.parse(localCards) as CharacterCard[];
      if (Array.isArray(parsed) && parsed.length) {
        characterCards.value = parsed;
      }
    } catch {
      // 忽略损坏的本地数据
    }
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
    const chapters = Object.values(chaptersMap.value)
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
    });
    projectId.value = saved.id;
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
  try {
    const result = await generateChapter({
      outline: outline.value,
      volume_index: volumeIndex.value,
      chapter_index: chapterIndex.value,
      chapter_title: currentChapterTitle.value,
      context_text: contextText,
      previous_chapter_text: getPreviousChapterText(),
      mode,
      target_length: targetLength.value,
      character_cards: chapterVolumeCards.value,
      extra_requirements: extraReq.value.trim(),
      attachment_name: chapterAttachment.value?.name ?? "",
      attachment_text: chapterAttachment.value?.content ?? "",
    });
    if (!result.success) {
      isError.value = true;
      message.value = result.message || "生成失败，请检查后端服务";
      return;
    }
    text.value = result.full_text || result.content;
    cursorPos.value = text.value.length;
    syncCurrentToMap();
    message.value =
      result.status === "demo"
        ? result.message
        : `已生成约 ${result.content.length} 字（${modeName(mode)}）。`;
  } catch (err) {
    isError.value = true;
    message.value = err instanceof Error ? err.message : "生成失败，请检查后端服务";
  } finally {
    loading.value = false;
  }
}

function modeName(mode: string): string {
  if (mode === "rewrite") return "从光标处重写";
  if (mode === "continue") return "从文末续写";
  return "章节开头";
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
    safeSetItem("novel_outline", JSON.stringify(outline.value));
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
    loadDraft();
    // 恢复本地的角色卡实时备份
    const cardsKey = `novel_cards_${outline.value.title || "novel"}`;
    const localCards = localStorage.getItem(cardsKey);
    if (localCards) {
      try {
        const parsed = JSON.parse(localCards) as CharacterCard[];
        if (Array.isArray(parsed)) characterCards.value = parsed;
      } catch {
        // 忽略损坏的本地数据
      }
    }
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", handleBeforeUnload);
});

function handleBeforeUnload(): void {
  syncCurrentToMap();
}

// 输入实时落盘：每次键入都同步到 localStorage / chaptersMap，
// 这样即使刷新或意外关闭页面也不会丢失未保存的内容。
watch(text, () => {
  if (outline.value) syncCurrentToMap();
});

// 角色卡实时备份：编辑角色卡后即使不点保存，刷新也不会丢
watch(
  characterCards,
  () => {
    if (outline.value) {
      safeSetItem(
        `novel_cards_${outline.value.title || "novel"}`,
        JSON.stringify(characterCards.value),
      );
    }
  },
  { deep: true },
);

// 其他要求实时保存：刷新不丢
watch(extraReq, () => {
  if (outline.value) {
    safeSetItem(extraKey(), extraReq.value);
  }
});
</script>

<style scoped>
.writer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 18px;
}

.toolbar h2 {
  font-size: 20px;
  color: #6ea8ff;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.btn.small {
  padding: 8px 14px;
  font-size: 13px;
}

.btn.small.primary {
  background: linear-gradient(90deg, #4f8cff, #8a5cff);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.btn.small.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.back-link {
  color: #9aa3b5;
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  color: #6ea8ff;
}

.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 18px;
  align-items: start;
}

.sidebar {
  background: #171b2c;
  border: 1px solid #262c45;
  border-radius: 14px;
  padding: 16px;
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.volume {
  margin-bottom: 16px;
}

.volume h4 {
  color: #ffd479;
  font-size: 14px;
  margin-bottom: 8px;
}

.chapter-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: #aab3c8;
  padding: 8px 10px;
  margin-bottom: 6px;
  font-size: 13px;
  cursor: pointer;
}

.chapter-btn:hover {
  background: #202540;
}

.chapter-btn.active {
  background: rgba(110, 168, 255, 0.15);
  border-color: #6ea8ff;
  color: #6ea8ff;
}

.editor-panel {
  background: #171b2c;
  border: 1px solid #262c45;
  border-radius: 14px;
  padding: 20px;
}

.chapter-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.chapter-head h3 {
  color: #ffffff;
  font-size: 17px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  background: transparent;
  border: 1px solid #2b3150;
  border-radius: 999px;
  color: #9aa3b5;
  padding: 7px 18px;
  font-size: 14px;
  cursor: pointer;
}

.tab-btn:hover {
  color: #6ea8ff;
  border-color: #6ea8ff;
}

.tab-btn.active {
  background: rgba(110, 168, 255, 0.15);
  border-color: #6ea8ff;
  color: #6ea8ff;
}

.card-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.card-toolbar select {
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 8px;
  color: #e8eaf0;
  padding: 8px 10px;
  font-size: 13px;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-item {
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 10px;
  padding: 12px 14px;
}

.card-item summary {
  cursor: pointer;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  list-style: none;
}

.card-item summary::-webkit-details-marker {
  display: none;
}

.card-role {
  color: #6ea8ff;
  font-size: 12px;
  font-weight: 400;
  margin-left: 8px;
}

.card-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}

.card-fields label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #9aa3b5;
}

.card-fields input,
.card-fields textarea {
  background: #171b2c;
  border: 1px solid #2b3150;
  border-radius: 8px;
  color: #e8eaf0;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.6;
  outline: none;
  resize: vertical;
}

.card-fields input:focus,
.card-fields textarea:focus {
  border-color: #6ea8ff;
}

.card-fields .delete-btn {
  justify-self: start;
  align-self: end;
  margin-top: 4px;
}

.cards-empty {
  color: #9aa3b5;
  font-size: 13px;
  line-height: 1.8;
  padding: 24px 0;
}

.word-count {
  color: #9aa3b5;
  font-size: 13px;
}

.editor {
  width: 100%;
  min-height: 52vh;
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 10px;
  color: #e8eaf0;
  padding: 14px;
  font-size: 15px;
  line-height: 1.9;
  resize: vertical;
  outline: none;
}

.editor:focus {
  border-color: #6ea8ff;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.length-picker {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #9aa3b5;
  font-size: 13px;
}

.length-picker select {
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 8px;
  color: #e8eaf0;
  padding: 8px 10px;
  font-size: 13px;
}

.extra-row {
  margin-top: 12px;
}

.extra-row label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9aa3b5;
  font-size: 13px;
  flex-wrap: wrap;
}

.extra-row input {
  flex: 1;
  min-width: 220px;
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 8px;
  color: #e8eaf0;
  padding: 9px 12px;
  font-size: 13px;
  outline: none;
}

.extra-row input:focus {
  border-color: #6ea8ff;
}

.attach-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attach-label {
  font-size: 13px;
  color: #9aa3b5;
}

.attach-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.attach-btn {
  display: inline-flex;
  background: rgba(110, 168, 255, 0.1);
  border: 1px dashed #6ea8ff;
  border-radius: 8px;
  color: #6ea8ff;
  padding: 8px 14px;
  font-size: 13px;
  cursor: pointer;
}

.attach-btn:hover {
  background: rgba(110, 168, 255, 0.18);
}

.attach-btn input[type="file"] {
  display: none;
}

.attach-name {
  color: #cdd3e0;
  font-size: 13px;
}

.attach-remove {
  background: transparent;
  border: 1px solid rgba(255, 123, 123, 0.4);
  border-radius: 8px;
  color: #ff9b9b;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
}

.attach-remove:hover {
  background: rgba(255, 123, 123, 0.15);
}

.btn {
  background: #202540;
  border: 1px solid #2b3150;
  border-radius: 10px;
  color: #cdd3e0;
  padding: 10px 16px;
  font-size: 14px;
  cursor: pointer;
}

.btn:hover:not(:disabled) {
  border-color: #6ea8ff;
  color: #6ea8ff;
}

.btn.primary {
  background: linear-gradient(90deg, #4f8cff, #8a5cff);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin-top: 12px;
  color: #78839a;
  font-size: 12px;
  line-height: 1.6;
}

.message {
  margin-top: 10px;
  color: #7ddfa0;
  font-size: 13px;
}

.message.error {
  color: #ff7b7b;
}

.empty {
  background: #171b2c;
  border: 1px dashed #2b3150;
  border-radius: 14px;
  padding: 48px;
  text-align: center;
  color: #9aa3b5;
}

.empty a {
  color: #6ea8ff;
}

.open-btn {
  margin: 16px 0;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(8, 10, 20, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #171b2c;
  border: 1px solid #2b3150;
  border-radius: 14px;
  width: min(560px, 92vw);
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.modal-head h3 {
  color: #ffffff;
  font-size: 17px;
}

.project-list {
  overflow-y: auto;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #202540;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  cursor: pointer;
}

.project-item:hover {
  border: 1px solid #6ea8ff;
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.project-info strong {
  color: #ffffff;
  font-size: 15px;
}

.project-info span {
  color: #9aa3b5;
  font-size: 12px;
}

.delete-btn {
  background: transparent;
  border: 1px solid rgba(255, 123, 123, 0.4);
  border-radius: 8px;
  color: #ff9b9b;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
}

.delete-btn:hover {
  background: rgba(255, 123, 123, 0.15);
}

.modal-empty {
  color: #9aa3b5;
  text-align: center;
  padding: 32px 0;
}

@media (max-width: 760px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .toolbar {
    flex-wrap: wrap;
  }
  .card-fields {
    grid-template-columns: 1fr;
  }
}
</style>
