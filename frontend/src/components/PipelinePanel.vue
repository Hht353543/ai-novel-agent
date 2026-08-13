<template>
  <div v-if="runId || error" class="pipeline-panel">
    <div class="pipeline-head">
      <h3>小说创作 Pipeline</h3>
      <span class="pipeline-status" :class="statusClass">
        {{ statusLabel }}
      </span>
    </div>

    <div class="pipeline-steps">
      <div
        v-for="step in stepOrder"
        :key="step"
        class="pipeline-step"
        :class="stepState(step)"
      >
        <span class="step-icon">{{ stepIcon(step) }}</span>
        <span class="step-label">{{ stepLabel(step) }}</span>
      </div>
    </div>

    <p v-if="stateMessage" class="pipeline-message">{{ stateMessage }}</p>
    <p v-if="state?.revision_attempts" class="pipeline-revision">
      修订次数：{{ state.revision_attempts }}
    </p>
    <p v-if="error" class="pipeline-error">{{ error }}</p>

    <div v-if="completed && finalContent" class="pipeline-result">
      <p><strong>最终章节预览：</strong>{{ finalContent.slice(0, 160) }}…</p>
      <p v-if="finalReview" class="pipeline-review">
        Reviewer：{{ finalReview.passed ? "通过" : "未通过" }}（评分
        {{ finalReview.score }}）
      </p>
      <div class="pipeline-actions">
        <button class="btn primary" @click="emit('enter-writer')">
          进入章节写作
        </button>
        <button class="btn" @click="emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import {
  getPipelineRun,
  startPipelineAsync,
  startSequenceAsync,
  type PipelinePayload,
  type PipelineResultPayload,
  type PipelineRunState,
  type ReviewResultPayload,
  type SequenceResultPayload,
} from "../api/agents";

const props = defineProps<{
  payload: PipelinePayload;
  chapterCount: number;
}>();

const emit = defineEmits<{
  (e: "completed", result: {
    outline: unknown;
    projectId: string;
    content: string;
    status: string;
    review: ReviewResultPayload | null;
  }): void;
  (e: "enter-writer"): void;
  (e: "close"): void;
}>();

const runId = ref("");
const state = ref<PipelineRunState | null>(null);
const error = ref("");
const completed = ref(false);
const finalContent = ref("");
const finalReview = ref<ReviewResultPayload | null>(null);
const terminal = ref(false);
let timer: ReturnType<typeof setTimeout> | undefined;
let started = false;

const STEP_ORDER = [
  "PLANNING",
  "CHARACTER_DESIGN",
  "WRITING",
  "REVIEWING",
  "REVISING",
  "UPDATING_MEMORY",
  "COMPLETED",
];

const STEP_LABELS: Record<string, string> = {
  PLANNING: "大纲规划",
  CHARACTER_DESIGN: "人物设计",
  WRITING: "章节写作",
  REVIEWING: "质量审校",
  REVISING: "修订",
  UPDATING_MEMORY: "记忆更新",
  COMPLETED: "完成",
};

const stepOrder = computed(() => {
  const seen = new Set<string>();
  const order: string[] = [];
  for (const entry of state.value?.progress ?? []) {
    if (!seen.has(entry.step)) {
      seen.add(entry.step);
      order.push(entry.step);
    }
  }
  for (const step of STEP_ORDER) {
    if (!seen.has(step)) order.push(step);
  }
  return order;
});

const statusLabel = computed(() => {
  if (!state.value) return "等待启动";
  const map: Record<string, string> = {
    CREATED: "等待启动",
    PLANNING: "大纲规划中",
    CHARACTER_DESIGN: "人物设计中",
    WRITING: "写作中",
    REVIEWING: "审校中",
    REVISING: "修订中",
    UPDATING_MEMORY: "记忆更新中",
    COMPLETED: "已完成",
    FAILED: "失败",
  };
  return map[state.value.status] ?? state.value.status;
});

const statusClass = computed(() => {
  if (!state.value) return "";
  if (state.value.status === "FAILED") return "status-error";
  if (state.value.status === "COMPLETED") return "status-ok";
  return "status-running";
});

const stateMessage = computed(() => {
  if (error.value) return "";
  return state.value?.message || state.value?.status || "";
});

function stepIcon(step: string): string {
  const s = stepState(step);
  if (s === "done") return "✓";
  if (s === "running") return "●";
  return "○";
}

function stepState(step: string): string {
  if (!state.value) return "pending";
  if (step === "COMPLETED") {
    return state.value.status === "COMPLETED" ? "done" : "pending";
  }
  const entries = state.value.progress.filter((e) => e.step === step);
  if (entries.some((e) => e.status === "error")) return "error";
  if (entries.some((e) => e.status === "running")) return "running";
  if (entries.some((e) => e.status === "done")) return "done";
  if (state.value.status === "FAILED") return "pending";
  const order = STEP_ORDER.indexOf(step);
  const currentIndex = state.value.progress.length
    ? STEP_ORDER.indexOf(state.value.progress[state.value.progress.length - 1].step)
    : -1;
  return order < currentIndex ? "done" : "pending";
}

