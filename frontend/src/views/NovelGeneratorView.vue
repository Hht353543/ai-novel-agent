<template>
  <div class="generator">
    <section class="panel form-panel">
      <h2>小说创意</h2>
      <div class="form-grid">
        <label>
          小说标题（可选）
          <input v-model.trim="form.title" type="text" placeholder="如：《从天而降的我成为武神》" />
        </label>
        <label>
          小说类型
          <select v-model="form.genre">
            <option value="玄幻">玄幻</option>
            <option value="仙侠">仙侠</option>
            <option value="武侠">武侠</option>
            <option value="都市">都市</option>
            <option value="科幻">科幻</option>
            <option value="历史">历史</option>
          </select>
        </label>
        <label>
          核心主题
          <input v-model.trim="form.theme" type="text" placeholder="如：无敌流" />
        </label>
        <label>
          关键词（逗号分隔）
          <input v-model.trim="form.keywords" type="text" placeholder="如：系统流,极道流" />
        </label>
        <label class="full-width">
          字数规模 / 要求
          <input v-model.trim="form.requirement" type="text" placeholder="如：100万字" />
        </label>
        <label class="full-width">
          其他要求（自由输入，可留空）
          <textarea
            v-model.trim="form.extra_requirements"
            rows="4"
            placeholder="如：风格参考古龙，节奏明快；不要圣母主角；开篇 3 章内要有打脸；第 20 章前完成第一个剧情小高潮……"
          ></textarea>
        </label>
        <div class="full-width attach-row">
          <span class="attach-label">本地 txt 附件（可选，内容视为最高优先级素材/要求）</span>
          <div class="attach-controls">
            <label v-if="!attachment" class="attach-btn">
              选择 txt 文件
              <input
                type="file"
                accept=".txt,text/plain"
                @change="onAttachFile"
              />
            </label>
            <template v-else>
              <span class="attach-name">{{ attachment.name }}</span>
              <button class="attach-remove" @click="removeAttachment">移除</button>
            </template>
          </div>
        </div>
      </div>
      <button class="generate-btn" :disabled="loading" @click="onGenerate">
        {{ loading ? "生成中…" : "生成大纲" }}
      </button>
      <div class="pipeline-row">
        <label class="pipeline-count">
          连续章数
          <select v-model.number="chapterCount">
            <option :value="1">1</option>
            <option :value="2">2</option>
            <option :value="3">3</option>
          </select>
        </label>
        <button
          class="pipeline-btn"
          :disabled="loading || showPipeline"
          @click="startPipeline"
        >
          {{ showPipeline ? "Pipeline 运行中…" : "一键 Pipeline（多 Agent）" }}
        </button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </section>

    <LoadingState v-if="loading" />

    <PipelinePanel
      v-if="showPipeline"
      ref="pipelinePanel"
      :payload="pipelinePayload"
      :chapter-count="chapterCount"
      @completed="onPipelineCompleted"
      @enter-writer="enterPipelineWriter"
      @close="showPipeline = false"
    />

    <section v-else-if="result" class="panel result-panel">
      <div v-if="result.status !== 'success'" class="notice" :class="result.status">
        {{ result.message }}
      </div>
      <NovelOutlineCard
        :outline="result.outline"
        :generating-volume-index="titlesGenerating"
        @generate-titles="onGenerateVolumeTitles"
      />
      <button class="write-btn" @click="goWriter">
        进入章节写作（可编辑 / 续写 / 重写）
      </button>
      <button class="write-btn save-btn" :disabled="savingOutline || !canSaveOutline" @click="saveOutlineProject">
        {{ savingOutline ? "保存中…" : "保存大纲为项目" }}
      </button>

      <details v-if="result.context.length" class="context-panel">
        <summary>查看知识库检索结果（{{ result.context.length }} 条）</summary>
        <div v-for="(item, index) in result.context" :key="index" class="context-item">
          <span v-if="item.category" class="context-category">{{ item.category }}</span>
          <strong>{{ item.source }}</strong>
          <p>{{ item.content }}</p>
        </div>
      </details>
    </section>

    <section v-else class="panel empty-panel">
      <p>填写左侧创意需求，点击「生成大纲」。AI 会先从本地知识库检索世界观、人物与剧情模板，再调用 DeepSeek 生成结构化大纲。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import LoadingState from "../components/LoadingState.vue";
