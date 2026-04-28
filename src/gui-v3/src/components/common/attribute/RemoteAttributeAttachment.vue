<template>
  <attribute-item-layout
    :attribute-group="attributeGroup"
    :read-only="true"
    :editable="false"
  >
    <template #values>
      <div v-for="value in attributeGroup.attributes" :key="value.id">
        <attribute-value-layout
          :value="value"
          :read-only="true"
          :editable="false"
        >
          <template #display>
            <!-- TODO: Display remote file attachment info -->
            <!-- Phase 3: Show filename, size, download link -->
            <!-- May need to fetch file metadata from API feed -->
            <div class="flex items-center gap-2 text-sm text-gray-300">
              <v-icon size="small">{{ ICONS.FILE_DOCUMENT }}</v-icon>
              <span>{{ value.value.filename || 'Remote Attachment' }}</span>
              <span class="text-xs text-gray-500">
                ({{ formatFileSize(value.value.size) }})
              </span>
              <button
                class="text-blue-400 hover:text-blue-300 text-xs ml-auto"
                @click="downloadRemoteAttachment(value.value)"
              >
                Download
              </button>
            </div>
          </template>
        </attribute-value-layout>
      </div>
    </template>
  </attribute-item-layout>
</template>

<script setup>
import { ICONS } from '@/config/ui-constants'
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'

const props = defineProps({
  attributeGroup: {
    type: Object,
    required: true
  },
  reportItemId: {
    type: Number,
    required: true
  }
})

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const downloadRemoteAttachment = (attachment) => {
  // TODO: Phase 3 - Implement remote file download
  // May need to use a different API endpoint for remote files
  // Handle proxying if needed
  console.log('Download remote attachment TODO:', attachment)
}

// TODO: Phase 3 - Add remote-specific features:
// - Show source/origin of remote file
// - Display when file was sourced from API feed
// - Handle download from external sources
// - Show file verification/hash if available
</script>

<style scoped>
/* TODO: Add remote attachment styling */
</style>
