<template>
  <NewsItemDetailDialog
    v-model="showDialog"
    :news-item="newsItem"
    :multi-select-active="multiSelectActive"
    @action="handleAction"
    @delete="handleDelete"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'
import { getNewsItem } from '@/api/assess'

const props = defineProps({
  attach: {
    type: [String, HTMLElement],
    default: undefined
  },
  verticalView: {
    type: Boolean,
    default: false
  },
  multiSelectActive: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['action', 'delete'])

const showDialog = ref(false)
const newsItem = ref({})

const open = async (item) => {
  try {
    // For single items, get the full detail from API
    if (item && item.id) {
      const response = await getNewsItem(item.id)
      newsItem.value = response || item
    } else {
      newsItem.value = item
    }
    showDialog.value = true
  } catch (_error) {
    // Fallback to passed item data
    newsItem.value = item
    showDialog.value = true
  }
}

const handleAction = (payload) => {
  emit('action', payload)
}

const handleDelete = (item) => {
  showDialog.value = false
  emit('delete', item)
}

defineExpose({
  open
})
</script>
