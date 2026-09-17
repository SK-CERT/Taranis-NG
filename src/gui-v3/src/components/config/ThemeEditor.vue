<template>
    <section class="settings-pane theme-editor">
        <header class="settings-pane__header settings-pane__header--actions">
            <v-btn-toggle
                :model-value="editingDark ? 'dark' : 'light'"
                mandatory
                density="compact"
                variant="outlined"
                divided
                @update:model-value="(value) => setVariant(value === 'dark')"
            >
                <v-btn
                    value="light"
                    size="small"
                >
                    <v-icon start>mdi-white-balance-sunny</v-icon>
                    {{ t('theme_editor.light') }}
                </v-btn>
                <v-btn
                    value="dark"
                    size="small"
                >
                    <v-icon start>mdi-weather-night</v-icon>
                    {{ t('theme_editor.dark') }}
                </v-btn>
            </v-btn-toggle>

            <div class="theme-editor__actions">
                <!-- Both actions carry their own colour: a live preview lets the
                     user turn the text colour unreadable, and the way out of that
                     must not be the thing that disappears. -->
                <v-btn
                    size="small"
                    variant="flat"
                    color="warning"
                    :disabled="!isDirty"
                    @click="reset"
                >
                    <v-icon start>mdi-restore</v-icon>
                    {{ t('theme_editor.reset') }}
                </v-btn>
                <v-btn
                    size="small"
                    color="primary"
                    variant="flat"
                    :loading="saving"
                    @click="save"
                >
                    <v-icon start>mdi-content-save</v-icon>
                    {{ t('common.save') }}
                </v-btn>
            </div>
        </header>

        <div class="theme-editor__body">
            <v-alert
                v-if="!isCustomActive"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-4"
                :text="t('theme_editor.not_active')"
            />

            <div
                v-for="group in TOKEN_GROUPS"
                :key="group"
                class="theme-editor__group"
            >
                <h3 class="theme-editor__group-title">{{ t('theme_editor.groups.' + group) }}</h3>
                <div class="theme-editor__grid">
                    <div
                        v-for="token in tokensByGroup[group]"
                        :key="token.key"
                        class="token"
                        :class="{ 'token--modified': isModified(token.key) }"
                    >
                        <v-menu
                            :close-on-content-click="false"
                            location="bottom start"
                        >
                            <template #activator="{ props: menuProps }">
                                <button
                                    v-bind="menuProps"
                                    type="button"
                                    class="token__swatch"
                                    :style="{ background: values[token.key] }"
                                    :aria-label="t('theme_editor.tokens.' + token.key)"
                                />
                            </template>
                            <v-color-picker
                                :model-value="values[token.key]"
                                :mode="token.allowsAlpha ? 'hexa' : 'hex'"
                                :modes="token.allowsAlpha ? ['hexa'] : ['hex']"
                                show-swatches
                                swatches-max-height="180"
                                @update:model-value="(value) => setToken(token.key, value)"
                            />
                        </v-menu>

                        <div class="token__body">
                            <span class="token__name">{{ t('theme_editor.tokens.' + token.key) }}</span>
                            <span
                                v-if="warnings[token.key]"
                                class="token__warning"
                            >
                                <v-icon size="13">mdi-alert-outline</v-icon>
                                {{ warnings[token.key] }}
                            </span>
                            <span
                                v-else
                                class="token__value"
                                >{{ values[token.key] }}</span
                            >
                        </div>

                        <v-btn
                            class="token__reset"
                            icon="mdi-restore"
                            size="x-small"
                            variant="text"
                            density="comfortable"
                            :disabled="!isModified(token.key)"
                            :aria-label="t('theme_editor.reset')"
                            @click="resetToken(token.key)"
                        />
                    </div>
                </div>
            </div>
        </div>
    </section>
</template>

