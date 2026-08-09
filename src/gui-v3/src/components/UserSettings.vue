<template>
    <v-dialog
        v-model="visible"
        max-width="980"
        max-height="90vh"
        scrollable
        @keydown.esc="close"
    >
        <v-card class="user-settings-dialog">
            <v-toolbar
                color="primary"
                dark
                density="comfortable"
            >
                <v-toolbar-title class="user-settings-dialog__title">
                    <v-icon size="23">mdi-account-cog-outline</v-icon>
                    <span>{{ t('settings.user_settings') }}</span>
                </v-toolbar-title>
                <v-spacer />
                <v-btn
                    variant="text"
                    @click="close"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    variant="text"
                    @click="save"
                >
                    <v-icon start>mdi-content-save</v-icon>
                    {{ t('common.save') }}
                </v-btn>
            </v-toolbar>

            <v-tabs
                v-model="activeTab"
                grow
                color="primary"
            >
                <!-- General Tab -->
                <v-tab value="general">
                    <v-icon start>mdi-tune-variant</v-icon>
                    {{ t('settings.tab_general') }}
                </v-tab>

                <!-- Security Tab -->
                <v-tab value="security">
                    <v-icon
                        :icon="ICONS.SHIELD_LOCK"
                        start
                    />
                    {{ t('settings.tab_security') }}
                </v-tab>

                <!-- Word Lists Tab -->
                <v-tab value="wordlists">
                    <v-icon start>mdi-format-list-bulleted</v-icon>
                    {{ t('settings.tab_wordlists') }}
                </v-tab>

                <!-- Hotkeys Tab -->
                <v-tab value="hotkeys">
                    <v-icon start>mdi-keyboard-outline</v-icon>
                    {{ t('settings.tab_hotkeys') }}
                </v-tab>
            </v-tabs>

            <v-card-text class="user-settings-dialog__content">
                <v-window v-model="activeTab">
                    <!-- General Settings -->
                    <v-window-item value="general">
                        <SettingsTable :global-setting="false" />
                    </v-window-item>

                    <!-- Security (TOTP, passkeys) -->
                    <v-window-item value="security">
                        <SecuritySettings
                            v-if="activeTab === 'security'"
                            :load-trigger="securityLoadTrigger"
                        />
                    </v-window-item>

                    <!-- Word Lists -->
                    <v-window-item value="wordlists">
                        <section class="settings-pane">
                            <header class="settings-pane__header">
                                <span class="settings-pane__icon">
                                    <v-icon>mdi-format-list-checks</v-icon>
                                </span>
                                <div>
                                    <h2>{{ t('settings.tab_wordlists') }}</h2>
                                    <p>{{ t('assess.tooltip.highlight_wordlist') }}</p>
                                </div>
                            </header>
                            <v-data-table
                                v-model="selectedWordLists"
                                :headers="wordListHeaders"
                                :items="wordLists"
                                item-value="id"
                                show-select
                                density="comfortable"
                                :items-per-page="-1"
                                hide-default-footer
                                class="settings-subtable"
                            >
                                <template #no-data>
                                    <div class="settings-empty-state">
                                        <v-icon size="32">mdi-format-list-bulleted-square</v-icon>
                                        <span>{{ t('common.no_data') }}</span>
                                    </div>
                                </template>
                            </v-data-table>
                        </section>
                    </v-window-item>

                    <!-- Hotkeys -->
                    <v-window-item value="hotkeys">
                        <section class="settings-pane">
                            <header class="settings-pane__header settings-pane__header--actions">
                                <div class="settings-pane__heading">
                                    <span class="settings-pane__icon">
                                        <v-icon>mdi-keyboard-settings-outline</v-icon>
                                    </span>
                                    <h2>{{ t('settings.tab_hotkeys') }}</h2>
                                </div>
                                <v-btn
                                    size="small"
                                    variant="tonal"
                                    @click="resetHotkeys"
                                >
                                    <v-icon start>mdi-reload</v-icon>
                                    {{ t('settings.reset_keys') }}
                                </v-btn>
                            </header>
                            <v-row class="hotkey-grid">
                                <v-col
                                    v-for="shortcut in shortcuts"
                                    :key="shortcut.alias"
                                    cols="12"
                                    sm="6"
                                    md="4"
                                >
                                    <button
                                        class="hotkey-card"
                                        type="button"
                                        @click="openKeyDialog(shortcut.alias)"
                                    >
                                        <span class="hotkey-card__icon">
                                            <v-icon size="20">
                                                {{ shortcut.icon }}
                                            </v-icon>
                                        </span>
                                        <span class="hotkey-card__label">
                                            {{ t('settings.' + shortcut.alias) }}
                                        </span>
                                        <kbd
                                            v-if="shortcut.key"
                                            class="hotkey-card__key"
                                        >
                                            {{ shortcut.key }}
                                        </kbd>
                                        <v-icon
                                            v-else
                                            class="hotkey-card__missing"
                                            color="error"
                                            size="20"
                                        >
                                            mdi-alert
                                        </v-icon>
                                    </button>
                                </v-col>
                            </v-row>
                        </section>
                    </v-window-item>
                </v-window>
            </v-card-text>
        </v-card>

        <!-- Press Key Dialog -->
        <v-dialog
            v-model="keyDialogVisible"
            max-width="300"
            persistent
            @keydown="handleKeyPress"
        >
            <v-card
                color="primary"
                dark
            >
                <v-card-text class="white--text">
                    {{ t('settings.press_key') }}
                    <strong>{{ t('settings.' + currentHotkeyAlias) }}</strong>
                    <v-progress-linear
                        indeterminate
                        color="white"
                        class="mb-0"
                    />
                </v-card-text>
            </v-card>
        </v-dialog>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSettingsStore } from '@/stores/settings'
    import { ICONS } from '@/config/ui-constants'
    import SettingsTable from './config/SettingsTable.vue'
    import SecuritySettings from './SecuritySettings.vue'

    type HotkeyItem = {
        alias: string
        icon: string
        key: string
    }

    type WordListItem = {
        id: number | string
        name?: string
        description?: string
        selected?: boolean
        [key: string]: unknown
    }

    type KeyboardEventLike = {
        preventDefault: () => void
        key: string
    }

    const props = defineProps<{
        modelValue: boolean
    }>()

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
    }>()

    const { t } = useI18n()
    const settingsStore = useSettingsStore()

    const activeTab = ref<'general' | 'security' | 'wordlists' | 'hotkeys'>('general')
    const keyDialogVisible = ref<boolean>(false)
    const currentHotkeyAlias = ref<string>('')
    // Bumped whenever the Security tab becomes visible so SecuritySettings
    // reloads its TOTP/passkey state (mirrors the old dialog-open behavior).
    const securityLoadTrigger = ref<number>(0)

    // Word lists
    const wordListHeaders = computed(() => [
        { title: t('word_lists.name'), key: 'name', sortable: true },
        { title: t('word_lists.description'), key: 'description', sortable: false }
    ])
    const wordLists = ref<WordListItem[]>([])
    const selectedWordLists = ref<Array<number | string>>([])

    // Hotkeys
    const shortcuts = ref<HotkeyItem[]>([])

    const visible = computed<boolean>({
        get: () => props.modelValue,
        set: (value: boolean) => emit('update:modelValue', value)
    })

    const close = (): void => {
        visible.value = false
    }

    const loadSettings = async (): Promise<void> => {
        try {
            // Load word lists
            await Promise.all([settingsStore.loadUserWordLists(), settingsStore.loadAvailableWordLists({ search: '' })])
            const profileWordLists = (settingsStore.getProfileWordLists || []) as WordListItem[]
            const availableWordLists = (settingsStore.getAvailableWordListsComputed || []) as WordListItem[]
            wordLists.value = Array.isArray(availableWordLists) ? availableWordLists : []
            selectedWordLists.value = Array.isArray(profileWordLists) ? profileWordLists.map((wordList) => wordList.id) : []

            // Load hotkeys
            await settingsStore.loadUserHotkeys()
            getProfileHotkeys()
        } catch (error: unknown) {
            console.error('Error loading user settings:', error)
        }
    }

    const getProfileHotkeys = async (): Promise<void> => {
        const userHotkeys = (settingsStore.getProfileHotkeys || []) as HotkeyItem[]
        if (Array.isArray(userHotkeys) && userHotkeys.length > 0) {
            // Convert to plain array to ensure it's not a Proxy
            shortcuts.value = userHotkeys.map((h: HotkeyItem) => ({
                alias: h.alias,
                icon: h.icon,
                key: h.key
            }))
        }
    }

    const save = async (): Promise<void> => {
        try {
            // Save word lists and hotkeys (general settings are auto-saved by SettingsTable)
            const selectedLists = selectedWordLists.value.map((id) => ({ id }))
            await Promise.all([settingsStore.saveUserWordLists(selectedLists), settingsStore.saveUserHotkeys(shortcuts.value)])

            close()
        } catch (error: unknown) {
            console.error('Error saving user settings:', error)
        }
    }

    const openKeyDialog = (alias: string): void => {
        currentHotkeyAlias.value = alias
        keyDialogVisible.value = true
    }

    const handleKeyPress = (event: KeyboardEventLike): void => {
        event.preventDefault()
        const key = event.key

        // Ensure shortcuts is an array
        if (!Array.isArray(shortcuts.value)) {
            console.error('shortcuts.value is not an array:', shortcuts.value)
            keyDialogVisible.value = false
            return
        }

        const shortcut = shortcuts.value.find((s: HotkeyItem) => s && s.alias === currentHotkeyAlias.value)
        if (shortcut) {
            shortcut.key = key
        }
        keyDialogVisible.value = false
    }

    const resetHotkeys = (): void => {
        settingsStore.resetHotkeys()
        getProfileHotkeys()
    }

    // Load settings when dialog opens
    watch(visible, (newValue: boolean) => {
        if (newValue) {
            loadSettings()
        }
    })

    // Reload Security tab data whenever it becomes active
    watch(activeTab, (tab) => {
        if (tab === 'security') {
            securityLoadTrigger.value++
        }
    })
