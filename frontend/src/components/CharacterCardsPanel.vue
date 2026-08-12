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

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

@media (max-width: 760px) {
  .card-fields {
    grid-template-columns: 1fr;
  }
}
</style>
