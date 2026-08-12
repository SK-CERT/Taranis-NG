<template>
    <div class="mdi-icon-picker">
        <div class="mdi-icon-picker__label text-caption mb-1">
            {{ label }}
        </div>

        <v-btn
            class="mdi-icon-picker__trigger"
            variant="outlined"
            block
            :disabled="disabled"
            :aria-label="`${label}: ${modelValue}`"
            @click="openPicker"
        >
            <v-icon
                :icon="modelValue"
                size="24"
            />
            <v-spacer />
            <v-icon icon="mdi-chevron-down" />
        </v-btn>

        <v-dialog
            v-model="pickerOpen"
            max-width="700"
            scrollable
        >
            <v-card>
                <v-card-title>{{ label }}</v-card-title>
                <v-card-text>
                    <v-text-field
                        ref="searchField"
                        v-model="search"
                        :label="t('toolbar_filter.search')"
                        prepend-inner-icon="mdi-magnify"
                        clearable
                        hide-details
                        variant="outlined"
                        density="comfortable"
                        class="mb-4"
                    />

                    <v-virtual-scroll
                        v-if="iconRows.length"
                        class="mdi-icon-picker__icons"
                        :items="iconRows"
                        :height="384"
                        :item-height="76"
                    >
                        <template #default="{ item: row }">
                            <div class="mdi-icon-picker__row">
                                <v-btn
                                    v-for="icon in row"
                                    :key="icon"
                                    class="mdi-icon-picker__icon"
                                    :class="{ 'mdi-icon-picker__icon--selected': icon === modelValue }"
                                    :variant="icon === modelValue ? 'tonal' : 'text'"
                                    :color="icon === modelValue ? 'primary' : undefined"
                                    :title="icon"
                                    :aria-label="icon"
                                    block
                                    @click="selectIcon(icon)"
                                >
                                    <v-icon
                                        :icon="icon"
                                        size="26"
                                    />
                                    <span class="mdi-icon-picker__icon-name">{{ icon }}</span>
                                </v-btn>
                            </div>
                        </template>
                    </v-virtual-scroll>

                    <div
                        v-else
                        class="text-medium-emphasis text-center py-8"
                    >
                        {{ t('common.no_data') }}
                    </div>
                </v-card-text>
                <v-card-actions>
                    <v-spacer />
                    <v-btn
                        variant="text"
                        @click="cancel"
                    >
                        {{ t('common.cancel') }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
    import { computed, nextTick, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import mdiVariables from '@mdi/font/scss/_variables.scss?raw'

    const props = withDefaults(
        defineProps<{
            modelValue: string
            label: string
            disabled?: boolean
        }>(),
        {
            disabled: false
        }
    )

    const emit = defineEmits<{
        'update:modelValue': [value: string]
    }>()

    const { t } = useI18n()
    const pickerOpen = ref(false)
    const search = ref('')
    const searchField = ref<{ focus: () => void } | null>(null)

    // @mdi/font ships the canonical icon-name map with the font itself. Reading it
    // keeps the picker synchronized with the exact MDI version used by Vuetify.
    const iconNames = Array.from(mdiVariables.matchAll(/^\s*"([^"]+)":\s*[A-F\d]+,?$/gm), (match) => `mdi-${match[1]}`)

    const filteredIcons = computed(() => {
        const query = search.value.trim().toLocaleLowerCase().replace(/^mdi-/, '')
        if (!query) return iconNames
        return iconNames.filter((icon) => icon.slice(4).includes(query))
    })

    const iconRows = computed(() => {
        const rows: string[][] = []
        for (let index = 0; index < filteredIcons.value.length; index += 6) {
            rows.push(filteredIcons.value.slice(index, index + 6))
        }
        return rows
    })

    async function openPicker(): Promise<void> {
        if (props.disabled) return
        search.value = ''
        pickerOpen.value = true
        await nextTick()
        searchField.value?.focus()
    }

    function selectIcon(icon: string): void {
        emit('update:modelValue', icon)
        pickerOpen.value = false
    }

    function cancel(): void {
        pickerOpen.value = false
    }
</script>

<style scoped>
    .mdi-icon-picker__label {
        color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
        padding-inline: 12px;
    }

    .mdi-icon-picker__trigger {
        height: 48px;
        justify-content: flex-start;
        padding-inline: 16px;
        text-transform: none;
    }

    .mdi-icon-picker__icons {
        border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
        border-radius: 4px;
    }

    .mdi-icon-picker__row {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        min-height: 76px;
        place-items: center;
    }

    .mdi-icon-picker__icon {
        height: 68px;
        min-width: 0;
        padding: 4px;
    }

    .mdi-icon-picker__icon :deep(.v-btn__content) {
        flex-direction: column;
        max-width: 100%;
    }

    .mdi-icon-picker__icon-name {
        color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
        display: block;
        font-size: 9px;
        font-weight: 400;
        line-height: 14px;
        margin-top: 3px;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        text-transform: none;
        white-space: nowrap;
    }

    .mdi-icon-picker__icon--selected {
        outline: 2px solid rgb(var(--v-theme-primary));
        outline-offset: -2px;
    }
</style>
