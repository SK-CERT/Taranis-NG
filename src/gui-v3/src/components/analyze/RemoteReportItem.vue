<template>
  <v-dialog
    v-model="visible"
    fullscreen
    persistent
    @keydown.esc="handleClose"
  >
    <v-card>
      <v-toolbar color="primary" dark>
        <v-btn icon @click="handleClose">
          <v-icon>mdi-close-circle</v-icon>
        </v-btn>
        <v-toolbar-title>{{ reportItem.title }}</v-toolbar-title>
        <v-spacer />
      </v-toolbar>

      <v-card-text class="pa-6">
        <div>
          <strong>{{ t('report_item.id') }}:</strong>
          <span>{{ reportItem.uuid }}</span>
        </div>

        <v-divider class="my-4" />

        <h3 class="text-h6 mb-4">{{ t('report_item.attributes') }}</h3>
        <v-container v-if="reportItem.attributes && reportItem.attributes.length > 0">
          <RemoteAttributeContainer
            v-for="attribute in reportItem.attributes"
            :key="attribute.id"
            :attribute-item="attribute"
          />
        </v-container>
        <v-alert v-else type="info">
          {{ t('report_item.no_attributes') }}
        </v-alert>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import RemoteAttributeContainer from '@/components/common/attribute/RemoteAttributeContainer.vue'
import { getReportItem } from '@/api/analyze'

const { t } = useI18n()

const visible = ref(false)
const reportItem = ref({
  id: null,
  title: '',
  uuid: '',
  attributes: []
})

const showDetail = async (item) => {
  try {
    const response = await getReportItem(item.id)
    reportItem.value = response || item
    visible.value = true
  } catch (_error) {
    // Fallback to passed item data
    reportItem.value = item
    visible.value = true
  }
}

const handleClose = () => {
  visible.value = false
}

defineExpose({
  showDetail
})
</script>
