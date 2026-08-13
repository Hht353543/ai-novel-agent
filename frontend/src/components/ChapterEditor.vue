<template>
  <div>
    <div class="chapter-head">
      <h3>{{ currentChapterTitle }}</h3>
      <span class="word-count">已写 {{ text.length }} 字</span>
    </div>

    <textarea
      class="editor"
      :value="text"
      placeholder="选择左侧章节，点击「生成本章开头」；也可以直接在这里手动写作。"
      @input="onTextInput"
      @click="onCursor"
      @keyup="onCursor"
      @select="onCursor"
    ></textarea>

    <div class="actions">
      <label class="length-picker">
        生成字数
        <select :value="targetLength" @change="onTargetLengthChange">
          <option :value="300">300</option>
          <option :value="600">600</option>
          <option :value="800" selected>800</option>
          <option :value="1200">1200</option>
          <option :value="2000">2000</option>
        </select>
      </label>
      <button class="btn" :disabled="loading" @click="emit('generate')">生成本章开头</button>
      <button class="btn" :disabled="loading" @click="emit('continue')">从文末续写</button>
      <button class="btn primary" :disabled="loading" @click="emit('rewrite')">
        {{ loading ? "生成中…" : "从光标处重写" }}
      </button>
      <button class="btn" :disabled="generatingTitle" @click="emit('generate-title-from-text')">
        {{ generatingTitle ? "生成中…" : "根据正文生成标题" }}
      </button>
      <button class="btn" :disabled="reviewing || !text.trim()" @click="emit('review')">
        {{ reviewing ? "审校中…" : "审校本章" }}
      </button>
    </div>

    <div class="extra-row">
      <label>
        其他要求（可选，生成时优先遵循）
        <input
          :value="extraReq"
          type="text"
          placeholder="如：风格参考古龙，节奏明快；本章结尾留钩子；主角不要说教……"
          @input="onExtraReqInput"
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
          <input type="file" accept=".txt,text/plain" @change="emit('attach-file', $event)" />
        </label>
        <template v-else>
          <span class="attach-name">{{ chapterAttachment.name }}</span>
          <button class="attach-remove" @click="emit('remove-attachment')">移除</button>
        </template>
      </div>
    </div>

    <div v-if="reviewIssues.length" class="review-list">
      <h4 class="review-title">审校结果（{{ reviewIssues.length }} 条）</h4>
      <div
        v-for="(issue, i) in reviewIssues"
        :key="i"
        class="review-item"
        :class="`sev-${issue.severity}`"
      >
        <strong>{{ issue.type || "问题" }}</strong>
        <span class="review-sev">{{ issue.severity }}</span>
        <p>{{ issue.description }}</p>
        <p v-if="issue.suggestion" class="review-suggestion">
          建议：{{ issue.suggestion }}
        </p>
      </div>
    </div>

    <p class="hint">
      编辑正文后，把光标放在修改处，点击「从光标处重写」：光标前的内容会作为上文，
      重新生成光标之后的部分并替换。生成正文时会按本卷角色卡约束角色言行。
    </p>
  </div>
</template>

<script setup lang="ts">
import type { Attachment } from "../composables/useAttachment";
import type { ReviewIssue } from "../api/novel";

defineProps<{
  currentChapterTitle: string;
  text: string;
  targetLength: number;
  extraReq: string;
  chapterAttachment: Attachment | null;
  loading: boolean;
  generatingTitle: boolean;
  reviewing: boolean;
  reviewIssues: ReviewIssue[];
}>();

const emit = defineEmits<{
  (e: "update:text", value: string): void;
  (e: "update:target-length", value: number): void;
  (e: "update:extra-req", value: string): void;
  (e: "record-cursor", position: number): void;
  (e: "generate"): void;
  (e: "continue"): void;
  (e: "rewrite"): void;
  (e: "generate-title-from-text"): void;
  (e: "attach-file", event: Event): void;
  (e: "remove-attachment"): void;
  (e: "review"): void;
}>();

function onTextInput(event: Event): void {
  emit("update:text", (event.target as HTMLTextAreaElement).value);
}

function onCursor(event: Event): void {
  emit("record-cursor", (event.target as HTMLTextAreaElement).selectionStart ?? 0);
}

function onTargetLengthChange(event: Event): void {
  emit("update:target-length", Number((event.target as HTMLSelectElement).value));
}

function onExtraReqInput(event: Event): void {
  emit("update:extra-req", (event.target as HTMLInputElement).value);
}
</script>

<style scoped>
.chapter-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.chapter-head h3 {
  color: #3d3931;
  font-size: 17px;
  font-weight: 650;
}

.word-count {
  color: var(--text-muted);
  font-size: 12.5px;
  font-variant-numeric: tabular-nums;
}

.editor {
  width: 100%;
  min-height: 54vh;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 14px;
  color: var(--text);
  padding: 16px;
  font-size: 15px;
  line-height: 2;
  resize: vertical;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.editor:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(192, 86, 33, 0.14);
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.length-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
}

.length-picker select {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 9px;
  color: var(--text);
  padding: 9px 11px;
  font-size: 13px;
  outline: none;
}

.extra-row {
  margin-top: 14px;
}

.extra-row label {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  flex-wrap: wrap;
}

.extra-row input {
  flex: 1;
  min-width: 220px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text);
  padding: 10px 13px;
  font-size: 13.5px;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.extra-row input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(192, 86, 33, 0.14);
}

.attach-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.attach-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.attach-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.attach-btn {
  display: inline-flex;
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

.btn {
  background: rgba(93, 82, 60, 0.06);
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  color: var(--text);
  padding: 10px 16px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease,
    transform 0.18s ease, box-shadow 0.18s ease;
}

.btn:hover:not(:disabled) {
  background: rgba(192, 86, 33, 0.12);
  border-color: rgba(192, 86, 33, 0.35);
  transform: translateY(-1px);
}

.btn.primary {
  background: linear-gradient(135deg, #c05621, #9a3f1e);
  border: none;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(192, 86, 33, 0.18);
}

.btn.primary:hover:not(:disabled) {
  filter: brightness(1.06);
  box-shadow: 0 8px 22px rgba(192, 86, 33, 0.22);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.hint {
  margin-top: 14px;
  color: var(--text-muted);
  font-size: 12.5px;
  line-height: 1.7;
}

.review-list {
  margin-top: 16px;
  border-top: 1px solid var(--border);
  padding-top: 14px;
}

.review-title {
  color: var(--warning);
  font-size: 13.5px;
  font-weight: 600;
  margin-bottom: 10px;
}

.review-item {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-left: 3px solid var(--text-muted);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 10px;
}

.review-item.sev-high {
  border-left-color: var(--danger);
}

.review-item.sev-medium {
  border-left-color: var(--warning);
}

.review-item.sev-low {
  border-left-color: var(--accent);
}

.review-item strong {
  color: #3d3931;
  font-size: 13px;
  margin-right: 8px;
}

.review-sev {
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
}

.review-item p {
  color: var(--text-secondary);
  font-size: 12.5px;
  line-height: 1.7;
  margin-top: 5px;
}

.review-suggestion {
  color: var(--success) !important;
}
</style>