<script setup lang="ts">
    import { computed, onBeforeUnmount, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSettingsStore } from '@/stores/settings'
    import { useAppTheme } from '@/composables/useAppTheme'
    import { Settings } from '@/types/settings'
    import {
        CUSTOM_THEME_FAMILY,
        EDITABLE_TOKENS,
        TOKEN_GROUPS,
        cloneCustomTheme,
        parseCustomTheme,
        readBasedOn,
        serializeCustomTheme,
        type CustomThemeData,
        type TokenGroup
    } from '@/themes/custom'
    import { AAA_BODY_TEXT, AA_TEXT, contrastRatio } from '@/themes/wcag'

    const props = withDefaults(
        defineProps<{
            // Bumped by the settings dialog when this tab becomes visible, so the
            // editor re-reads the saved theme (mirrors SecuritySettings).
            loadTrigger?: number
        }>(),
        { loadTrigger: 0 }
    )

    const { t } = useI18n()
    const settingsStore = useSettingsStore()
    const { family, isDark, installCustomTheme, customThemeSeed, previewVariant } = useAppTheme()

    const editingDark = ref(false)
    const saving = ref(false)
    const theme = ref<CustomThemeData>(customThemeSeed())
    // What is currently persisted, so closing without saving can put it back.
    const saved = ref<CustomThemeData>(customThemeSeed())
    // The untouched palette of the family this theme is based on: what both the
    // per-colour and the whole-theme reset return to.
    const seed = ref<CustomThemeData>(customThemeSeed())

    const tokensByGroup = computed(
        () =>
            Object.fromEntries(TOKEN_GROUPS.map((group) => [group, EDITABLE_TOKENS.filter((token) => token.group === group)])) as Record<
                TokenGroup,
                typeof EDITABLE_TOKENS
            >
    )

    const values = computed<Record<string, string>>(() => (editingDark.value ? theme.value.dark : theme.value.light))
    const seedValues = computed<Record<string, string>>(() => (editingDark.value ? seed.value.dark : seed.value.light))

    const isModified = (key: string): boolean => values.value[key] !== seedValues.value[key]

    const isDirty = computed(() =>
        EDITABLE_TOKENS.some(
            (token) =>
                theme.value.light[token.key] !== seed.value.light[token.key] || theme.value.dark[token.key] !== seed.value.dark[token.key]
        )
    )

    const isCustomActive = computed(() => family.value === CUSTOM_THEME_FAMILY)

    // Literal black and white by definition: this picks whichever reads better
    // on the swatch, so it must not follow the theme.
    const swatchText = (value?: string): string => (contrastRatio(value ?? '#000000', '#FFFFFF') >= 3 ? '#FFFFFF' : '#000000')

    /**
     * Advisory readability check against the same thresholds the theme contract
     * test enforces. It never blocks saving - it is the user's own theme.
     */
    const warnings = computed<Record<string, string>>(() => {
        const current = values.value
        const result: Record<string, string> = {}
        const flag = (key: string, ratio: number, minimum: number) => {
            if (ratio < minimum) result[key] = t('theme_editor.low_contrast', { ratio: ratio.toFixed(1), min: minimum })
        }

        for (const ground of ['background', 'surface', 'listRow', 'workspace']) {
            flag(ground, contrastRatio(current['onSurface'] ?? '', current[ground] ?? ''), AAA_BODY_TEXT)
        }
        flag('onSurface', contrastRatio(current['onSurface'] ?? '', current['surface'] ?? ''), AAA_BODY_TEXT)
        flag('primary', contrastRatio(current['primary'] ?? '', current['surface'] ?? ''), AA_TEXT)

        return result
    })

    // Dragging the picker's canvas emits on every mousemove, and each install
    // makes Vuetify rebuild the stylesheet for every registered theme. Coalesce
    // to one per frame so the preview stays immediate without the churn.
    let pendingFrame = 0
    const install = (): void => {
        if (pendingFrame) return
        pendingFrame = requestAnimationFrame(() => {
            pendingFrame = 0
            installCustomTheme(theme.value)
        })
    }

    /** Bypass the frame coalescing when the result must be in place immediately. */
    const installNow = (data = theme.value): void => {
        if (pendingFrame) {
            cancelAnimationFrame(pendingFrame)
            pendingFrame = 0
        }
        installCustomTheme(data)
    }

    const setToken = (key: string, value: unknown): void => {
        if (typeof value !== 'string' || !value) return
        const target = editingDark.value ? theme.value.dark : theme.value.light
        target[key] = value.toUpperCase()
        install()
    }

    const setVariant = (dark: boolean): void => {
        editingDark.value = dark
        // Preview only - the saved DARK_THEME setting is left alone.
        if (isCustomActive.value) previewVariant(dark)
    }

    const loadData = (): void => {
        const stored = settingsStore.getSetting(Settings.CUSTOM_THEME, '')
        // A saved theme keeps the family it was seeded from; a fresh one starts
        // from whatever family is active right now.
        seed.value = customThemeSeed(readBasedOn(stored) ?? family.value)

        saved.value = parseCustomTheme(stored, seed.value)
        theme.value = cloneCustomTheme(saved.value)
        editingDark.value = isDark.value
        installNow()
    }

    const reset = (): void => {
        theme.value = cloneCustomTheme(seed.value)
        installNow()
    }

    /** Put a single slot back to the family it was seeded from. */
    const resetToken = (key: string): void => {
        const target = editingDark.value ? theme.value.dark : theme.value.light
        const source = seedValues.value[key]
        if (source) target[key] = source
        installNow()
    }

    const save = async (): Promise<void> => {
        const record = settingsStore.getSettings.find((entry) => entry.key === Settings.CUSTOM_THEME)
        if (!record) {
            // The setting row is created by a migration; without it there is
            // nowhere to save, and silence would look like success.
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'settings.error' } }))
            return
        }

        saving.value = true
        try {
            await settingsStore.saveSettings({
                data: { ...record, value: serializeCustomTheme(theme.value) },
                is_global: false
            })
            saved.value = cloneCustomTheme(theme.value)
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'success', loc: 'settings.successful_edit' } }))
        } catch {
            window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'settings.error' } }))
        } finally {
            saving.value = false
        }
    }

    watch(() => props.loadTrigger, loadData)

    // Leaving the tab with unsaved edits must not leave the app wearing them.
    onBeforeUnmount(() => {
        installNow(saved.value)
        if (isCustomActive.value) previewVariant(isDark.value)
    })

    loadData()
