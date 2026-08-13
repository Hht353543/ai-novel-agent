<template>
  <aside class="sidebar">
    <div v-for="(vol, vi) in outline.volume_plan" :key="vi" class="volume">
      <h4 class="volume-title" @click="toggleVolume(vi)">
        <span class="volume-caret">{{ expandedVolumes[vi] ? "▾" : "▸" }}</span>
        {{ vol.volume }}
      </h4>
      <template v-if="expandedVolumes[vi]">
        <button
          v-for="(chapter, ci) in visibleChapters(vol.chapters, vi)"
          :key="ci"
          class="chapter-btn"
          :class="{ active: vi === volumeIndex && ci === chapterIndex }"
          @click="emit('select-chapter', vi, ci)"
        >
          {{ chapter }}
        </button>
        <button
          v-if="vol.chapters.length > MAX_VISIBLE_CHAPTERS && !showAllChapters[vi]"
          class="expand-btn"
          @click="showAllChapters[vi] = true"
        >
          展开剩余 {{ vol.chapters.length - MAX_VISIBLE_CHAPTERS }} 章
        </button>
      </template>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { reactive, watch } from "vue";
import type { NovelOutline } from "../api/novel";

const props = defineProps<{
  outline: NovelOutline;
  volumeIndex: number;
  chapterIndex: number;
}>();

const emit = defineEmits<{
  (e: "select-chapter", volumeIndex: number, chapterIndex: number): void;
}>();

// 超过该数量的卷只渲染前 N 章，其余懒展开
const MAX_VISIBLE_CHAPTERS = 50;

// 卷折叠状态：默认只展开当前卷，减少长书 DOM 数量
const expandedVolumes = reactive<Record<number, boolean>>({
  [props.volumeIndex]: true,
});
const showAllChapters = reactive<Record<number, boolean>>({});

watch(
  () => props.volumeIndex,
  (vi) => {
    expandedVolumes[vi] = true;
  },
);

function toggleVolume(vi: number): void {
  expandedVolumes[vi] = !expandedVolumes[vi];
}

function visibleChapters(chapters: string[], vi: number): string[] {
  return showAllChapters[vi] || chapters.length <= MAX_VISIBLE_CHAPTERS
    ? chapters
    : chapters.slice(0, MAX_VISIBLE_CHAPTERS);
}
</script>

<style scoped>
.sidebar {
  background: var(--panel);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 16px;
  max-height: calc(100vh - 170px);
  overflow-y: auto;
  box-shadow: var(--shadow);
}

.volume {
  margin-bottom: 16px;
}

.volume-title {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #a16207;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  cursor: pointer;
  user-select: none;
  transition: color 0.18s ease;
}

.volume-title:hover {
  color: #a16207;
}

.volume-caret {
  display: inline-block;
  width: 14px;
  color: var(--text-muted);
}

.expand-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px dashed var(--border-strong);
  border-radius: 9px;
  color: var(--accent);
  padding: 7px 10px;
  margin-bottom: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}

.expand-btn:hover {
  border-color: var(--accent);
  background: rgba(192, 86, 33, 0.08);
}

.chapter-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 9px;
  color: var(--text-secondary);
  padding: 8px 11px;
  margin-bottom: 5px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.chapter-btn:hover {
  background: rgba(93, 82, 60, 0.06);
  color: var(--text);
}

.chapter-btn.active {
  background: linear-gradient(135deg, rgba(192, 86, 33, 0.18), rgba(154, 63, 30, 0.1));
  border-color: rgba(192, 86, 33, 0.4);
  color: #c05621;
  box-shadow: inset 0 0 0 1px rgba(192, 86, 33, 0.12);
}
</style>

