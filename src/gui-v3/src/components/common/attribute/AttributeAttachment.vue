<template>
  <AttributeItemLayout :add-button="false" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <div v-if="readOnly || values[index].remote" class="attachment-display d-flex align-center pa-3">
          <v-icon color="primary" class="mr-3">{{ ICONS.FILE_DOCUMENT }}</v-icon>
          <div class="flex-grow-1">
            <div class="text-body-2 font-weight-medium">
              {{ values[index].binary_description || 'Attachment' }}
            </div>
            <div class="text-caption text-grey">
              {{ values[index].binary_mime_type }} - {{ formatFileSize(values[index].binary_size) }}
            </div>
          </div>
          <v-btn
            size="small"
            variant="text"
            @click="downloadAttachmentNow(values[index])"
          >
            <v-icon>{{ ICONS.DOWNLOAD }}</v-icon>
          </v-btn>
        </div>

        <!-- Editable -->
        <AttributeValueLayout
          v-if="!readOnly && canModify && !values[index].remote"
          :del-button="false"
          :occurrence="attributeGroup.min_occurrence"
          :values="values"
          :val-index="index"
          @del-value="del(index)"
        >
          <template #col_middle>
            <div class="d-flex align-center">
              <div v-if="values[index].binary_description" class="mr-3">
                <div class="text-body-2">{{ values[index].binary_description }}</div>
                <div class="text-caption text-grey">
                  {{ values[index].binary_mime_type }} - {{ formatFileSize(values[index].binary_size) }}
                </div>
              </div>
              <v-btn
                v-if="values[index].id > 0"
                size="small"
                variant="text"
                @click="downloadAttachmentNow(values[index])"
              >
                <v-icon>{{ ICONS.DOWNLOAD }}</v-icon>
              </v-btn>
            </div>
          </template>
        </AttributeValueLayout>
      </div>
    </template>
  </AttributeItemLayout>
</template>

<script setup>
import { ICONS } from '@/config/ui-constants'
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'
import { useAttributes } from './useAttributes.js'
import { downloadAttachment } from '@/api/analyze'

const props = defineProps({
  attributeGroup: {
    type: Object,
    required: true
  },
  values: {
    type: Array,
    required: true
  },
  readOnly: {
    type: Boolean,
    default: false
  },
  edit: {
    type: Boolean,
    default: false
  },
  modify: {
    type: Boolean,
    default: false
  },
  reportItemId: {
    type: Number,
    required: true
  }
})

const { canModify, add, del } = useAttributes(props)

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const downloadAttachmentNow = (attrValue) => {
  if (!attrValue || !attrValue.id) return
  const fileName = attrValue.binary_description || 'attachment'
  const downloadLink = `/analyze/report-items/${props.reportItemId}/file-attributes/${attrValue.id}/file`
  downloadAttachment(downloadLink, fileName)
}
</script>

<style scoped>
.attachment-display {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
