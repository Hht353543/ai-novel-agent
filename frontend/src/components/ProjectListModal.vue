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
  z-index: 100;
  background: rgba(60, 50, 35, 0.35);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  animation: fade-in 0.18s ease;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal {
  background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(247, 243, 234, 0.98));
  border: 1px solid var(--border-strong);
  border-radius: 20px;
  width: min(580px, 94vw);
  max-height: 74vh;
  display: flex;
  flex-direction: column;
  padding: 22px;
  box-shadow: 0 30px 80px rgba(90, 80, 60, 0.18);
  animation: pop-in 0.22s ease;
}

@keyframes pop-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-head h3 {
  color: #3d3931;
  font-size: 17px;
  font-weight: 650;
}

.project-list {
  overflow-y: auto;
}

.project-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--border);
  border-radius: 13px;
  padding: 14px 16px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: border-color 0.18s ease, background 0.18s ease,
    transform 0.18s ease;
}

.project-item:hover {
  border-color: rgba(192, 86, 33, 0.4);
  background: rgba(192, 86, 33, 0.06);
  transform: translateY(-1px);
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.project-info strong {
  color: #3d3931;
  font-size: 15px;
  font-weight: 600;
}

.project-info span {
  color: var(--text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.delete-btn {
  background: transparent;
  border: 1px solid rgba(220, 38, 38, 0.35);
  border-radius: 9px;
  color: var(--danger);
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.18s ease;
  flex-shrink: 0;
}

.delete-btn:hover {
  background: rgba(220, 38, 38, 0.1);
}

.modal-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 36px 0;
}

.btn {
  background: rgba(93, 82, 60, 0.06);
  border: 1px solid var(--border-strong);
  border-radius: 10px;
  color: var(--text);
  padding: 9px 15px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}

.btn:hover {
  background: rgba(192, 86, 33, 0.12);
  border-color: rgba(192, 86, 33, 0.35);
}

.btn.small {
  padding: 8px 14px;
  font-size: 12.5px;
}
</style>

