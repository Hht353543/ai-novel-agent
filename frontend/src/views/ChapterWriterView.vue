<template>
  <div class="writer">
    <div class="toolbar">
      <router-link to="/" class="back-link">← 返回大纲生成</router-link>
      <h2 v-if="outline">{{ outline.title || "未命名小说" }}</h2>
      <div class="toolbar-actions">
        <button class="btn small" @click="refreshProjectList">打开项目</button>
        <button
          class="btn small primary"
          :disabled="saving || !outline"
          @click="onSaveProject"
        >
          {{ saving ? "保存中…" : "保存项目" }}
        </button>
      </div>
    </div>

    <div v-if="outline" class="layout">
      <WriterSidebar
        :outline="outline"
        :volume-index="volumeIndex"
        :chapter-index="chapterIndex"
        @select-chapter="selectChapter"
      />

      <main class="editor-panel">
        <div class="tabs">
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'chapter' }"
            @click="switchToChapter"
          >
            正文编辑
          </button>
          <button
            class="tab-btn"
            :class="{ active: viewMode === 'cards' }"
            @click="switchToCards"
          >
            角色卡
          </button>
        </div>

        <ChapterEditor
          v-if="viewMode === 'chapter'"
          :current-chapter-title="currentChapterTitle"
          :text="text"
          :target-length="targetLength"
          :extra-req="extraReq"
          :chapter-attachment="chapterAttachment"
          :loading="loading"
          :generating-title="generatingTitle"
          :reviewing="reviewing"
          :review-issues="reviewIssues"
          @update:text="text = $event"
          @update:target-length="targetLength = $event"
          @update:extra-req="extraReq = $event"
          @record-cursor="recordCursor"
          @generate="onGenerate"
          @continue="onContinue"
          @rewrite="onRewrite"
          @generate-title-from-text="onGenerateTitleFromText"
          @attach-file="onAttachFile"
          @remove-attachment="removeAttachment"
          @review="onReviewChapter"
        />

        <CharacterCardsPanel
          v-else
          :outline="outline"
          :current-card-volume-label="currentCardVolumeLabel"
          :card-volume-index="cardVolumeIndex"
          :volume-cards="volumeCards"
          :generating-cards="generatingCards"
          @update:card-volume-index="cardVolumeIndex = $event"
          @generate-cards="onGenerateCards"
          @add-card="onAddCard"
          @remove-card="onRemoveCard"
        />

        <p v-if="message" class="message" :class="{ error: isError }">{{ message }}</p>
      </main>
    </div>

    <div v-else class="empty">
      <p>还没有打开任何项目。</p>
      <button class="btn primary open-btn" @click="refreshProjectList">
        打开已保存的项目
      </button>
      <p>或先 <router-link to="/">生成大纲</router-link>，再进入章节写作。</p>
    </div>

    <ProjectListModal
      :show-project-list="showProjectList"
      :project-list="projectList"
      @close="showProjectList = false"
      @open="openProject"
      @delete="onDeleteProject"
    />
  </div>
</template>

<script setup lang="ts">
import CharacterCardsPanel from "../components/CharacterCardsPanel.vue";
import ChapterEditor from "../components/ChapterEditor.vue";
import ProjectListModal from "../components/ProjectListModal.vue";
import WriterSidebar from "../components/WriterSidebar.vue";
import { useWriterActions } from "../composables/useWriterActions";
import { useWriterState } from "../composables/useWriterState";

const {
  outline,
  text,
  volumeIndex,
  chapterIndex,
  targetLength,
  extraReq,
  loading,
  saving,
  message,
  isError,
  projectList,
  showProjectList,
  viewMode,
  cardVolumeIndex,
  generatingCards,
  generatingTitle,
  attachment: chapterAttachment,
  onAttachFile,
  removeAttachment,
} = useWriterState();

const {
  currentChapterTitle,
  currentCardVolumeLabel,
  volumeCards,
  reviewing,
  reviewIssues,
  selectChapter,
  recordCursor,
  refreshProjectList,
  openProject,
  onSaveProject,
  onDeleteProject,
  onGenerate,
  onContinue,
  onRewrite,
  onGenerateTitleFromText,
  onReviewChapter,
  switchToChapter,
  switchToCards,
  onGenerateCards,
  onAddCard,
  onRemoveCard,
} = useWriterActions();
</script>


<style scoped>
.writer {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 253, 248, 0.78);
  backdrop-filter: blur(16px) saturate(1.25);
  -webkit-backdrop-filter: blur(16px) saturate(1.25);
  box-shadow: 0 10px 30px rgba(90, 80, 60, 0.12);
}

.toolbar h2 {
  font-size: 19px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #3d3931;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.back-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 500;
  transition: color 0.18s ease;
}

.back-link:hover {
  color: var(--accent);
}

.layout {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 18px;
  align-items: start;
}

.editor-panel {
  background: var(--panel);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 22px;
  box-shadow: var(--shadow);
}

.tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.66);
  border: 1px solid var(--border);
  border-radius: 12px;
}

.tab-btn {
  background: transparent;
  border: none;
  border-radius: 9px;
  color: var(--text-secondary);
  padding: 8px 18px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.tab-btn:hover {
  color: var(--text);
}

.tab-btn.active {
  background: linear-gradient(135deg, rgba(201, 118, 66, 0.95), rgba(154, 63, 30, 0.95));
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(192, 86, 33, 0.2);
}

.message {
  margin-top: 12px;
  color: var(--success);
  font-size: 13px;
  line-height: 1.7;
}

.message.error {
  color: var(--danger);
}

.empty {
  background: var(--panel);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  border: 1px dashed var(--border-strong);
  border-radius: 20px;
  padding: 56px 32px;
  text-align: center;
  color: var(--text-secondary);
  box-shadow: var(--shadow);
}

.empty a {
  color: var(--accent);
  text-decoration: none;
}

.open-btn {
  margin: 18px 0;
}

.btn {
  background: rgba(93, 82, 60, 0.06);
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  color: var(--text);
  padding: 10px 16px;
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease,
    transform 0.18s ease, box-shadow 0.18s ease;
}

.btn:hover:not(:disabled) {
  background: rgba(192, 86, 33, 0.12);
  border-color: rgba(192, 86, 33, 0.35);
  transform: translateY(-1px);
}

.btn.primary {
  background: linear-gradient(135deg, #c05621, #9a3f1e);
  border: none;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 6px 18px rgba(192, 86, 33, 0.18);
}

.btn.primary:hover:not(:disabled) {
  filter: brightness(1.06);
  box-shadow: 0 8px 22px rgba(192, 86, 33, 0.22);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn.small {
  padding: 8px 14px;
  font-size: 13px;
}

@media (max-width: 760px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-wrap: wrap;
  }
}
</style>