import NovelOutlineCard from "../components/NovelOutlineCard.vue";
import PipelinePanel from "../components/PipelinePanel.vue";
import {
  generateTitles,
  generateNovel,
  type NovelGenerateResponse,
} from "../api/novel";
import { saveProject } from "../api/project";
import { useAttachment } from "../composables/useAttachment";
import type { PipelinePayload, ReviewResultPayload } from "../api/agents";
import {
  FORM_ATTACH_KEY,
  FORM_KEY,
  generateProjectKey,
  LAST_PROJECT_KEY,
  OUTLINE_KEY,
  OUTLINE_PROJECT_KEY,
  safeRemoveItem,
  safeSetItem,
} from "../utils/storage";

const router = useRouter();
const loading = ref(false);
const savingOutline = ref(false);
const titlesGenerating = ref<number | null>(null);
const showPipeline = ref(false);
const chapterCount = ref(1);
const pipelinePanel = ref<InstanceType<typeof PipelinePanel> | null>(null);
const pipelineResult = ref<{
  outline: unknown;
  projectId: string;
  content: string;
  status: string;
  review: ReviewResultPayload | null;
} | null>(null);
const error = ref("");
const result = ref<NovelGenerateResponse | null>(null);
const pipelinePayload = computed<PipelinePayload>(() => ({
  title: form.title,
  genre: form.genre,
  theme: form.theme,
  keywords: form.keywords,
  requirement: form.requirement,
  extra_requirements: form.extra_requirements,
  attachment_name: attachment.value?.name ?? "",
  attachment_text: attachment.value?.content ?? "",
  target_length: 800,
  with_review: true,
}));
// 只有成功或演示模式的结果允许保存为项目；错误结果不落库，避免伪成功数据入库
const canSaveOutline = computed(
  () =>
    !!result.value &&
    (result.value.status === "success" || result.value.status === "demo"),
);
// 表单默认值（与后端 schema 保持一致）
const DEFAULT_FORM = {
  title: "",
  genre: "武侠",
  theme: "无敌流",
  keywords: "系统流,极道流",
  requirement: "100万字",
  extra_requirements: "",
};

// 表单实时保存到 localStorage：任何输入刷新后都不会丢
const form = reactive({ ...DEFAULT_FORM });

// 用户上传的本地 txt 附件（复用公共逻辑）
const {
  attachment,
  restore: restoreAttachment,
  onAttachFile,
  removeAttachment,
} = useAttachment(() => FORM_ATTACH_KEY, (msg) => {
  error.value = msg;
});

watch(
  form,
  () => {
    safeSetItem(FORM_KEY, JSON.stringify(form));
  },
  { deep: true },
);

onMounted(() => {
  try {
    const raw = localStorage.getItem(FORM_KEY);
    if (raw) {
      const saved = JSON.parse(raw) as Partial<typeof DEFAULT_FORM>;
      Object.assign(form, DEFAULT_FORM, saved);
    }
  } catch {
    // 本地数据损坏时静默忽略，使用默认值
  }
  // 恢复附件
  restoreAttachment();
});

