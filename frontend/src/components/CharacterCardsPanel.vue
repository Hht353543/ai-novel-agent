<template>
  <div class="cards-panel">
    <div class="chapter-head">
      <h3>角色卡 · {{ currentCardVolumeLabel }}</h3>
      <div class="card-toolbar">
        <select :value="cardVolumeIndex" @change="onVolumeChange">
          <option v-for="(vol, vi) in outline?.volume_plan || []" :key="vi" :value="vi">
            第{{ vi + 1 }}卷 {{ vol.volume }}
          </option>
        </select>
        <button class="btn" :disabled="generatingCards" @click="emit('generate-cards')">
          {{ generatingCards ? "生成中…" : "AI 生成本卷角色卡" }}
        </button>
        <button class="btn" @click="emit('add-card')">添加角色卡</button>
      </div>
    </div>

    <div v-if="volumeCards.length" class="card-list">
      <details v-for="(card, i) in volumeCards" :key="i" class="card-item" :open="i === 0">
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
          <button class="delete-btn" @click="emit('remove-card', card)">删除该角色卡</button>
        </div>
      </details>
    </div>
    <p v-else class="cards-empty">
      本卷还没有角色卡。点击「AI 生成本卷角色卡」自动生成，或「添加角色卡」手动填写。
      编辑后的角色卡会随「保存项目」一起持久化，并在生成正文时约束角色设定。
    </p>
  </div>
</template>

<script setup lang="ts">
import type { CharacterCard, NovelOutline } from "../api/novel";

defineProps<{
  outline: NovelOutline;
  currentCardVolumeLabel: string;
  cardVolumeIndex: number;
  volumeCards: CharacterCard[];
  generatingCards: boolean;
}>();

const emit = defineEmits<{
  (e: "update:card-volume-index", value: number): void;
  (e: "generate-cards"): void;
  (e: "add-card"): void;
  (e: "remove-card", card: CharacterCard): void;
}>();

function onVolumeChange(event: Event): void {
  emit("update:card-volume-index", Number((event.target as HTMLSelectElement).value));
}
</script>

<style scoped>
.cards-panel {
  animation: fade-in 0.25s ease;
}

@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.chapter-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 10px;
}

.chapter-head h3 {
  color: #3d3931;
  font-size: 17px;
  font-weight: 650;
}

.card-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.card-toolbar select {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text);
  padding: 9px 12px;
  font-size: 13px;
  outline: none;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-item {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 16px;
  transition: border-color 0.18s ease;
}

.card-item:hover {
  border-color: var(--border-strong);
}

.card-item summary {
  cursor: pointer;
  color: #3d3931;
  font-size: 15px;
  font-weight: 600;
  list-style: none;
}

.card-item summary::-webkit-details-marker {
  display: none;
}

.card-role {
  color: var(--accent);
  font-size: 12px;
  font-weight: 500;
  margin-left: 8px;
}

.card-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 11px;
  margin-top: 12px;
}

.card-fields label {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.card-fields input,
.card-fields textarea {
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid var(--border-strong);
  border-radius: 9px;
  color: var(--text);
  padding: 9px 11px;
  font-size: 13px;
  line-height: 1.6;
  outline: none;
  resize: vertical;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.card-fields input:focus,
.card-fields textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(192, 86, 33, 0.14);
}

.card-fields .delete-btn {
  justify-self: start;
  align-self: end;
  margin-top: 4px;
}

.cards-empty {
  color: var(--text-secondary);
  font-size: 13.5px;
  line-height: 1.9;
  padding: 28px 8px;
}

.btn {
  background: rgba(93, 82, 60, 0.06);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text);
  padding: 9px 15px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease,
    transform 0.18s ease;
}

.btn:hover:not(:disabled) {
  background: rgba(192, 86, 33, 0.12);
  border-color: rgba(192, 86, 33, 0.35);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.delete-btn {
  background: transparent;
  border: 1px solid rgba(220, 38, 38, 0.35);
  border-radius: 9px;
  color: var(--danger);
  padding: 7px 13px;
  font-size: 12.5px;
  cursor: pointer;
  transition: background 0.18s ease;
  flex-shrink: 0;
}

.delete-btn:hover {
  background: rgba(220, 38, 38, 0.1);
}

@media (max-width: 760px) {
  .card-fields {
    grid-template-columns: 1fr;
  }
}
</style>