</script>

<style scoped>
    .user-settings-dialog {
        border: 1px solid var(--review-panel-border);
        border-radius: 6px;
        box-shadow: 0 16px 44px rgba(5, 24, 40, 0.28);
    }

    .user-settings-dialog__title {
        font-weight: 700;
    }

    .user-settings-dialog__title :deep(.v-toolbar-title__placeholder) {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .user-settings-dialog :deep(.v-tabs) {
        min-height: 58px;
        padding-inline: 0.75rem;
        border-bottom: 1px solid var(--review-panel-border);
        background: rgba(var(--v-theme-surface-variant), 0.28);
    }

    .user-settings-dialog :deep(.v-tab) {
        min-height: 58px;
        letter-spacing: 0.01em;
        text-transform: none;
    }

    .user-settings-dialog__content {
        max-height: 70vh;
        padding: 1.25rem 1.4rem 1.5rem;
        overflow-y: auto;
        background: var(--review-workspace);
    }

    .settings-pane {
        overflow: hidden;
        border: 1px solid var(--review-panel-border);
        border-radius: 5px;
        background: rgb(var(--v-theme-surface));
        box-shadow: 0 4px 14px rgba(16, 43, 67, 0.1);
    }

    .settings-pane__header {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        min-height: 72px;
        padding: 0.8rem 1rem;
        border-bottom: 1px solid var(--review-panel-border);
        background: rgba(var(--v-theme-surface-variant), 0.32);
    }

    .settings-pane__header--actions {
        justify-content: space-between;
    }

    .settings-pane__heading {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }

    .settings-pane__icon {
        display: grid;
        width: 38px;
        height: 38px;
        flex: 0 0 38px;
        place-items: center;
        border: 1px solid rgba(var(--v-theme-primary), 0.22);
        border-radius: 4px;
        background: rgba(var(--v-theme-primary), 0.09);
        color: rgb(var(--v-theme-primary));
    }

    .settings-pane h2,
    .settings-pane p {
        margin: 0;
    }

    .settings-pane h2 {
        font-size: 1rem;
    }

    .settings-pane p {
        margin-top: 0.15rem;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.78rem;
    }

    .settings-subtable :deep(thead) {
        background: rgba(var(--v-theme-surface-variant), 0.2);
    }

    .settings-empty-state {
        display: flex;
        min-height: 150px;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.55rem;
        color: rgba(var(--v-theme-on-surface), 0.52);
    }

    .hotkey-grid {
        padding: 0.6rem;
    }

    .hotkey-grid :deep(.v-col) {
        padding: 0.35rem;
    }

    .hotkey-card {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        width: 100%;
        min-height: 56px;
        padding: 0.45rem 0.55rem;
        gap: 0.65rem;
        border: 1px solid var(--review-list-border);
        border-radius: 4px;
        background: var(--review-list-row);
        color: rgb(var(--v-theme-on-surface));
        cursor: pointer;
        text-align: left;
    }

    .hotkey-card:hover,
    .hotkey-card:focus-visible {
        border-color: rgba(var(--v-theme-primary), 0.62);
        background: var(--review-list-row-hover);
        outline: 2px solid rgba(var(--v-theme-primary), 0.18);
    }

    .hotkey-card__icon {
        display: grid;
        width: 32px;
        height: 32px;
        place-items: center;
        border-radius: 3px;
        background: rgba(var(--v-theme-primary), 0.08);
        color: rgb(var(--v-theme-primary));
    }

    .hotkey-card__label {
        overflow: hidden;
        font-size: 0.78rem;
        font-weight: 600;
        line-height: 1.25;
        text-overflow: ellipsis;
    }

    .hotkey-card__key {
        min-width: 2rem;
        padding: 0.22rem 0.42rem;
        border: 1px solid rgba(var(--v-theme-outline), 0.38);
        border-bottom-width: 2px;
        border-radius: 3px;
        background: rgba(var(--v-theme-surface-variant), 0.52);
        color: rgb(var(--v-theme-on-surface));
        font-family: inherit;
        font-size: 0.72rem;
        font-weight: 700;
        text-align: center;
    }

    .hotkey-card__missing {
        justify-self: center;
    }

    @media (max-width: 700px) {
        .user-settings-dialog__content {
            padding: 0.75rem;
        }

        .user-settings-dialog :deep(.v-tab) {
            min-width: 0;
            padding-inline: 0.6rem;
        }
    }
</style>
