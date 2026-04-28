<template>
  <v-data-table
    :headers="headers"
    :items="records"
    :search="search"
    :items-per-page="-1"
    item-key="id"
    :sort-by="[{ key: 'description', order: 'asc' }]"
    density="compact"
    disable-pagination
    hide-default-footer
  >
    <template #top>
      <v-row class="pa-2">
        <v-col cols="12" md="4">
          <div v-if="globalSetting" class="text-h6">
            {{ t('nav_menu.settings') }}
          </div>
        </v-col>
        <v-col cols="12" md="8">
          <v-text-field
            v-model="search"
            :label="t('toolbar_filter.search')"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
            density="compact"
            single-line
            hide-details
            clearable
          />
        </v-col>
      </v-row>
    </template>

    <template #item.value="{ item }">
      <!-- Boolean setting (switch) -->
      <template v-if="item.type === 'B'">
        <v-switch
          :model-value="item.value === 'true'"
          color="primary"
          hide-details
          density="compact"
          @update:model-value="(val) => updateSetting(item, val ? 'true' : 'false')"
        />
      </template>

      <!-- Select with options -->
      <template v-else-if="item.options">
        <v-select
          :model-value="item.value"
          :items="getDisplayOptions(item)"
          item-title="txt"
          item-value="id"
          variant="outlined"
          density="compact"
          hide-details
          @update:model-value="(val) => updateSetting(item, val)"
        />
      </template>

      <!-- Text input with edit dialog -->
      <template v-else>
        <v-chip
          :color="getColor(item.value, item.default_val)"
          label
          clickable
          @click="openEditDialog(item)"
        >
          {{ item.value }}
        </v-chip>
      </template>
    </template>

    <template #item.description="{ item }">
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <span v-bind="props" style="cursor: help">
            {{
              te('settings_enum.' + item.key) ? t('settings_enum.' + item.key) : item.description
            }}
          </span>
        </template>
        {{ t('settings.default_value') }}: {{ item.default_val }}
      </v-tooltip>
    </template>

    <template #item.updated_at="{ item }">
      <span>{{ formatDate(item.updated_at) }}</span>
    </template>
  </v-data-table>

  <!-- Edit Dialog for text values -->
  <v-dialog v-model="editDialog" max-width="500">
    <v-card>
      <v-card-title>{{ t('settings.update_value') }}</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="editValue"
          :label="t('settings.value')"
          :rules="[maxCharsRule]"
          variant="outlined"
          counter="150"
          autofocus
          @keydown.enter="saveEdit"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="editDialog = false">
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn color="primary" variant="text" @click="saveEdit">
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from 'vuetify'
import { useSettingsStore } from '@/stores/settings'
import Settings from '@/services/settings'

const props = defineProps({
  globalSetting: {
    type: Boolean,
    required: true
  }
})

const { t, te, locale } = useI18n()
const theme = useTheme()
const settingsStore = useSettingsStore()

const applyTheme = (themeName) => {
  if (typeof theme.change === 'function') {
    theme.change(themeName)
  } else {
    theme.global.name.value = themeName
  }
}

const search = ref('')
const records = ref([])
const editDialog = ref(false)
const editValue = ref('')
const editItem = ref(null)

const maxCharsRule = (v) => !v || v.length <= 150 || 'Input too long!'

const headers = computed(() => {
  const baseHeaders = [
    { title: t('settings.description'), key: 'description' },
    { title: t('settings.value'), key: 'value', sortable: false }
  ]

  if (props.globalSetting) {
    baseHeaders.push(
      { title: t('settings.updated_by'), key: 'updated_by' },
      { title: t('settings.updated_at'), key: 'updated_at', sortable: true }
    )
  }

  return baseHeaders
})