async function onGenerate(): Promise<void> {
  if (!form.genre.trim()) {
    error.value = "请至少填写小说类型";
    return;
  }

  loading.value = true;
  error.value = "";
  result.value = null;
  try {
    result.value = await generateNovel({
      ...form,
      attachment_name: attachment.value?.name ?? "",
      attachment_text: attachment.value?.content ?? "",
    });
    // 生成成功即自动备份大纲到本地，刷新页面也不会丢
    if (result.value) {
      safeSetItem(OUTLINE_KEY, JSON.stringify(result.value.outline));
      // 每次成功生成都赋予新的本地项目标识，草稿按标识隔离，避免与旧大纲串数据
      safeSetItem(OUTLINE_PROJECT_KEY, generateProjectKey());
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "生成失败，请检查后端服务";
  } finally {
    loading.value = false;
  }
}

/** 启动多 Agent Pipeline（单章或连续多章） */
async function startPipeline(): Promise<void> {
  if (!form.genre.trim()) {
    error.value = "请至少填写小说类型";
    return;
  }
  error.value = "";
  pipelineResult.value = null;
  showPipeline.value = true;
  await nextTick();
  void pipelinePanel.value?.start();
}

/** Pipeline 完成：保存大纲与项目标识，供写作页调出 */
function onPipelineCompleted(payload: {
  outline: unknown;
  projectId: string;
  content: string;
  status: string;
  review: ReviewResultPayload | null;
}): void {
  pipelineResult.value = payload;
  if (payload.outline) {
    safeSetItem(OUTLINE_KEY, JSON.stringify(payload.outline));
  }
  if (payload.projectId) {
    safeSetItem(LAST_PROJECT_KEY, payload.projectId);
  }
}

/** 进入章节写作（Pipeline 已保存项目，写作页会直接调出） */
function enterPipelineWriter(): void {
  if (!pipelineResult.value) return;
  if (pipelineResult.value.outline) {
    safeSetItem(OUTLINE_KEY, JSON.stringify(pipelineResult.value.outline));
  }
  if (pipelineResult.value.projectId) {
    safeSetItem(LAST_PROJECT_KEY, pipelineResult.value.projectId);
  }
  void router.push({ path: "/writer" });
}

/** 保存大纲并进入章节写作页 */
function goWriter(): void {
  if (!result.value) return;
  safeSetItem(OUTLINE_KEY, JSON.stringify(result.value.outline));
  // 新大纲尚未保存为项目：移除旧项目记忆，避免章节页自动恢复旧项目
  safeRemoveItem(LAST_PROJECT_KEY);
  void router.push({ path: "/writer" });
}

/** 把大纲保存为后端项目（章节留空），下次打开可直接调出 */
async function saveOutlineProject(): Promise<void> {
  if (!result.value || !canSaveOutline.value) return;
  savingOutline.value = true;
  try {
    const saved = await saveProject({
      title: result.value.outline.title,
      outline: result.value.outline,
      chapters: [],
      character_cards: [],
      memory: "",
    });
    safeSetItem(LAST_PROJECT_KEY, saved.id);
    error.value = "";
    alert(`大纲已保存为项目：《${saved.title}》（可在「章节写作」页打开）`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "保存大纲失败";
  } finally {
    savingOutline.value = false;
  }
}

/** 生成本卷前 10 章标题（分批生成，不一次性生成全部） */
async function onGenerateVolumeTitles(volumeIndex: number): Promise<void> {
  if (!result.value) return;
  const vol = result.value.outline.volume_plan[volumeIndex];
  if (!vol) return;

  titlesGenerating.value = volumeIndex;
  error.value = "";
  try {
    const resp = await generateTitles({
      outline: result.value.outline,
      volume_index: volumeIndex,
      volume_label: vol.volume,
      mode: "volume",
      chapter_index: 0,
      chapter_text: "",
      existing_titles: vol.chapters.slice(0, 10),
    });
    if (!resp.success) {
      error.value = resp.message || "标题生成失败";
      return;
    }
    // 计算本卷起始章号（全书连续编号）
    let start = 1;
    for (let i = 0; i < volumeIndex; i++) {
      start += result.value.outline.volume_plan[i].chapters.length;
    }
    const count = Math.min(10, vol.chapters.length, resp.titles.length);
    for (let i = 0; i < count; i++) {
      vol.chapters[i] = `第${start + i}章 ${resp.titles[i].trim()}`;
    }
    // 同步本地备份，避免刷新丢失
    safeSetItem(
      OUTLINE_KEY,
      JSON.stringify(result.value.outline),
    );
    error.value = "";
    alert(
      resp.status === "demo"
        ? resp.message
        : `已生成第 ${volumeIndex + 1} 卷前 ${count} 章标题。若已保存过项目，请重新点「保存大纲为项目」同步。`,
    );
  } catch (err) {
    error.value = err instanceof Error ? err.message : "标题生成失败";
  } finally {
    titlesGenerating.value = null;
  }
}
</script>

<style scoped>
.generator {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  background: var(--panel);
  backdrop-filter: blur(16px) saturate(1.25);
  -webkit-backdrop-filter: blur(16px) saturate(1.25);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 26px;
  box-shadow: var(--shadow);
}

.form-panel h2 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 650;
  margin-bottom: 20px;
  color: #3d3931;
}

.form-panel h2::before {
  content: "";
  width: 4px;
  height: 18px;
  border-radius: 999px;
  background: linear-gradient(180deg, #d97742, #b4532a);
  box-shadow: 0 0 12px rgba(192, 86, 33, 0.35);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.full-width {
  grid-column: 1 / -1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 7px;
  font-size: 12.5px;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: var(--text-secondary);
}

input,
select,
textarea {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  color: var(--text);
  padding: 11px 13px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease,
    background 0.18s ease;
}

input::placeholder,
textarea::placeholder {
  color: var(--text-muted);
}

input:hover,
select:hover,
textarea:hover {
  border-color: rgba(148, 163, 214, 0.4);
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--accent);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 0 0 3px rgba(192, 86, 33, 0.14);
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.generate-btn {
  margin-top: 20px;
  width: 100%;
  padding: 13px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #c05621, #9a3f1e);
  color: #ffffff;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(192, 86, 33, 0.18);
  transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  filter: brightness(1.06);
  box-shadow: 0 12px 30px rgba(192, 86, 33, 0.22);
}

.generate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.pipeline-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.pipeline-count {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.pipeline-count select {
  padding: 9px 12px;
}

.pipeline-btn {
  flex: 1;
  padding: 12px;
  border: 1px solid rgba(154, 63, 30, 0.35);
  border-radius: 12px;
  background: rgba(154, 63, 30, 0.08);
  color: #8a3a1e;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease,
    transform 0.18s ease, box-shadow 0.18s ease;
}

.pipeline-btn:hover:not(:disabled) {
  background: rgba(154, 63, 30, 0.16);
  border-color: rgba(154, 63, 30, 0.5);
  transform: translateY(-1px);
  box-shadow: 0 8px 22px rgba(154, 63, 30, 0.18);
}

.pipeline-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  margin-top: 12px;
  color: var(--danger);
  font-size: 13px;
}

.write-btn {
  margin-top: 16px;
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(192, 86, 33, 0.3);
  border-radius: 12px;
  background: rgba(192, 86, 33, 0.1);
  color: #c05621;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.write-btn:hover {
  background: rgba(192, 86, 33, 0.16);
  box-shadow: 0 6px 20px rgba(192, 86, 33, 0.18);
}

.save-btn {
  border-color: rgba(22, 163, 74, 0.3);
  color: #15803d;
  background: rgba(22, 163, 74, 0.08);
}

.save-btn:hover:not(:disabled) {
  background: rgba(22, 163, 74, 0.12);
  box-shadow: 0 6px 20px rgba(22, 163, 74, 0.14);
}

.save-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.notice {
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;
}

.notice.demo {
  background: rgba(180, 83, 9, 0.08);
  border: 1px solid rgba(180, 83, 9, 0.3);
  color: #a16207;
}

.notice.error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.3);
  color: #b91c1c;
}

.empty-panel {
  text-align: center;
  color: var(--text-secondary);
}

.empty-panel p {
  max-width: 560px;
  margin: 0 auto;
  line-height: 1.9;
  font-size: 14px;
}

.context-panel {
  margin-top: 18px;
  border-top: 1px solid var(--border);
  padding-top: 16px;
}

.context-panel summary {
  color: var(--accent);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 500;
}

.context-item {
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
}

.context-item strong {
  color: var(--warning);
  font-size: 12px;
}

.context-category {
  display: inline-block;
  background: rgba(192, 86, 33, 0.14);
  color: var(--accent);
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 11px;
  margin-right: 8px;
}

.context-item p {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
  margin-top: 5px;
}

.attach-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attach-label {
  font-size: 12.5px;
  color: var(--text-secondary);
  font-weight: 500;
}

.attach-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.attach-btn {
  display: inline-flex;
  align-items: center;
  background: rgba(192, 86, 33, 0.08);
  border: 1px dashed rgba(192, 86, 33, 0.35);
  border-radius: 10px;
  color: var(--accent);
  padding: 9px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.18s ease;
}

.attach-btn:hover {
  background: rgba(192, 86, 33, 0.14);
}

.attach-btn input[type="file"] {
  display: none;
}

.attach-name {
  color: var(--text);
  font-size: 13px;
}

.attach-remove {
  background: transparent;
  border: 1px solid rgba(220, 38, 38, 0.35);
  border-radius: 9px;
  color: var(--danger);
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.18s ease;
}

.attach-remove:hover {
  background: rgba(220, 38, 38, 0.1);
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .pipeline-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>