function stepLabel(step: string): string {
  return STEP_LABELS[step] ?? step;
}

async function start(): Promise<void> {
  if (started || terminal.value) return;
  started = true;
  runId.value = "";
  state.value = null;
  error.value = "";
  completed.value = false;
  try {
    const resp =
      props.chapterCount > 1
        ? await startSequenceAsync({
            ...props.payload,
            save: true,
            start_chapter: 0,
            end_chapter: props.chapterCount - 1,
          })
        : await startPipelineAsync({
            ...props.payload,
            save: true,
            volume_index: 0,
            chapter_index: 0,
          });
    runId.value = resp.run_id;
    void poll();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "启动 Pipeline 失败";
    started = false;
  }
}

async function poll(): Promise<void> {
  if (!runId.value || terminal.value) return;
  try {
    state.value = await getPipelineRun(runId.value);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "获取进度失败";
    terminal.value = true;
    return;
  }
  if (state.value.status === "COMPLETED") {
    terminal.value = true;
    completed.value = true;
    const result = state.value.result as
      | PipelineResultPayload
      | SequenceResultPayload
      | null;
    if (result) {
      const chapter =
        "chapter" in result ? result.chapter : null;
      const chapters =
        "chapters" in result ? result.chapters : [];
      finalContent.value =
        chapter?.content ??
        chapters[chapters.length - 1]?.chapter?.content ??
        "";
      const pipelineReview =
        "latest_review" in result ? result.latest_review : null;
      finalReview.value =
        pipelineReview ??
        chapters[chapters.length - 1]?.latest_review ??
        null;
      emit("completed", {
        outline: result.outline,
        projectId: result.project_id,
        content: finalContent.value,
        status: result.status,
        review: finalReview.value,
      });
    }
    return;
  }
  if (state.value.status === "FAILED") {
    terminal.value = true;
    error.value =
      state.value.error?.message || state.value.message || "Pipeline 失败";
    return;
  }
  timer = setTimeout(() => void poll(), 1500);
}

defineExpose({ start });

onBeforeUnmount(() => {
  terminal.value = true;
  if (timer !== undefined) clearTimeout(timer);
});
</script>

<style scoped>
.pipeline-panel {
  margin-top: 18px;
  background: #171b2c;
  border: 1px solid #262c45;
  border-radius: 14px;
  padding: 18px 20px;
}

.pipeline-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.pipeline-head h3 {
  color: #ffffff;
  font-size: 16px;
}

.pipeline-status {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
}

.status-running {
  background: rgba(110, 168, 255, 0.15);
  color: #6ea8ff;
}

.status-ok {
  background: rgba(125, 223, 160, 0.15);
  color: #7ddfa0;
}

.status-error {
  background: rgba(255, 123, 123, 0.15);
  color: #ff7b7b;
}

.pipeline-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.pipeline-step {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #0f1220;
  border: 1px solid #2b3150;
  border-radius: 999px;
  color: #78839a;
  padding: 5px 12px;
  font-size: 12px;
}

.pipeline-step.done {
  color: #7ddfa0;
  border-color: rgba(125, 223, 160, 0.4);
}

.pipeline-step.running {
  color: #6ea8ff;
  border-color: #6ea8ff;
}

.pipeline-step.error {
  color: #ff7b7b;
  border-color: rgba(255, 123, 123, 0.4);
}

.step-icon {
  width: 14px;
  text-align: center;
}

.pipeline-message {
  color: #aab3c8;
  font-size: 13px;
}

.pipeline-revision {
  color: #ffd479;
  font-size: 12px;
  margin-top: 6px;
}

.pipeline-error {
  color: #ff7b7b;
  font-size: 13px;
  margin-top: 8px;
}

.pipeline-result {
  margin-top: 12px;
  border-top: 1px solid #262c45;
  padding-top: 12px;
  color: #aab3c8;
  font-size: 13px;
  line-height: 1.7;
}

.pipeline-review {
  color: #ffd479;
  font-size: 12px;
  margin-top: 4px;
}

.pipeline-actions {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.btn {
  background: #202540;
  border: 1px solid #2b3150;
  border-radius: 10px;
  color: #cdd3e0;
  padding: 9px 16px;
  font-size: 13px;
  cursor: pointer;
}

.btn.primary {
  background: linear-gradient(90deg, #4f8cff, #8a5cff);
  border: none;
  color: #ffffff;
  font-weight: 600;
}
</style>
