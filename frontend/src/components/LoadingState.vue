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
  gap: 18px;
  padding: 56px 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.spinner {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: conic-gradient(
    from 0deg,
    rgba(192, 86, 33, 0.1),
    #c05621,
    #d97742,
    rgba(192, 86, 33, 0.1)
  );
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 4px), #000 0);
  mask: radial-gradient(farthest-side, transparent calc(100% - 4px), #000 0);
  animation: spin 0.8s linear infinite;
  filter: drop-shadow(0 0 12px rgba(192, 86, 33, 0.3));
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

