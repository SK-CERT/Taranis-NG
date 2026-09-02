<template>
    <!-- Application Settings uses the same card + toolbar layout as the Access
         Management tabs. Inside the User Settings dialog (globalSetting = false) the
         wrapper stays flat/padding-free so it doesn't nest a card in a card. -->
    <v-container
        fluid
        :class="{ 'pa-0': !globalSetting }"
    >
        <v-card :flat="!globalSetting">
            <!-- Toolbar -->
            <v-card-text>
                <v-row class="settings-search-row">
                    <v-col
                        cols="12"
                        md="7"
                    >
                        <SearchField
                            v-model="search"
                            :width="350"
                        />
                    </v-col>
                </v-row>
            </v-card-text>

            <v-data-table
                :headers="headers"
                :items="records"
                :search="search"
                :items-per-page="-1"
                item-key="id"
                :sort-by="globalSetting ? [{ key: 'description', order: 'asc' }] : []"
                density="compact"
                hide-default-footer
                class="settings-table"
                :class="{ 'elevation-1': globalSetting, 'settings-table--personal': !globalSetting }"
            >
                <template #item.value="{ item }">
                    <!-- Boolean setting (switch) -->
                    <template v-if="item.type === 'B'">
                        <v-switch
                            :model-value="item.value === 'true'"
                            color="primary"
                            hide-details
                            density="compact"
                            :disabled="!canEditSettings"
                            @update:model-value="(val) => updateSetting(item, val ? 'true' : 'false')"
                        />
                    </template>

                    <!-- Select with options -->
                    <template v-else-if="item.key === Settings.UI_LANGUAGE || item.options">
                        <v-select
                            :model-value="item.value"
                            :items="getDisplayOptions(item)"
                            item-title="txt"
                            item-value="id"
                            variant="outlined"
                            density="compact"
                            hide-details
                            :prepend-inner-icon="getSelectIcon(item)"
                            :disabled="!canEditSettings"
                            @update:model-value="(val) => updateSetting(item, val)"
                        />
                    </template>

                    <!-- Text input with edit dialog -->
                    <template v-else>
                        <v-chip
                            :color="getColor(item.value, item.default_val)"
                            label
                            :clickable="canEditSettings"
                            @click="openEditDialog(item)"
                        >
                            {{ item.value }}
                        </v-chip>
                    </template>
                </template>

                <template #item.description="{ item }">
                    <div :class="{ 'setting-label': !globalSetting }">
                        <span
                            v-if="!globalSetting"
                            class="setting-label__icon"
                        >
                            <v-icon size="20">{{ getSettingIcon(item.key) }}</v-icon>
                        </span>
                        <span
                            class="setting-label__text"
                            style="cursor: help"
                            :title="formatDefaultValue(item.default_val)"
                        >
                            {{ te('settings_enum.' + item.key) ? t('settings_enum.' + item.key) : item.description }}
                        </span>
                    </div>
                </template>

                <template #item.updated_at="{ item }">
                    <span>{{ formatDate(item.updated_at) }}</span>
                </template>
            </v-data-table>
        </v-card>
    </v-container>

    <!-- Edit Dialog for text values -->
    <v-dialog
        v-model="editDialog"
        max-width="500"
    >
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
                <v-btn
                    variant="text"
                    @click="editDialog = false"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    v-if="canEditSettings"
                    color="primary"
                    variant="text"
                    @click="saveEdit"
                >
                    {{ t('common.save') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useTheme } from 'vuetify'
    import { useAuth } from '@/composables/useAuth'
    import { useSettingsStore } from '@/stores/settings'
    import { supportedLocales } from '@/i18n'
    import { Settings, type SettingKey } from '@/types/settings'
    import SearchField from '@/components/common/SearchField.vue'
    import { format } from 'date-fns'

    type SettingType = 'B' | 'I' | 'N' | 'S'

    type SettingOption = {
        id: string | number
        txt: string
        [key: string]: unknown
    }

    type SettingsRecord = {
        id?: string | number
        key: SettingKey
        value: string
        type?: SettingType
        description?: string
        default_val?: string
        updated_by?: string
        updated_at?: string
        options?: string
        is_global?: boolean
        [key: string]: unknown
    }

    type HeaderEntry = {
        title: string
        key: string
        sortable?: boolean
    }

    const props = defineProps<{
        globalSetting: boolean
    }>()

    const { t, te, locale } = useI18n()
    const theme = useTheme()
    const { checkPermission } = useAuth()
    const settingsStore = useSettingsStore()

    const applyTheme = (themeName: string): void => {
        if (typeof theme.change === 'function') {
            theme.change(themeName)
        } else {
            theme.global.name.value = themeName
        }
    }

    const search = ref('')
    let date_format: string
    const records = ref<SettingsRecord[]>([])
    const editDialog = ref(false)
    const editValue = ref('')
    const editItem = ref<SettingsRecord | null>(null)
    const canEditSettings = computed(() => !props.globalSetting || checkPermission('CONFIG_SETTINGS_UPDATE'))

    const MAX_SETTING_VALUE_LENGTH = 150
    const FIRST_STRONG_ISOLATE = '\u2068'
    const LEFT_TO_RIGHT_ISOLATE = '\u2066'
    const POP_DIRECTIONAL_ISOLATE = '\u2069'

    const isolateAuto = (value: unknown): string => `${FIRST_STRONG_ISOLATE}${String(value ?? '')}${POP_DIRECTIONAL_ISOLATE}`
    const isolateLtr = (value: unknown): string => `${LEFT_TO_RIGHT_ISOLATE}${String(value ?? '')}${POP_DIRECTIONAL_ISOLATE}`

    const formatDefaultValue = (value?: string): string => t('settings.default_value_with_value', { value: isolateAuto(value) })

    const maxCharsRule = (value: string | null | undefined): true | string =>
        !value ||
        value.length <= MAX_SETTING_VALUE_LENGTH ||
        t('settings.input_too_long', { count: value.length, max: MAX_SETTING_VALUE_LENGTH })

    const headers = computed<HeaderEntry[]>(() => {
        const baseHeaders: HeaderEntry[] = [
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

    const getColor = (value: string, defaultValue?: string): string => {
        return value === defaultValue ? 'grey' : 'success'
    }

    const settingIcons: Record<SettingKey, string> = {
        [Settings.DATE_FORMAT]: 'mdi-calendar-range',
        [Settings.REPORT_SELECTOR_READ_ONLY]: 'mdi-eye-lock-outline',
        [Settings.TIME_FORMAT]: 'mdi-clock-outline',
        [Settings.CASCADE_STATES_ENABLED]: 'mdi-state-machine',
        [Settings.ATTRIBUTE_EXTRACTION_ENABLED]: 'mdi-regex',
        [Settings.CONTENT_DEFAULT_LANGUAGE]: 'mdi-file-document-edit-outline',
        [Settings.DARK_THEME]: 'mdi-theme-light-dark',
        [Settings.HOTKEYS]: 'mdi-keyboard-outline',
        [Settings.SPELLCHECK]: 'mdi-spellcheck',
        [Settings.TAG_COLOR]: 'mdi-palette-outline',
        [Settings.UI_LANGUAGE]: 'mdi-web'
    }

    const getSettingIcon = (key: SettingKey): string => settingIcons[key] || 'mdi-tune-variant'

    const getSelectIcon = (item: SettingsRecord): string | undefined => {
        if (item.key === Settings.UI_LANGUAGE) return 'mdi-web'
        if (item.key === Settings.CONTENT_DEFAULT_LANGUAGE) return 'mdi-translate'
        return undefined
    }

    const formatDate = (dateString?: string): string => {
        if (!dateString) return ''
        try {
            const date = new Date(dateString)
            return format(date, date_format)
        } catch {
            return dateString
        }
    }

    const getDisplayOptions = (item: SettingsRecord): SettingOption[] => {
        if (item.key === Settings.UI_LANGUAGE) {
            return supportedLocales.map((code) => ({
                id: code,
                txt: t('settings.language_name_with_code', {
                    name: isolateAuto(getLanguageName(code, undefined, true)),
                    code: isolateLtr(code)
                })
            }))
        }

        try {
            const options = JSON.parse(item.options || '[]') as SettingOption[]

            // Content languages remain configured by the backend.
            if (item.key === Settings.CONTENT_DEFAULT_LANGUAGE) {
                return options.map((opt) => ({
                    ...opt,
                    txt: getLanguageName(String(opt.id), opt.txt)
                }))
            }

            return options
        } catch {
            return []
        }
    }

    const getLanguageName = (code: string, defaultName?: string, native = false): string => {
        try {
            // Try to use Intl.DisplayNames for multilingual support
            if (typeof Intl !== 'undefined' && Intl.DisplayNames) {
                try {
                    const displayNames = new Intl.DisplayNames(native ? [code, 'en'] : [locale.value, 'en'], { type: 'language' })
                    return displayNames.of(code) || defaultName || code
                } catch {
                    // Fallback
                }
            }

            // Simple fallback - return default name or code
            return defaultName || code
        } catch {
            return defaultName || code
        }
    }

    const initRecords = (): void => {
        const allSettings = settingsStore.getSettings || []

        if (!Array.isArray(allSettings)) {
            console.warn('[SettingsTable] allSettings is not an array:', typeof allSettings)
            records.value = []
            return
        }
        date_format = settingsStore.getDateTimeFormat

        const settingsRecords = allSettings as SettingsRecord[]
        const filtered = settingsRecords.filter((item) => {
            const settingsItem = item as SettingsRecord
            if (!props.globalSetting && settingsItem.key === Settings.TAG_COLOR) return false
            return settingsItem.is_global === props.globalSetting
        })

        if (props.globalSetting) {
            records.value = filtered as SettingsRecord[]
            return
        }

        const personalSettingOrder: Partial<Record<SettingKey, number>> = {
            [Settings.UI_LANGUAGE]: 0,
            [Settings.CONTENT_DEFAULT_LANGUAGE]: 1
        }

        records.value = [...filtered].sort((left, right) => {
            const priorityDifference = (personalSettingOrder[left.key] ?? 10) - (personalSettingOrder[right.key] ?? 10)
            if (priorityDifference !== 0) return priorityDifference

            const leftLabel = te('settings_enum.' + left.key) ? t('settings_enum.' + left.key) : left.description || ''
            const rightLabel = te('settings_enum.' + right.key) ? t('settings_enum.' + right.key) : right.description || ''
            return leftLabel.localeCompare(rightLabel, locale.value)
        })
    }

    const validateValue = (item: SettingsRecord, value: string): string => {
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

    const updateSetting = async (item: SettingsRecord, value: string): Promise<void> => {
        if (!canEditSettings.value) return
        try {
            const validatedValue = validateValue(item, value)
            const settingData = {
                ...item,
                value: validatedValue
            }

            await settingsStore.saveSettings({ data: settingData, is_global: props.globalSetting })
            initRecords()

            // Apply special settings immediately
            if (item.key === Settings.DARK_THEME) {
                applyTheme(validatedValue === 'true' ? 'dark' : 'light')
            } else if (item.key === Settings.UI_LANGUAGE) {
                locale.value = validatedValue
            } else if (item.key === Settings.SPELLCHECK) {
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

    const openEditDialog = (item: SettingsRecord): void => {
        if (!canEditSettings.value) return
        editItem.value = item
        editValue.value = item.value
        editDialog.value = true
    }

    const saveEdit = (): void => {
        if (!canEditSettings.value) return
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
    watch(
        () => props.globalSetting,
        () => {
            initRecords()
        }
    )
</script>

<style scoped>
    .settings-search-row {
        margin-bottom: 0.25rem;
    }

    .settings-table--personal {
        overflow: hidden;
        border: 1px solid var(--review-panel-border);
        border-radius: 5px;
        background: rgb(var(--v-theme-surface));
        box-shadow: 0 4px 14px rgba(16, 43, 67, 0.1);
    }

    .settings-table--personal :deep(thead) {
        background: rgba(var(--v-theme-surface-variant), 0.42);
    }

    .settings-table--personal :deep(th) {
        height: 44px;
        font-weight: 700;
    }

    .settings-table--personal :deep(td) {
        height: 66px;
        padding-block: 0.55rem;
        border-bottom-color: var(--review-list-border) !important;
    }

    .settings-table--personal :deep(td:last-child) {
        width: 42%;
    }

    .settings-table--personal :deep(.v-select) {
        width: min(100%, 330px);
    }

    .setting-label {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        min-width: 0;
    }

    .setting-label__icon {
        display: grid;
        width: 36px;
        height: 36px;
        flex: 0 0 36px;
        place-items: center;
        border: 1px solid rgba(var(--v-theme-primary), 0.2);
        border-radius: 4px;
        background: rgba(var(--v-theme-primary), 0.08);
        color: rgb(var(--v-theme-primary));
    }

    .setting-label__text {
        min-width: 0;
        font-weight: 550;
    }

    .wrap-text-cell {
        white-space: normal;
        word-wrap: break-word;
        word-break: break-word;
    }

    @media (max-width: 700px) {
        .settings-table--personal :deep(td:last-child) {
            width: 48%;
        }

        .setting-label {
            gap: 0.5rem;
        }
    }
</style>
