<template>
    <v-text-field
        v-model="model"
        :label="label"
        :placeholder="suggested || placeholder"
        variant="outlined"
        density="comfortable"
        persistent-hint
        :disabled="disabled"
        v-bind="$attrs"
    >
        <template #append-inner>
            <slot name="append-inner" />
            <v-btn
                v-if="suggested"
                icon
                variant="text"
                size="small"
                :disabled="disabled || !suggested"
                :aria-label="tooltipText"
                :title="tooltipText"
                @click="applySuggested"
            >
                <v-icon size="small">mdi-auto-fix</v-icon>
            </v-btn>
        </template>
        <template #append>
            <slot name="append" />
        </template>
        <template
            v-for="name in forwardSlots"
            #[name]
        >
            <slot :name="name" />
        </template>
    </v-text-field>
</template>

<script setup lang="ts">
    /**
     * SuggestField - a v-text-field that offers a suggested value.
     *
     * The suggested value is shown as the placeholder (so the user sees the right
     * answer before typing) and a wand icon in the append slot fills the field with
     * it on click. The suggestion is caller-supplied (e.g. a metadata URL derived
     * from the current host) so this component stays generic: anything not listed
     * below (rules, hint, variant, @update:model-value, ...) falls through to the
     * underlying v-text-field via $attrs.
     *
     *   <SuggestField v-model="entityId" :suggested="suggestedEntityId" :label="t('...')" :hint="t('...')" :rules="rules" />
     *
     * The default tooltip is the shared ``common.use_suggested``. Override it with
     * ``tooltip-label`` when the suggestion needs a more specific call-to-action.
     */
    import { computed, useSlots } from 'vue'
    import { useI18n } from 'vue-i18n'

    defineOptions({ inheritAttrs: false })

    const props = defineProps<{
        label?: string
        suggested?: string
        placeholder?: string
        tooltipLabel?: string
        disabled?: boolean
    }>()

    const model = defineModel<string | undefined>({ default: '' })
    const emit = defineEmits<{ (e: 'suggest', value: string): void }>()
    const slots = useSlots()
    const { t } = useI18n()

    const tooltipText = computed(() => props.tooltipLabel ?? t('common.use_suggested'))

    // Forward only the slots the caller hasn't provided (anything except the ones we
    // manage ourselves), so append-inner / append still compose with the wand icon.
    const managedSlots = new Set(['append-inner', 'append'])
    const forwardSlots = computed(() => Object.keys(slots).filter((name) => !managedSlots.has(name)))

    const applySuggested = (): void => {
        if (props.suggested !== undefined) {
            model.value = props.suggested
            emit('suggest', props.suggested)
        }
    }
</script>
