<template>
  <v-row>
    <v-btn v-if="showButton && canCreate" color="primary" variant="elevated" @click="addEmptyReportItem">
      <v-icon start>mdi-plus</v-icon>
      <span>{{ t('common.add_btn') }}</span>
    </v-btn>

    <v-dialog v-model="visible" fullscreen persistent @keydown.esc="cancel">
      <v-dialog v-model="showCloseConfirmation" max-width="500px" persistent>
        <v-card>
          <v-card-title class="text-h5">{{ t('confirm_close.title') }}</v-card-title>
          <v-card-text>{{ t('report_item.confirm_close.message') }}</v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn color="" @click="showCloseConfirmation = false">
              {{ t('confirm_close.continue') }}
            </v-btn>
            <v-btn color="primary" @click="saveAndClose">
              {{ t('confirm_close.save_and_close') }}
            </v-btn>
            <v-btn color="error" @click="confirmClose">
              {{ t('confirm_close.close') }}
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <v-overlay v-model="overlay" contained class="align-center justify-center" z-index="50000">
        <v-progress-circular indeterminate size="64" />
      </v-overlay>

      <v-card>
        <v-toolbar color="primary" dark data-dialog="report-item">
          <v-btn icon data-btn="cancel" @click="cancel">
            <v-icon>mdi-close-circle</v-icon>
          </v-btn>

          <v-toolbar-title>
            <span v-if="!edit">{{ t('report_item.add_new') }}</span>
            <span v-else-if="readOnly">{{ t('report_item.read') }}</span>
            <span v-else>{{ t('report_item.edit') }}</span>
          </v-toolbar-title>

          <v-spacer />

          <v-switch v-model="verticalView" hide-details density="compact" label="Side-by-side view" class="mt-5" />

          <v-spacer />

          <StateSelector
            v-if="available_states.length > 0"
            v-model="report_item.state_id"
            :available-states="available_states"
            :label="t('report_item.state')"
            :disabled="!canModify"
            @update:model-value="saveReportItem('state_id')"
          />

          <v-btn v-if="!edit" variant="text" @click="addReportItem">
            <v-icon start>mdi-content-save</v-icon>
            <span>{{ t('common.save') }}</span>
          </v-btn>
        </v-toolbar>

        <v-row no-gutters>
          <v-col :cols="verticalView ? 6 : 12" :style="verticalView ? 'height: calc(100vh - 3em); overflow-y: auto;' : ''">
            <v-form ref="formRef" class="px-4" @submit.prevent="addReportItem">
              <v-row no-gutters>
                <v-col v-if="edit" cols="12">
                  <span class="text-caption text-grey">ID: {{ report_item.uuid }}</span>
                </v-col>
                <v-col cols="4" class="pr-3">
                  <v-combobox
                    v-model="selected_type"
                    :disabled="edit"
                    :items="report_types"
                    item-title="title"
                    :label="t('report_item.report_type')"
                    :rules="[(v) => !!v || t('error.required')]"
                    return-object
                    @update:model-value="reportSelected"
                  />
                </v-col>
                <v-col cols="4" class="pr-3">
                  <v-text-field
                    v-model="report_item.title_prefix"
                    :label="t('report_item.title_prefix')"
                    :disabled="field_locks.title_prefix || !canModify"
                    :class="getLockedStyle('title_prefix')"
                    :spellcheck="spellcheck"
                    @focus="onFocus('title_prefix')"
                    @blur="saveReportItem('title_prefix')"
                    @keyup="onKeyUp('title_prefix')"
                  />
                </v-col>
                <v-col cols="4" class="pr-3">
                  <v-text-field
                    v-model="report_item.title"
                    :label="t('report_item.title')"
                    :disabled="field_locks.title || !canModify"
                    :class="getLockedStyle('title')"
                    :rules="[(v) => !!v || t('error.required')]"
                    :spellcheck="spellcheck"
                    @focus="onFocus('title')"
                    @blur="saveReportItem('title')"
                    @keyup="onKeyUp('title')"
                  />
                </v-col>
              </v-row>

              <v-row no-gutters class="pb-4">
                <v-col cols="12">
                  <v-btn
                    v-if="canModify"
                    :prepend-icon="ICONS.PLUS"
                    variant="outlined"
                    class="mb-3"
                    @click="newsItemSelectorRef?.openSelector()"
                  >
                    {{ t('assess.add_news_item') }}
                  </v-btn>
                </v-col>
              </v-row>

              <v-row v-if="!verticalView" no-gutters>
                <v-col cols="12">
                  <NewsItemSelector
                    ref="newsItemSelectorRef"
                    :attach="false"
                    :values="news_item_aggregates"
                    :modify="modify"
                    :report-item-id="report_item.id"
                    :edit="edit"
                    :vertical-view="false"
                    @items-changed="updateNewsItemAggregates"
                  />
                </v-col>
              </v-row>

              <v-row no-gutters>
                <v-col cols="12">
                  <RemoteReportItemSelector
                    :values="remote_report_items"
                    :modify="modify"
                    :edit="edit"
                    :report-item-id="report_item.id"
                    @remote-report-items-changed="updateRemoteAttributes"
                  />
                </v-col>
              </v-row>

              <!-- Attribute Groups -->
              <v-row>
                <v-col cols="12" class="pa-0 ma-0">
                  <v-expansion-panels
                    v-for="(attribute_group, i) in attribute_groups"
                    :key="attribute_group.id"
                    v-model="expandPanelGroups"
                    multiple
                    class="mb-1"
                  >
                    <v-expansion-panel>
                      <v-expansion-panel-title class="text-primary text-body-1 text-uppercase pa-3">
                        {{ attribute_group.title }}
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <v-expansion-panels v-model="expand_group_items[i].values" multiple class="items">
                          <v-expansion-panel
                            v-for="attribute_item in attribute_group.attribute_group_items"
                            :key="attribute_item.attribute_group_item.id"
                            class="item-panel"
                          >
                            <v-expansion-panel-title class="pa-2 font-weight-bold text-primary rounded-0">
                              <v-row>
                                <span>{{ attribute_item.attribute_group_item.title }}</span>
                                <span v-if="getAttributeMeta(attribute_item)" class="attribute-meta text-medium-emphasis ml-2">
                                  {{ getAttributeMeta(attribute_item) }}
                                </span>
                              </v-row>
                            </v-expansion-panel-title>
                            <v-expansion-panel-text class="pt-0">
                              <v-row align="center">
                                <v-col>
                                  <AttributeContainer
                                    :attribute-item="attribute_item"
                                    :edit="edit"
                                    :modify="modify"
                                    :report-item-id="report_item.id"
                                    :read-only="readOnly"
                                  />
                                </v-col>
                                <v-col class="d-flex justify-end" cols="auto">
                                  <v-btn
                                    v-if="!!attribute_item.attribute_group_item.ai_provider_id"
                                    variant="text"
                                    size="small"
                                    :title="t('report_item.tooltip.auto_generate')"
                                    @click="autoGenerate(attribute_item.attribute_group_item.id)"
                                  >
                                    <v-icon>
                                      {{ autoGenerateIcon[attribute_item.attribute_group_item.id] || 'mdi-creation' }}
                                    </v-icon>
                                  </v-btn>
                                </v-col>
                              </v-row>
                            </v-expansion-panel-text>
                          </v-expansion-panel>
                        </v-expansion-panels>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </v-col>
              </v-row>

              <v-row no-gutters class="pt-2">
                <v-col cols="12">
                  <v-alert v-if="show_validation_error" density="compact" type="error" variant="tonal">
                    {{ t('error.validation') }}
                  </v-alert>
                  <v-alert v-if="show_error" density="compact" type="error" variant="tonal">
                    {{ t('report_item.error') }}
                  </v-alert>
                </v-col>
              </v-row>
            </v-form>
          </v-col>

          <v-col v-if="verticalView" :cols="6" style="height: calc(100vh - 3em); overflow-y: auto" class="pa-5 taranis-ng-vertical-view">
            <NewsItemSelector
              ref="newsItemSelectorRef"
              attach=".taranis-ng-vertical-view"
              :values="news_item_aggregates"
              :modify="modify"
              :report-item-id="report_item.id"
              :edit="edit"
              :vertical-view="true"
              @items-changed="updateNewsItemAggregates"
            />
          </v-col>
        </v-row>
      </v-card>
    </v-dialog>
  </v-row>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { ICONS } from '@/config/ui-constants'
