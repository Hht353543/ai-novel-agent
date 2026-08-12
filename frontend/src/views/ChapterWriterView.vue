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
  gap: 18px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 18px;
}

.toolbar h2 {
  font-size: 20px;
  color: #6ea8ff;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.btn.small {
  padding: 8px 14px;
  font-size: 13px;
}

.btn.small.primary {
  background: linear-gradient(90deg, #4f8cff, #8a5cff);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.btn.small.primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.back-link {
  color: #9aa3b5;
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  color: #6ea8ff;
}

.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 18px;
  align-items: start;
}

.editor-panel {
  background: #171b2c;
  border: 1px solid #262c45;
  border-radius: 14px;
  padding: 20px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-btn {
  background: transparent;
  border: 1px solid #2b3150;
  border-radius: 999px;
  color: #9aa3b5;
  padding: 7px 18px;
  font-size: 14px;
  cursor: pointer;
}

.tab-btn:hover {
  color: #6ea8ff;
  border-color: #6ea8ff;
}

.tab-btn.active {
  background: rgba(110, 168, 255, 0.15);
  border-color: #6ea8ff;
  color: #6ea8ff;
}

.message {
  margin-top: 10px;
  color: #7ddfa0;
  font-size: 13px;
}

.message.error {
  color: #ff7b7b;
}

.empty {
  background: #171b2c;
  border: 1px dashed #2b3150;
  border-radius: 14px;
  padding: 48px;
  text-align: center;
  color: #9aa3b5;
}

.empty a {
  color: #6ea8ff;
}

.open-btn {
  margin: 16px 0;
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

.btn.primary {
  background: linear-gradient(90deg, #4f8cff, #8a5cff);
  border: none;
  color: #ffffff;
  font-weight: 600;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
