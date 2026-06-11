<!--
  PageLayout - 通用管理页面布局组件
  用于所有非地图管理页面，提供统一的页头、面包屑和内容区结构
-->
<template>
  <div class="page-layout">
    <div class="page-header">
      <div class="page-header-left">
        <h2 class="page-title">{{ title }}</h2>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>
      <div class="page-header-right">
        <slot name="actions" />
      </div>
    </div>
    <div class="page-body">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.page-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}

.page-header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0;
}

.page-body {
  flex: 1;
  overflow: auto;
  padding: 20px 24px;
}
</style>
