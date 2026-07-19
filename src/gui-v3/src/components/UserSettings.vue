<template>
    <v-dialog
        v-model="visible"
        max-width="900"
        max-height="90vh"
        scrollable
        @keydown.esc="close"
    >
        <v-card>
            <v-toolbar
                color="primary"
                dark
                density="compact"
            >
                <v-toolbar-title>{{ t('settings.user_settings') }}</v-toolbar-title>
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
                    <v-icon
                        :icon="ICONS.COG"
                        start
                    />
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
                    <v-icon
                        :icon="ICONS.TEXT_BOX_OUTLINE"
                        start
                    />
                    {{ t('settings.tab_wordlists') }}
                </v-tab>

                <!-- Hotkeys Tab -->
                <v-tab value="hotkeys">
                    <v-icon
                        :icon="ICONS.KEYBOARD"
                        start
                    />
                    {{ t('settings.tab_hotkeys') }}
                </v-tab>
            </v-tabs>

            <v-card-text style="height: 70vh; overflow-y: auto">
                <v-window v-model="activeTab">
                    <!-- General Settings -->
                    <v-window-item value="general">
                        <SettingsTable :global-setting="false" />
                    </v-window-item>

                    <!-- Security (TOTP, passkeys) -->
                    <v-window-item value="security">
                        <SecuritySettings :load-trigger="securityLoadTrigger" />
                    </v-window-item>

                    <!-- Word Lists -->
                    <v-window-item value="wordlists">
                        <v-container fluid>
                            <v-data-table
                                v-model="selectedWordLists"
                                :headers="wordListHeaders"
                                :items="wordLists"
                                item-value="id"
                                show-select
                                density="compact"
                            >
                                <template #top>
                                    <v-toolbar
                                        flat
                                        density="compact"
                                    >
                                        <v-toolbar-title>{{ t('assess.tooltip.highlight_wordlist') }}</v-toolbar-title>
                                    </v-toolbar>
                                </template>
                            </v-data-table>
                        </v-container>
                    </v-window-item>

                    <!-- Hotkeys -->
                    <v-window-item value="hotkeys">
                        <v-container fluid>
                            <v-row>
                                <v-col
                                    v-for="shortcut in shortcuts"
                                    :key="shortcut.alias"
                                    cols="12"
                                    sm="6"
                                    md="4"
                                >
                                    <v-btn
                                        block
                                        variant="outlined"
                                        @click="openKeyDialog(shortcut.alias)"
                                    >
                                        <v-icon start>
                                            {{ shortcut.icon }}
                                        </v-icon>
                                        <span
                                            v-if="shortcut.key"
                                            class="text-caption"
                                        >
                                            {{ shortcut.key }}
                                        </span>
                                        <v-icon
                                            v-else
                                            color="error"
                                            >mdi-alert</v-icon
                                        >
                                    </v-btn>
                                    <div class="text-caption text-center mt-1">
                                        {{ t('settings.' + shortcut.alias) }}
                                    </div>
                                </v-col>
                            </v-row>
                            <v-row>
                                <v-col class="text-right">
                                    <v-btn
                                        variant="text"
                                        @click="resetHotkeys"
                                    >
                                        <v-icon start>mdi-reload</v-icon>
                                        {{ t('settings.reset_keys') }}
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </v-container>
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
    const wordListHeaders = [
        { title: 'Name', key: 'name', sortable: true },
        { title: 'Description', key: 'description', sortable: false }
    ]
    const wordLists = ref<WordListItem[]>([])
    const selectedWordLists = ref<Array<number | string>>([])

    // Hotkeys
    const shortcuts = ref<HotkeyItem[]>([
        { alias: 'close_item_1', icon: 'mdi-close', key: 'Escape' },
        { alias: 'close_item_2', icon: 'mdi-close', key: '' },
        { alias: 'close_item_3', icon: 'mdi-close', key: '' },
        { alias: 'collection_up_1', icon: 'mdi-arrow-up', key: 'ArrowUp' },
        { alias: 'collection_up_2', icon: 'mdi-arrow-up', key: 'k' },
        { alias: 'collection_down_1', icon: 'mdi-arrow-down', key: 'ArrowDown' },
        { alias: 'collection_down_2', icon: 'mdi-arrow-down', key: 'j' },
        { alias: 'show_item_1', icon: 'mdi-eye', key: 'Enter' },
        { alias: 'show_item_2', icon: 'mdi-eye', key: 'o' },
        { alias: 'show_item_3', icon: 'mdi-eye', key: '' },
        { alias: 'read_item', icon: 'mdi-email-open', key: 'r' },
        { alias: 'important_item', icon: 'mdi-star', key: 'i' },
        { alias: 'like_item', icon: 'mdi-thumb-up', key: 'l' },
        { alias: 'unlike_item', icon: 'mdi-thumb-down', key: 'u' },
        { alias: 'delete_item', icon: 'mdi-delete', key: 'Delete' },
        { alias: 'selection', icon: 'mdi-checkbox-multiple-marked', key: 's' },
        { alias: 'group', icon: 'mdi-group', key: 'g' },
        { alias: 'ungroup', icon: 'mdi-ungroup', key: '' },
        { alias: 'new_product', icon: 'mdi-plus', key: 'n' }
    ])

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
            await settingsStore.loadUserWordLists()
            const profileWordLists = (settingsStore.getProfileWordLists || []) as WordListItem[]
            wordLists.value = Array.isArray(profileWordLists) ? profileWordLists : []
            selectedWordLists.value = wordLists.value.filter((wl: WordListItem) => wl.selected).map((wl: WordListItem) => wl.id)

            // Load hotkeys
            await settingsStore.loadUserHotkeys()
            const userHotkeys = (settingsStore.getProfileHotkeys || []) as HotkeyItem[]
            if (Array.isArray(userHotkeys) && userHotkeys.length > 0) {
                // Convert to plain array to ensure it's not a Proxy
                shortcuts.value = userHotkeys.map((h: HotkeyItem) => ({
                    alias: h.alias,
                    icon: h.icon,
                    key: h.key
                }))
            }
        } catch (error: unknown) {
            console.error('Error loading user settings:', error)
        }
    }

    const save = async (): Promise<void> => {
        try {
            // Save word lists and hotkeys (general settings are auto-saved by SettingsTable)
            await Promise.all([settingsStore.saveUserWordLists(selectedWordLists.value), settingsStore.saveUserHotkeys(shortcuts.value)])

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
        // Reset to default hotkeys
        shortcuts.value = [
            { alias: 'close_item_1', icon: 'mdi-close', key: 'Escape' },
            { alias: 'close_item_2', icon: 'mdi-close', key: '' },
            { alias: 'close_item_3', icon: 'mdi-close', key: '' },
            { alias: 'collection_up_1', icon: 'mdi-arrow-up', key: 'ArrowUp' },
            { alias: 'collection_up_2', icon: 'mdi-arrow-up', key: 'k' },
            { alias: 'collection_down_1', icon: 'mdi-arrow-down', key: 'ArrowDown' },
            { alias: 'collection_down_2', icon: 'mdi-arrow-down', key: 'j' },
            { alias: 'show_item_1', icon: 'mdi-eye', key: 'Enter' },
            { alias: 'show_item_2', icon: 'mdi-eye', key: 'o' },
            { alias: 'show_item_3', icon: 'mdi-eye', key: '' },
            { alias: 'read_item', icon: 'mdi-email-open', key: 'r' },
            { alias: 'important_item', icon: 'mdi-star', key: 'i' },
            { alias: 'like_item', icon: 'mdi-thumb-up', key: 'l' },
            { alias: 'unlike_item', icon: 'mdi-thumb-down', key: 'u' },
            { alias: 'delete_item', icon: 'mdi-delete', key: 'Delete' },
            { alias: 'selection', icon: 'mdi-checkbox-multiple-marked', key: 's' },
            { alias: 'group', icon: 'mdi-group', key: 'g' },
            { alias: 'ungroup', icon: 'mdi-ungroup', key: '' },
            { alias: 'new_product', icon: 'mdi-plus', key: 'n' }
        ]
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