import { useAnalyzeStore } from '@/stores/analyze'
import { useSettingsStore } from '@/stores/settings'
import {
  createNewReportItem,
  updateReportItem,
  lockReportItem,
  unlockReportItem,
  holdLockReportItem,
  getReportItem,
  getReportItemData,
  getReportItemLocks,
  aiGenerate
} from '@/api/analyze'
import { getEntityTypeStates } from '@/api/state'
import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'
import NewsItemSelector from '@/components/analyze/NewsItemSelector.vue'
import RemoteReportItemSelector from '@/components/analyze/RemoteReportItemSelector.vue'
import StateSelector from '@/components/common/StateSelector.vue'

const props = defineProps({
  showButton: {
    type: Boolean,
    default: true
  },
  readOnly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['data-updated'])

const { t, te } = useI18n()
const route = useRoute()
const router = useRouter()
const { checkPermission, getUserId } = useAuth()
const analyzeStore = useAnalyzeStore()
const settingsStore = useSettingsStore()

// Refs
const formRef = ref(null)
const newsItemSelectorRef = ref(null)

// Dialog state
const visible = ref(false)
const edit = ref(false)
const modify = ref(true)
const overlay = ref(false)
const showCloseConfirmation = ref(false)
const verticalView = ref(false)
const show_validation_error = ref(false)
const show_error = ref(false)
const key_timeout = ref(null)
const initialFormState = ref(null)

// Data
const report_types = ref([])
const selected_type = ref(null)
const attribute_groups = ref([])
const news_item_aggregates = ref([])
const remote_report_items = ref([])
const available_states = ref([])
const expand_group_items = ref([])
const autoGenerateIcon = reactive({})
const autoGenerateIconTimer = reactive({})
const local_reports = ref(true)

const field_locks = reactive({
  title_prefix: false,
  title: false
})

const report_item = reactive({
  id: null,
  uuid: null,
  title: '',
  title_prefix: '',
  report_item_type_id: null,
  state_id: null,
  news_item_aggregates: [],
  remote_report_items: [],
  attributes: []
})

// Computed
const canCreate = computed(() => {
  return checkPermission('ANALYZE_CREATE') && local_reports.value === true
})

const canModify = computed(() => {
  return edit.value === false || (checkPermission('ANALYZE_UPDATE') && modify.value === true)
})

const expandPanelGroups = computed(() => {
  return Array.from(Array(attribute_groups.value.length).keys())
})

const spellcheck = computed(() => {
  const setting = settingsStore.getSetting('SPELLCHECK')
  return setting ? setting.value === 'true' : true
})

// Methods
const initializeNewReportItem = (newsItemAggregates = []) => {
  visible.value = true
  modify.value = true
  edit.value = false
  overlay.value = false
  show_error.value = false
  field_locks.title = false
  field_locks.title_prefix = false
  selected_type.value = null
  attribute_groups.value = []
  news_item_aggregates.value = newsItemAggregates
  remote_report_items.value = []
  report_item.id = null
  report_item.uuid = null
  report_item.title = ''
  report_item.title_prefix = ''
  report_item.report_item_type_id = null
  selectDefaultState()
  resetValidation()
  resetAutoGenerate()
  initialFormState.value = snapshotForm()
}

const addEmptyReportItem = () => {
  initializeNewReportItem([])
}

const reportSelected = () => {
  attribute_groups.value = []
  expand_group_items.value = []

  if (!selected_type.value?.attribute_groups) return

  for (let i = 0; i < selected_type.value.attribute_groups.length; i++) {
    const group = {
      id: selected_type.value.attribute_groups[i].id,
      title: selected_type.value.attribute_groups[i].title,
      attribute_group_items: []
    }

    for (let j = 0; j < selected_type.value.attribute_groups[i].attribute_group_items.length; j++) {
      group.attribute_group_items.push({
        attribute_group_item: selected_type.value.attribute_groups[i].attribute_group_items[j],
        values: []
      })
    }

    attribute_groups.value.push(group)
    expand_group_items.value.push({
      values: Array.from(Array(group.attribute_group_items.length).keys())
    })
  }
}

const cancel = () => {
  if (!edit.value && hasUnsavedChanges()) {
    showCloseConfirmation.value = true
    return
  }
  closeDialog()
}

const confirmClose = () => {
  showCloseConfirmation.value = false
  closeDialog()
}

const saveAndClose = async () => {
  showCloseConfirmation.value = false
  await addReportItem()
}

const closeDialog = () => {
  setTimeout(() => {
    resetValidation()
    showCloseConfirmation.value = false
    visible.value = false
  }, 150)
}

const addReportItem = async () => {
  if (!formRef.value) return
  const { valid } = await formRef.value.validate()
  if (!valid) {
    show_validation_error.value = true
    return false
  }

  show_validation_error.value = false
  show_error.value = false
  overlay.value = true

  report_item.report_item_type_id = selected_type.value.id
  report_item.news_item_aggregates = news_item_aggregates.value.map((item) => ({ id: item.id }))
  report_item.remote_report_items = remote_report_items.value.map((item) => ({ id: item.id }))

  // Collect attribute values
  report_item.attributes = []
  for (let i = 0; i < attribute_groups.value.length; i++) {
    for (let j = 0; j < attribute_groups.value[i].attribute_group_items.length; j++) {
      for (let k = 0; k < attribute_groups.value[i].attribute_group_items[j].values.length; k++) {
        let value = attribute_groups.value[i].attribute_group_items[j].values[k].value
        const value_description = attribute_groups.value[i].attribute_group_items[j].values[k].value_description
        const attrType = attribute_groups.value[i].attribute_group_items[j].attribute_group_item.attribute.type

        if (attrType === 'CPE') {
          value = value.replace('*', '%')
        } else if (attrType === 'BOOLEAN') {
          value = value === true ? 'true' : 'false'
        }

        if (attrType !== 'ATTACHMENT') {
          report_item.attributes.push({
            id: -1,
            value: value,
            value_description: value_description,
            attribute_group_item_id: attribute_groups.value[i].attribute_group_items[j].attribute_group_item.id
          })
        }
      }
    }
  }

  try {
    const response = await createNewReportItem(report_item)
    report_item.id = response.data
    overlay.value = false
    closeDialog()
    emit('data-updated')
    router.push('/analyze')
    return true
  } catch (error) {
    console.error('Error creating report item:', error)
    show_error.value = true
    overlay.value = false
    return false
  }
}

const saveReportItem = (field_id) => {
  if (!edit.value) return

  const data = { update: true }
  if (field_id === 'title') {
    data.title = report_item.title
  } else if (field_id === 'title_prefix') {
    data.title_prefix = report_item.title_prefix
  } else if (field_id === 'state_id') {
    data.state_id = report_item.state_id
  }

  updateReportItem(report_item.id, data)
    .then(() => {
      window.dispatchEvent(new CustomEvent('report-item-updated'))
    })
    .catch(() => {})
  unlockReportItem(report_item.id, { field_id }).catch(() => {})
}

const resetValidation = () => {
  show_validation_error.value = false
  formRef.value?.resetValidation()
}

const getLockedStyle = (field_id) => {
  return field_locks[field_id] === true ? 'locked-style' : ''
}

const onFocus = (field_id) => {
  if (edit.value === true) {
    lockReportItem(report_item.id, { field_id }).catch(() => {})
  }
}

const onKeyUp = (field_id) => {
  if (edit.value === true) {
    clearTimeout(key_timeout.value)
    key_timeout.value = setTimeout(() => {
      holdLockReportItem(report_item.id, { field_id }).catch(() => {})
    }, 1000)
  }
}

const showDetail = async (report_item_data) => {
  initialFormState.value = null
  resetAutoGenerate()

  try {
    const response = await getReportItem(report_item_data.id)
    const data = response.data

    edit.value = true
    overlay.value = false
    show_error.value = false
    modify.value = report_item_data.modify !== undefined ? report_item_data.modify : true

    field_locks.title = false
    field_locks.title_prefix = false

    selected_type.value = null
    attribute_groups.value = []
    news_item_aggregates.value = data.news_item_aggregates || []
    remote_report_items.value = data.remote_report_items || []

    report_item.id = data.id
    report_item.uuid = data.uuid
    report_item.title = data.title
    report_item.title_prefix = data.title_prefix
    report_item.report_item_type_id = data.report_item_type_id
    report_item.state_id = data.state_id

    if (!report_types.value || !report_types.value.length) {
      await loadReportTypes()
    }

    for (let i = 0; i < report_types.value.length; i++) {
      if (report_types.value[i].id === report_item.report_item_type_id) {
        selected_type.value = report_types.value[i]

        expand_group_items.value = []
        for (let j = 0; j < selected_type.value.attribute_groups.length; j++) {
          expand_group_items.value.push({
            values: Array.from(Array(selected_type.value.attribute_groups[j].attribute_group_items.length).keys())
          })
        }
        break
      }
    }

    visible.value = true

    // Load locks and populate attribute groups
    const locksResponse = await getReportItemLocks(report_item.id)
    const locks_data = locksResponse.data

    if (locks_data.title !== undefined && locks_data.title !== null) {
      field_locks.title = true
    }
    if (locks_data.title_prefix !== undefined && locks_data.title_prefix !== null) {
      field_locks.title_prefix = true
    }

    if (selected_type.value) {
      for (let i = 0; i < selected_type.value.attribute_groups.length; i++) {
        const group = {
          id: selected_type.value.attribute_groups[i].id,
          title: selected_type.value.attribute_groups[i].title,
          attribute_group_items: []
        }

        for (let j = 0; j < selected_type.value.attribute_groups[i].attribute_group_items.length; j++) {
          const values = []

          // Local attributes
          for (let k = 0; k < data.attributes.length; k++) {
            if (data.attributes[k].attribute_group_item_id === selected_type.value.attribute_groups[i].attribute_group_items[j].id) {
              let value = data.attributes[k].value
              const value_description = data.attributes[k].value_description
              const attrType = selected_type.value.attribute_groups[i].attribute_group_items[j].attribute.type

              if (attrType === 'CPE') {
                value = value.replace('%', '*')
              } else if (attrType === 'BOOLEAN') {
                value = value === 'true'
              }

              const locked =
                locks_data["'" + data.attributes[k].id + "'"] !== undefined && locks_data["'" + data.attributes[k].id + "'"] !== null

              values.push({
                id: data.attributes[k].id,
                index: values.length,
                value: value,
                value_description: value_description,
                binary_mime_type: data.attributes[k].binary_mime_type,
                binary_size: data.attributes[k].binary_size,
                binary_description: data.attributes[k].binary_description,
                last_updated: data.attributes[k].last_updated,
                user: data.attributes[k].user,
                locked: locked,
                remote: false
              })
            }
          }

          // Remote attributes
          for (let l = 0; l < (data.remote_report_items || []).length; l++) {
            for (let k = 0; k < data.remote_report_items[l].attributes.length; k++) {
              if (
                data.remote_report_items[l].attributes[k].attribute_group_item_title ===
                selected_type.value.attribute_groups[i].attribute_group_items[j].title
              ) {
                let value = data.remote_report_items[l].attributes[k].value
                const value_description = data.remote_report_items[l].attributes[k].value_description
                const attrType = selected_type.value.attribute_groups[i].attribute_group_items[j].attribute.type

                if (attrType === 'CPE') {
                  value = value.replace('%', '*')
                } else if (attrType === 'BOOLEAN') {
                  value = value === 'true'
                }

                values.push({
                  id: data.remote_report_items[l].attributes[k].id,
                  index: values.length,
                  value: value,
                  value_description: value_description,
                  last_updated: data.remote_report_items[l].attributes[k].last_updated,
                  binary_mime_type: data.remote_report_items[l].attributes[k].binary_mime_type,
                  binary_size: data.remote_report_items[l].attributes[k].binary_size,
                  binary_description: data.remote_report_items[l].attributes[k].binary_description,
                  user: { name: data.remote_report_items[l].remote_user },
                  locked: false,
                  remote: true
                })
              }
            }
          }

          group.attribute_group_items.push({
            attribute_group_item: selected_type.value.attribute_groups[i].attribute_group_items[j],
            values: values
          })
        }

        attribute_groups.value.push(group)
      }
    }
  } catch (error) {
    console.error('Error loading report item detail:', error)
    show_error.value = true
  }
}

const updateRemoteAttributes = () => {
  for (let i = 0; i < attribute_groups.value.length; i++) {
    for (let j = 0; j < attribute_groups.value[i].attribute_group_items.length; j++) {
      // Remove existing remote attributes
      for (let k = attribute_groups.value[i].attribute_group_items[j].values.length - 1; k >= 0; k--) {
        if (attribute_groups.value[i].attribute_group_items[j].values[k].remote === true) {
          attribute_groups.value[i].attribute_group_items[j].values.splice(k, 1)
        }
      }

      // Add new remote attributes
      for (let l = 0; l < remote_report_items.value.length; l++) {
        for (let k = 0; k < remote_report_items.value[l].attributes.length; k++) {
          if (
            remote_report_items.value[l].attributes[k].attribute_group_item_title ===
            attribute_groups.value[i].attribute_group_items[j].attribute_group_item.title
          ) {
            let value = remote_report_items.value[l].attributes[k].value
            const attrType = attribute_groups.value[i].attribute_group_items[j].attribute_group_item.attribute.type

            if (attrType === 'CPE') {
              value = value.replace('%', '*')
            } else if (attrType === 'BOOLEAN') {
              value = value === 'true'
            }

            attribute_groups.value[i].attribute_group_items[j].values.push({
              id: remote_report_items.value[l].attributes[k].id,
              index: attribute_groups.value[i].attribute_group_items[j].values.length,
              value: value,
              value_description: remote_report_items.value[l].attributes[k].value_description,
              last_updated: remote_report_items.value[l].attributes[k].last_updated,
              binary_mime_type: remote_report_items.value[l].attributes[k].binary_mime_type,
              binary_size: remote_report_items.value[l].attributes[k].binary_size,
              binary_description: remote_report_items.value[l].attributes[k].binary_description,
              user: { name: remote_report_items.value[l].remote_user },
              locked: false,
              remote: true
            })
          }
        }
      }
    }
  }
}

const updateNewsItemAggregates = (items) => {
  news_item_aggregates.value = Array.isArray(items) ? [...items] : []
}

const getAttributeMeta = (attributeItem) => {
  const values = Array.isArray(attributeItem?.values) ? attributeItem.values : []
  let latest = null

  for (const value of values) {
    const userName = value?.user?.name
    if (!userName) continue

    if (!latest) {
      latest = value
      continue
    }

    const currentTime = Date.parse(value?.last_updated || '')
    const latestTime = Date.parse(latest?.last_updated || '')

    if (!Number.isNaN(currentTime) && Number.isNaN(latestTime)) {
      latest = value
    } else if (!Number.isNaN(currentTime) && !Number.isNaN(latestTime) && currentTime > latestTime) {
      latest = value
    }
  }

  if (!latest?.user?.name) return ''
  if (!latest?.last_updated) return latest.user.name

  return `${latest.last_updated} ${latest.user.name}`
}

// AI generation
const autoGenerate = async (attribute_group_item_id) => {
  if (!autoGenerateIcon[attribute_group_item_id]) {
    autoGenerateIcon[attribute_group_item_id] = 'mdi-creation'
  }
  if (autoGenerateIcon[attribute_group_item_id] && autoGenerateIcon[attribute_group_item_id].startsWith('mdi-timer-sand')) {
    return
  }

  setAutoGenerateIcon(attribute_group_item_id, 'wait')
  const news_item_aggregate_ids = news_item_aggregates.value.map((item) => item.id)

  try {
    const response = await aiGenerate(attribute_group_item_id, news_item_aggregate_ids)
    if (response.data.message) {
      if (setAttributeGroupItemValue(attribute_group_item_id, response.data.message)) {
        setAutoGenerateIcon(attribute_group_item_id, '')
        return
      }
    } else {
      setAttributeGroupItemValue(attribute_group_item_id, JSON.stringify(response.data))
    }
    setAutoGenerateIcon(attribute_group_item_id, 'error')
  } catch (error) {
    setAttributeGroupItemValue(attribute_group_item_id, JSON.stringify(error.response?.data || error.message))
    setAutoGenerateIcon(attribute_group_item_id, 'error')
  }
}

const setAttributeGroupItemValue = (attribute_group_item_id, value) => {
  for (let i = 0; i < attribute_groups.value.length; i++) {
    for (let j = 0; j < attribute_groups.value[i].attribute_group_items.length; j++) {
      const item = attribute_groups.value[i].attribute_group_items[j]
      if (item.attribute_group_item.id === attribute_group_item_id) {
        if (item.values.length > 0) {
          item.values[0].value = value
        }
        return true
      }
    }
  }
  return false
}

const setAutoGenerateIcon = (attribute_group_item_id, state) => {
  if (autoGenerateIconTimer[attribute_group_item_id]) {
    clearTimeout(autoGenerateIconTimer[attribute_group_item_id])
    autoGenerateIconTimer[attribute_group_item_id] = null
  }
  if (state === 'wait') {
    const ico = autoGenerateIcon[attribute_group_item_id]
    if (ico === 'mdi-timer-sand') {
      autoGenerateIcon[attribute_group_item_id] = 'mdi-timer-sand-complete'
    } else if (ico === 'mdi-timer-sand-complete') {
      autoGenerateIcon[attribute_group_item_id] = 'mdi-timer-sand-paused'
    } else {
      autoGenerateIcon[attribute_group_item_id] = 'mdi-timer-sand'
    }
    autoGenerateIconTimer[attribute_group_item_id] = setTimeout(() => {
      setAutoGenerateIcon(attribute_group_item_id, state)
    }, 500)
  } else if (state === 'error') {
    autoGenerateIcon[attribute_group_item_id] = 'mdi-exclamation-thick'
  } else {
    autoGenerateIcon[attribute_group_item_id] = 'mdi-creation'
  }
}

const resetAutoGenerate = () => {
  Object.keys(autoGenerateIcon).forEach((key) => delete autoGenerateIcon[key])
  Object.keys(autoGenerateIconTimer).forEach((key) => {
    clearTimeout(autoGenerateIconTimer[key])
    delete autoGenerateIconTimer[key]
  })
}

const loadAvailableStates = async () => {
  try {
    const response = await getEntityTypeStates('report_item')
    available_states.value = response.data.states || []
  } catch (error) {
    console.error('Failed to load available states for REPORT:', error)
    available_states.value = []
  }
}

const selectDefaultState = () => {
  if (!available_states.value || !available_states.value.length) return
  const defaultState = available_states.value.find((state) => state.is_default)
  if (defaultState) {
    report_item.state_id = defaultState.id
  }
}

const loadReportTypes = async () => {
  await analyzeStore.loadReportItemTypes()
  const types = analyzeStore.getReportItemTypes
  report_types.value = types?.items || []
}

const snapshotForm = () => {
  return JSON.stringify({
    report_item: { ...report_item },
    selected_type: selected_type.value,
    news_item_aggregates: news_item_aggregates.value,
    remote_report_items: remote_report_items.value
  })
}

const hasUnsavedChanges = () => {
  if (initialFormState.value !== null) {
    return snapshotForm() !== initialFormState.value
  }
  return false
}

// SSE event handlers for collaborative editing
const reportItemLocked = (data) => {
  if (edit.value === true && report_item.id === data.report_item_id) {
    if (data.user_id !== getUserId()) {
      field_locks[data.field_id] = true
    }
  }
}

const reportItemUnlocked = (data) => {
  if (edit.value === true && report_item.id === data.report_item_id) {
    if (data.user_id !== getUserId()) {
      field_locks[data.field_id] = false
    }
  }
}

const reportItemUpdated = async (data_info) => {
  if (edit.value === true && report_item.id === data_info.report_item_id) {
    if (data_info.user_id !== getUserId()) {
      try {
        const response = await getReportItemData(report_item.id, data_info)
        const data = response.data
        if (data.title !== undefined) {
          report_item.title = data.title
        } else if (data.title_prefix !== undefined) {
          report_item.title_prefix = data.title_prefix
        } else if (data.state_id !== undefined) {
          report_item.state_id = data.state_id
        }
        if (data.update !== undefined) {
          for (let i = 0; i < attribute_groups.value.length; i++) {
            for (let j = 0; j < attribute_groups.value[i].attribute_group_items.length; j++) {
              for (let k = 0; k < attribute_groups.value[i].attribute_group_items[j].values.length; k++) {
                if (attribute_groups.value[i].attribute_group_items[j].values[k].id === data.attribute_id) {
                  attribute_groups.value[i].attribute_group_items[j].values[k].value = data.attribute_value
                  attribute_groups.value[i].attribute_group_items[j].values[k].value_description = data.attribute_value_description
                  return
                }
              }
            }
          }
        }
      } catch (error) {
        console.error('Error updating report item from SSE:', error)
      }
    }
  }
}

const reportItemLockedEvent = (event) => {
  reportItemLocked(event.detail)
}

const reportItemUnlockedEvent = (event) => {
  reportItemUnlocked(event.detail)
}

const reportItemUpdatedEvent = (event) => {
  reportItemUpdated(event.detail)
}

// Watchers
watch(visible, (val) => {
  if (val) {
    document.documentElement.style.overflow = 'hidden'
  } else {
    document.documentElement.style.overflow = 'auto'
  }
})

watch(
  () => route.path,
  () => {
    local_reports.value = !window.location.pathname.includes('/group/')
  }
)

// Lifecycle
onMounted(async () => {
  loadAvailableStates()
  local_reports.value = !window.location.pathname.includes('/group/')
  await loadReportTypes()

  window.addEventListener('report-item-locked', reportItemLockedEvent)
  window.addEventListener('report-item-unlocked', reportItemUnlockedEvent)
  window.addEventListener('report-item-updated', reportItemUpdatedEvent)
})

onUnmounted(() => {
  window.removeEventListener('report-item-locked', reportItemLockedEvent)
  window.removeEventListener('report-item-unlocked', reportItemUnlockedEvent)
  window.removeEventListener('report-item-updated', reportItemUpdatedEvent)
})

// Expose for parent components
defineExpose({
  openDialog: (newsItemAggregates) => {
    initializeNewReportItem(newsItemAggregates || [])
  },
  showDetail,
  initializeNewReportItem
})
</script>

<style scoped>
.taranis-ng-vertical-view {
  position: relative;
}

.locked-style :deep(input) {
  color: grey !important;
  font-style: italic;
}

.attribute-meta {
  font-size: 0.8rem;
  font-weight: 400;
  text-transform: none;
}
</style>
