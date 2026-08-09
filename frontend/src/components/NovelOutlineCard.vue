<template>
  <div class="outline-card">
    <div class="outline-header">
      <h2>{{ outline.title || "未命名小说" }}</h2>
      <span class="badge">大纲</span>
    </div>

    <section class="block">
      <h3>全书梗概</h3>
      <p>{{ outline.summary || "（无）" }}</p>
    </section>

    <section class="block">
      <h3>世界观</h3>
      <p class="preserve-line">{{ outline.world || "（无）" }}</p>
    </section>

    <section class="block">
      <h3>主要角色</h3>
      <div v-if="outline.characters.length" class="character-list">
        <div
          v-for="(item, index) in outline.characters"
          :key="index"
          class="character-item"
        >
          <strong>{{ item.name }}</strong>
          <span class="role">{{ item.role }}</span>
          <p>{{ item.description }}</p>
        </div>
      </div>
      <p v-else>（无）</p>
    </section>

    <section class="block">
      <h3>分卷计划</h3>
      <div v-if="outline.volume_plan.length" class="volume-list">
        <div
          v-for="(vol, index) in outline.volume_plan"
          :key="index"
          class="volume-item"
        >
          <div class="volume-head">
            <h4>{{ vol.volume }}</h4>
            <button
              class="title-btn"
              :disabled="generatingVolumeIndex === index"
              @click="emit('generate-titles', index)"
            >
              {{ generatingVolumeIndex === index ? "生成中…" : "生成前10章标题" }}
            </button>
          </div>
          <ul>
            <li v-for="(chapter, ci) in vol.chapters.slice(0, 20)" :key="ci">{{ chapter }}</li>
            <li v-if="vol.chapters.length > 20" class="more">
              … 共 {{ vol.chapters.length }} 章（其余请在章节写作页查看）
            </li>
          </ul>
        </div>
      </div>
      <p v-else>（无）</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { NovelOutline } from "../api/novel";

defineProps<{
  outline: NovelOutline;
  /** 正在生成标题的卷索引；null/undefined 表示没有进行中的生成 */
  generatingVolumeIndex?: number | null;
}>();

const emit = defineEmits<{
  (e: "generate-titles", volumeIndex: number): void;
}>();
</script>

<style scoped>
.outline-card {
  background: #171b2c;
  border: 1px solid #262c45;
  border-radius: 14px;
  padding: 24px;
}

.outline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}

.outline-header h2 {
  font-size: 22px;
  color: #6ea8ff;
}

.badge {
  background: rgba(110, 168, 255, 0.15);
  color: #6ea8ff;
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
}

.block {
  margin-bottom: 20px;
}

.block h3 {
  font-size: 15px;
  color: #b388ff;
  margin-bottom: 8px;
  border-left: 3px solid #b388ff;
  padding-left: 10px;
}

.block p {
  color: #cdd3e0;
  line-height: 1.7;
  font-size: 14px;
}

.preserve-line {
  white-space: pre-line;
}

.character-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.character-item {
  background: #202540;
  border-radius: 10px;
  padding: 12px;
}

.character-item strong {
  color: #ffffff;
  margin-right: 8px;
}

.character-item .role {
  color: #6ea8ff;
  font-size: 12px;
}

.character-item p {
  margin-top: 6px;
  font-size: 13px;
  color: #aab3c8;
}

.volume-item {
  background: #202540;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
}

.volume-item h4 {
  color: #ffd479;
  font-size: 15px;
  margin-bottom: 8px;
}

.volume-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.volume-head h4 {
  margin-bottom: 0;
}

.title-btn {
  background: rgba(110, 168, 255, 0.1);
  border: 1px solid #6ea8ff;
  border-radius: 999px;
  color: #6ea8ff;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;
  flex-shrink: 0;
}

.title-btn:hover:not(:disabled) {
  background: rgba(110, 168, 255, 0.2);
}

.title-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.volume-item ul {
  list-style: none;
  padding-left: 4px;
}

.volume-item li {
  font-size: 13px;
  color: #aab3c8;
  line-height: 1.9;
}

.volume-item li.more {
  color: #78839a;
  font-size: 12px;
  margin-top: 4px;
}
</style>
