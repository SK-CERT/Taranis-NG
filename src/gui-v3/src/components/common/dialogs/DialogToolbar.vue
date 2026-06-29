<template>
    <v-toolbar
        color="primary"
        density="compact"
    >
        <v-toolbar-title>{{ title }}</v-toolbar-title>
        <v-spacer />
        <v-btn
            variant="text"
            :disabled="saving"
            @click="$emit('cancel')"
        >
            {{ t('common.cancel') }}
        </v-btn>
        <v-btn
            v-if="showSave"
            variant="text"
            :loading="saving"
            :disabled="saving || saveDisabled"
            @click="$emit('save')"
        >
            <v-icon start>mdi-content-save</v-icon>
            {{ t('common.save') }}
        </v-btn>
    </v-toolbar>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'

    const { t } = useI18n()

    withDefaults(
        defineProps<{
            /** Header title text (already translated). */
            title: string
            /** Save in progress: disables both buttons and shows a spinner on save. */
            saving?: boolean
            /** Extra condition that disables the save button (beyond `saving`). */
            saveDisabled?: boolean
            /** Hide the save button entirely (e.g. read-only dialogs). */
            showSave?: boolean
        }>(),
        {
            saving: false,
            saveDisabled: false,
            showSave: true
        }
    )

    defineEmits<{
        (e: 'cancel'): void
        (e: 'save'): void
    }>()
</script>