</script>

<style scoped>
    @import '../../styles/settings-pane.css';

    /* The pane itself is padding-free, so the grid would otherwise run flush
       into its border on both sides. */
    .theme-editor__body {
        padding: 1rem 1.1rem 1.15rem;
    }

    .theme-editor__group + .theme-editor__group {
        margin-top: 1.35rem;
    }

    .theme-editor__actions {
        display: flex;
        gap: 0.5rem;
    }

    .theme-editor__group-title {
        display: flex;
        align-items: center;
        margin-bottom: 0.65rem;
        color: rgba(var(--v-theme-on-surface), 0.6);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        gap: 0.75rem;
    }

    .theme-editor__group-title::after {
        border-top: 1px solid var(--review-list-border);
        content: '';
        flex: 1 1 auto;
    }

    .theme-editor__grid {
        display: grid;
        gap: 0.55rem;
        grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
    }

    .token {
        display: flex;
        align-items: center;
        min-width: 0;
        padding: 0.45rem 0.5rem 0.45rem 0.45rem;
        border: 1px solid var(--review-list-border);
        border-radius: 5px;
        background: rgb(var(--v-theme-list-row));
        gap: 0.7rem;
        transition:
            border-color 0.15s ease,
            box-shadow 0.15s ease;
    }

    .token:hover {
        border-color: rgba(var(--v-theme-primary), 0.55);
        box-shadow: 0 1px 6px rgba(var(--v-theme-on-surface), 0.1);
    }

    .token--modified {
        border-inline-start: 3px solid rgb(var(--v-theme-primary));
        padding-inline-start: calc(0.45rem - 2px);
    }

    /* Checkerboard shows through the alpha-capable tokens. */
    .token__swatch {
        width: 42px;
        height: 42px;
        flex: 0 0 42px;
        border: 1px solid rgba(var(--v-theme-on-surface), 0.28);
        border-radius: 4px;
        background-color: transparent;
        background-image:
            linear-gradient(45deg, rgba(128, 128, 128, 0.22) 25%, transparent 25%),
            linear-gradient(-45deg, rgba(128, 128, 128, 0.22) 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, rgba(128, 128, 128, 0.22) 75%),
            linear-gradient(-45deg, transparent 75%, rgba(128, 128, 128, 0.22) 75%);
        background-position:
            0 0,
            0 5px,
            5px -5px,
            -5px 0;
        background-size: 10px 10px;
        cursor: pointer;
    }

    .token__swatch:focus-visible {
        outline: 2px solid rgb(var(--v-theme-primary));
        outline-offset: 2px;
    }

    .token__body {
        display: flex;
        min-width: 0;
        flex: 1 1 auto;
        flex-direction: column;
        gap: 0.1rem;
    }

    .token__name {
        overflow: hidden;
        font-size: 0.86rem;
        font-weight: 600;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .token__value {
        color: rgba(var(--v-theme-on-surface), 0.58);
        font-family: ui-monospace, 'SFMono-Regular', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.02em;
    }

    .token__warning {
        display: flex;
        align-items: center;
        color: rgb(var(--v-theme-warning));
        font-size: 0.7rem;
        font-weight: 600;
        gap: 0.2rem;
    }

    /* Always present, so the control is discoverable on every colour, but muted
       until there is something to undo. */
    .token__reset {
        flex: 0 0 auto;
        opacity: 0.32;
        transition: opacity 0.15s ease;
    }

    .token--modified .token__reset,
    .token:hover .token__reset,
    .token__reset:focus-visible {
        opacity: 1;
    }

    @media (max-width: 620px) {
        .theme-editor__grid {
            grid-template-columns: 1fr;
        }
    }
</style>
