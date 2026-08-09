<template>
  <div class="loading-state">
    <div class="spinner"></div>
    <p>{{ text }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ text?: string }>(), {
  text: "AI 正在构思中，请稍候…",
});
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 0;
  color: #9aa3b5;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(110, 168, 255, 0.25);
  border-top-color: #6ea8ff;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
