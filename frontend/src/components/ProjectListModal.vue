<template>
  <div v-if="showProjectList" class="modal-mask" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-head">
        <h3>已保存的项目</h3>
        <button class="btn small" @click="emit('close')">关闭</button>
      </div>
      <div v-if="projectList.length" class="project-list">
        <div
          v-for="p in projectList"
          :key="p.id"
          class="project-item"
          @click="emit('open', p.id)"
        >
          <div class="project-info">
            <strong>{{ p.title }}</strong>
            <span>{{ p.chapter_count }} 章 · {{ formatTime(p.updated_at) }}</span>
          </div>
          <button class="delete-btn" @click.stop="emit('delete', p.id)">删除</button>
        </div>
      </div>
      <p v-else class="modal-empty">暂无已保存的项目。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProjectSummary } from "../api/project";

defineProps<{
  showProjectList: boolean;
  projectList: ProjectSummary[];
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "open", id: string): void;
  (e: "delete", id: string): void;
}>();

function formatTime(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(8, 10, 20, 0.72);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  background: #171b2c;
  border: 1px solid #2b3150;
  border-radius: 14px;
  width: min(560px, 92vw);
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.modal-head h3 {
  color: #ffffff;
  font-size: 17px;
}

.project-list {
  overflow-y: auto;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #202540;
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 10px;
  cursor: pointer;
}

.project-item:hover {
  border: 1px solid #6ea8ff;
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.project-info strong {
  color: #ffffff;
  font-size: 15px;
}

.project-info span {
  color: #9aa3b5;
  font-size: 12px;
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

.modal-empty {
  color: #9aa3b5;
  text-align: center;
  padding: 32px 0;
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

.btn.small {
  padding: 8px 14px;
  font-size: 13px;
}
</style>
