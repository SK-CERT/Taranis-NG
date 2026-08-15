<template>
    <v-text-field
        v-bind="$attrs"
        :id="resolvedId"
        v-model="model"
        :label="resolvedLabel"
        :prepend-inner-icon="resolvedIcon"
        :style="widthStyle"
        variant="outlined"
        density="compact"
        hide-details
        single-line
        clearable
    />
</template>

<script setup lang="ts">
    /**
     * SearchField - the app-wide search input.
     *
     * Renders the standard search look (outlined, compact, single-line, magnify icon,
     * "Search" label, clearable) so callers only override what differs. Anything not
     * listed below (disabled, @update:model-value, style, `:clearable="false"`, ...)
     * falls through to the underlying v-text-field.
     *
     *   <SearchField v-model="search" />                       <!-- default look -->
     *   <SearchField v-model="search" :width="350" />          <!-- fixed width -->
     *   <SearchField v-model="search" :label="t('x')" icon="mdi-account-search" />
     */
    import { computed, useAttrs, useId } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    // Forward stray attrs to the input rather than the root, so e.g. `style`/`class`
    // passed by the caller end up on the v-text-field.
    defineOptions({ inheritAttrs: false })

    const props = defineProps<{
        /** Field label/placeholder text. Defaults to the shared "Search" string. */
        label?: string
        /** Prepend-inner icon. Defaults to the magnify icon. */
        icon?: string
        /** Fixed width, e.g. 350 or '350px'. Omit for full width. */
        width?: string | number
    }>()

    const model = defineModel<string | undefined>({ default: '' })
    const { t } = useI18n()
    const attrs = useAttrs()

    // A per-instance id. The previous hardcoded `id="search"` gave every instance the
    // same one, so any view showing two search fields (a list toolbar plus a dialog,
    // say) emitted duplicate DOM ids — invalid HTML that breaks `<label for>` binding
    // and makes Vuetify report a duplicate input name inside a v-form. It sat after
    // `v-bind="$attrs"`, so a caller could not override it either; now they can.
    const generatedId = useId()
    const resolvedId = computed(() => (typeof attrs['id'] === 'string' ? attrs['id'] : generatedId))

    const resolvedLabel = computed(() => props.label ?? t('toolbar_filter.search'))
    const resolvedIcon = computed(() => props.icon ?? ICONS.MAGNIFY)
    const widthStyle = computed(() =>
        props.width != null ? { width: typeof props.width === 'number' ? `${props.width}px` : props.width } : undefined
    )
</script>
