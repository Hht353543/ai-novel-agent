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

.volume-title {
  color: #ffd479;
  font-size: 14px;
  margin-bottom: 8px;
  cursor: pointer;
  user-select: none;
}

.volume-caret {
  display: inline-block;
  width: 14px;
  color: #9aa3b5;
}

.expand-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px dashed #2b3150;
  border-radius: 8px;
  color: #6ea8ff;
  padding: 6px 10px;
  margin-bottom: 6px;
  font-size: 12px;
  cursor: pointer;
}

.expand-btn:hover {
  border-color: #6ea8ff;
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
</style>
