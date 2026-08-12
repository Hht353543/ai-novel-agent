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
  margin-bottom: 12px;
}

.chapter-head h3 {
  color: #ffffff;
  font-size: 17px;
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

.review-list {
  margin-top: 14px;
  border-top: 1px solid #2b3150;
  padding-top: 12px;
}

.review-title {
  color: #ffd479;
  font-size: 13px;
  margin-bottom: 8px;
}

.review-item {
  background: #0f1220;
  border: 1px solid #2b3150;
  border-left: 3px solid #78839a;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
}

.review-item.sev-high {
  border-left-color: #ff7b7b;
}

.review-item.sev-medium {
  border-left-color: #ffd479;
}

.review-item.sev-low {
  border-left-color: #6ea8ff;
}

.review-item strong {
  color: #ffffff;
  font-size: 13px;
  margin-right: 8px;
}

.review-sev {
  color: #9aa3b5;
  font-size: 11px;
  text-transform: uppercase;
}

.review-item p {
  color: #aab3c8;
  font-size: 12px;
  line-height: 1.6;
  margin-top: 4px;
}

.review-suggestion {
  color: #7ddfa0;
}
</style>
