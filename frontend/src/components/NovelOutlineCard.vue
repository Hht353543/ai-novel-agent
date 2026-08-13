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
  background: transparent;
  border: none;
  padding: 0;
}

.outline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.outline-header h2 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.01em;
  background: linear-gradient(90deg, #b4532a, #8a3a1e);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.badge {
  background: linear-gradient(135deg, rgba(192, 86, 33, 0.18), rgba(154, 63, 30, 0.16));
  border: 1px solid rgba(192, 86, 33, 0.2);
  color: #c05621;
  border-radius: 999px;
  padding: 3px 11px;
  font-size: 12px;
  font-weight: 600;
}

.block {
  margin-bottom: 22px;
}

.block h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 650;
  color: #9a3f1e;
  margin-bottom: 10px;
}

.block h3::before {
  content: "";
  width: 3px;
  height: 15px;
  border-radius: 999px;
  background: linear-gradient(180deg, #b4532a, #d97742);
}

.block p {
  color: var(--text-secondary);
  line-height: 1.8;
  font-size: 14px;
}

.preserve-line {
  white-space: pre-line;
}

.character-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.character-item {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-radius: 13px;
  padding: 14px;
  transition: border-color 0.18s ease, transform 0.18s ease;
}

.character-item:hover {
  border-color: var(--border-strong);
  transform: translateY(-1px);
}

.character-item strong {
  color: #3d3931;
  margin-right: 8px;
  font-size: 14px;
}

.character-item .role {
  color: var(--accent);
  font-size: 12px;
}

.character-item p {
  margin-top: 7px;
  font-size: 13px;
  color: var(--text-secondary);
}

.volume-item {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color 0.18s ease;
}

.volume-item:hover {
  border-color: var(--border-strong);
}

.volume-item h4 {
  color: #a16207;
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 10px;
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
  background: rgba(192, 86, 33, 0.1);
  border: 1px solid rgba(192, 86, 33, 0.3);
  border-radius: 999px;
  color: var(--accent);
  padding: 6px 13px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.18s ease, box-shadow 0.18s ease;
}

.title-btn:hover:not(:disabled) {
  background: rgba(192, 86, 33, 0.18);
  box-shadow: 0 4px 14px rgba(192, 86, 33, 0.18);
}

.title-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.volume-item ul {
  list-style: none;
  padding-left: 2px;
}

.volume-item li {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 2;
  padding-left: 14px;
  position: relative;
}

.volume-item li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 50%;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: rgba(192, 86, 33, 0.45);
  transform: translateY(-50%);
}

.volume-item li.more {
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 4px;
}

.volume-item li.more::before {
  display: none;
}
</style>