const getColor = (value, defaultValue) => {
  return value === defaultValue ? 'grey' : 'success'
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  try {
    const date = new Date(dateString)
    // Simple format: YYYY-MM-DD HH:MM:SS
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch (e) {
    return dateString
  }
}

const getDisplayOptions = (item) => {
  try {
    const options = JSON.parse(item.options)

    // For language settings, use language names
    if (item.key === 'UI_LANGUAGE' || item.key === 'CONTENT_DEFAULT_LANGUAGE') {
      return options.map((opt) => ({
        ...opt,
        txt: getLanguageName(opt.id, opt.txt)
      }))
    }

    return options
  } catch (e) {
    return []
  }
}

const getLanguageName = (code, defaultName) => {
  try {
    // Try to use Intl.DisplayNames for multilingual support
    if (typeof Intl !== 'undefined' && Intl.DisplayNames) {
      try {
        const displayNames = new Intl.DisplayNames([locale.value, 'en'], { type: 'language' })
        return displayNames.of(code)
      } catch (e) {
        // Fallback
      }
    }

    // Simple fallback - return default name or code
    return defaultName || code
  } catch (e) {
    return defaultName || code
  }
}

const initRecords = () => {
  const allSettings = settingsStore.getSettings || []
  console.log('[SettingsTable] initRecords - globalSetting:', props.globalSetting)
  console.log('[SettingsTable] initRecords - allSettings:', allSettings)
  console.log('[SettingsTable] initRecords - allSettings.length:', allSettings.length)

  if (!Array.isArray(allSettings)) {
    console.warn('[SettingsTable] allSettings is not an array:', typeof allSettings)
    records.value = []
    return
  }

  const filtered = allSettings.filter((item) => {
    console.log('[SettingsTable] item:', item.key, 'is_global:', item.is_global, 'checking against:', props.globalSetting)
    return item.is_global === props.globalSetting
  })

  console.log('[SettingsTable] filtered records:', filtered.length)
  records.value = filtered
}

const validateValue = (item, value) => {
  let val = value.trim()

  if (item.type === 'B') {
    val = val.toLowerCase()
    if (val !== 'true' && val !== 'false') {
      throw new Error(t('settings.boolean_error'))
    }
  } else if (item.type === 'I') {
    const numVal = Number(val)
    if (isNaN(numVal) || !Number.isInteger(numVal)) {
      throw new Error(t('settings.integer_error'))
    }
  } else if (item.type === 'N') {
    const numVal = Number(val)
    if (isNaN(numVal) || !isFinite(numVal)) {
      throw new Error(t('settings.decimal_error'))
    }
  }

  return String(val)
}

const updateSetting = async (item, value) => {
  try {
    const validatedValue = validateValue(item, value)
    const settingData = {
      ...item,
      value: validatedValue
    }

    await settingsStore.saveSettings({ data: settingData, is_global: props.globalSetting })
    initRecords()

    // Apply special settings immediately
    if (item.key === 'DARK_THEME') {
      applyTheme(validatedValue === 'true' ? 'dark' : 'light')
    } else if (item.key === 'UI_LANGUAGE') {
      locale.value = validatedValue
    } else if (item.key === 'SPELLCHECK') {
      settingsStore.spellcheck = validatedValue === 'true'
    }

    // Show success notification
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'success', loc: 'settings.successful_edit' }
      })
    )
  } catch (error) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'settings.error' }
      })
    )
  }
}

const openEditDialog = (item) => {
  editItem.value = item
  editValue.value = item.value
  editDialog.value = true
}

const saveEdit = () => {
  if (editItem.value && editValue.value !== null) {
    updateSetting(editItem.value, editValue.value)
  }
  editDialog.value = false
}

onMounted(async () => {
  await settingsStore.loadSettings({ search: '' })
  initRecords()
})

// Re-filter records whenever globalSetting prop changes
watch(() => props.globalSetting, () => {
  console.log('[SettingsTable] globalSetting changed, re-filtering records')
  initRecords()
})
</script>

<style scoped>
.wrap-text-cell {
  white-space: normal;
  word-wrap: break-word;
  word-break: break-word;
}
</style>
