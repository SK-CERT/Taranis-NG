<template>
  <ViewLayout>
    <template #panel>
      <ToolbarFilterPublish
        ref="toolbarFilter"
        title="nav_menu.products"
        total-count-title="toolbar_filter.total_count"
        :show-add-button="canCreateProduct"
        @add-new="handleAddNew"
      />
    </template>
    <template #content>
      <ContentDataPublish ref="contentRef" :selection="publishStore.getSelection" @update-showing-count="updateShowingCount" />
    </template>
  </ViewLayout>

  <NewProduct ref="newProductRef" />
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { usePublishStore } from '@/stores/publish'
import { useAuth } from '@/composables/useAuth'
import ViewLayout from '@/components/layouts/ViewLayout.vue'
import ToolbarFilterPublish from '@/components/publish/ToolbarFilterPublish.vue'
import ContentDataPublish from '@/components/publish/ContentDataPublish.vue'
import NewProduct from '@/components/publish/NewProduct.vue'

const publishStore = usePublishStore()
const { checkPermission } = useAuth()

const newProductRef = ref(null)
const contentRef = ref(null)
const toolbarFilter = ref(null)

const canCreateProduct = computed(() => checkPermission('PUBLISH_CREATE'))

const handleAddNew = () => {
  if (newProductRef.value) {
    newProductRef.value.openDialog()
  }
}

const updateShowingCount = (count) => {
  if (toolbarFilter.value) {
    toolbarFilter.value.updateShowingCount(count)
  }
}

onMounted(async () => {
  if (publishStore.pendingNewProduct) {
    const items = publishStore.pendingNewProduct
    publishStore.pendingNewProduct = null
    await nextTick()
    window.dispatchEvent(new CustomEvent('new-product', { detail: items }))
  }
})

onBeforeRouteLeave(() => {
  publishStore.multiSelect(false)
})
</script>
