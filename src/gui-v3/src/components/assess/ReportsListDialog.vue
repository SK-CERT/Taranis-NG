<template>
  <v-dialog v-model="isOpen" max-width="900px" @click:outside="close">
    <v-card>
      <v-toolbar color="primary" dark flat>
        <v-toolbar-title>
          {{ t('assess.reports_dialog.title') }}
        </v-toolbar-title>
        <v-spacer />
        <v-btn icon @click="close">
          <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
        </v-btn>
      </v-toolbar>

      <v-card-text class="pa-4">
        <!-- Loading state -->
        <div v-if="loading" class="text-center pa-4">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <!-- Error state -->
        <div v-else-if="error" class="text-center pa-4">
          <v-icon color="error" size="large">{{ ICONS.ALERT_CIRCLE }}</v-icon>
          <p class="mt-2">{{ error }}</p>
        </div>

        <!-- List view -->
        <div v-else-if="reports.length === 0" class="text-center pa-4">
          <v-icon size="large">{{ ICONS.INFORMATION_OUTLINE }}</v-icon>
          <p class="mt-2">{{ t('assess.reports_dialog.no_reports') }}</p>
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="report in reports"
            :key="report.id"
            class="d-flex align-center ga-2"
          >
            <div class="flex-grow-1">
              <CardAnalyze
                :card="toAnalyzeCard(report)"
                :show-remove-action="true"
                :disable-actions="false"
                @show-detail="viewReport"
                @remove-report-item-from-selector="removeReport"
              />
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ICONS } from '@/config/ui-constants'
import { useI18n } from 'vue-i18n'
import { getReportItemsByAggregate, updateReportItem } from '@/api/analyze'
import CardAnalyze from '@/components/analyze/CardAnalyze.vue'

const { t } = useI18n()

const isOpen = ref(false)
const loading = ref(false)
const error = ref(null)
const reports = ref([])
const currentCard = ref(null)

const emit = defineEmits(['view-report-detail'])

const open = async (card) => {
  currentCard.value = card

  // If only one report, open it directly without dialog
  if (card.in_reports_count === 1) {
    try {
      const response = await getReportItemsByAggregate(card.id)
      const reportItems = response.data.data || response.data

      if (reportItems && reportItems.length === 1) {
        emit('view-report-detail', reportItems[0])
        return
      }
    } catch (err) {
      console.error('Error fetching report:', err)
    }
  }

  // Show dialog for multiple or fallback cases
  showDialog(card)
}

const showDialog = async (card) => {
  isOpen.value = true
  loading.value = true
  error.value = null
  reports.value = []

  try {
    const response = await getReportItemsByAggregate(card.id)
    const reportItems = response.data.data || response.data
    reports.value = reportItems || []
    loading.value = false
  } catch (err) {
    console.error('Error fetching reports:', err)
    error.value = t('assess.reports_dialog.error_loading')
    loading.value = false
  }
}

const viewReport = (report) => {
  // Emit event to open report in NewReportItem
  emit('view-report-detail', report)
  close()
}

const toAnalyzeCard = (report) => {
  // CardAnalyze gates click by access/modify flags; set safe defaults for dialog usage.
  return {
    ...report,
    access: report.access ?? true,
    modify: report.modify ?? true
  }
}

const close = () => {
  isOpen.value = false
  reports.value = []
  currentCard.value = null
  error.value = null
}

const removeReport = async (report) => {
  try {
    const data = {
      delete: true,
      aggregate_id: currentCard.value.id
    }

    await updateReportItem(report.id, data)

    // Remove the report from the list
    reports.value = reports.value.filter((r) => r.id !== report.id)
    if (currentCard.value) {
      currentCard.value.in_reports_count -= 1
    }

    // If no reports left, close the dialog
    if (reports.value.length === 0) {
      close()
    }

    // Show success notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: {
          type: 'success',
          message: t('report_item.removed_from_report')
        }
      })
    )
  } catch (err) {
    console.error('Error removing aggregate:', err)
    error.value = t('assess.reports_dialog.error_removing')
  }
}

defineExpose({
  open,
  close
})
</script>

<style scoped>
.space-y-3 > * + * {
  margin-top: 12px;
}
</style>
