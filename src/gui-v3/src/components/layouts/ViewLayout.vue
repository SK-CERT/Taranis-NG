<template>
  <div class="view">
    <div class="view-panel">
      <slot name="panel" />
    </div>
    <div class="view-content">
      <slot name="content" />
    </div>
  </div>
</template>

<script setup>
// Simple layout component with panel and content slots
</script>

<style scoped>
.view {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
}

.view-panel {
  flex: 0 0 auto;
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(var(--v-theme-surface));
}

.view-content {
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
}
</style>
