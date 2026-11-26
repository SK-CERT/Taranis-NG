<template>
    <v-btn
        icon
        variant="text"
        size="small"
        density="comfortable"
        :title="label"
        :aria-label="label"
        :aria-pressed="removing"
        data-test="stored-secret-toggle"
        @click.stop="emit('toggle')"
    >
        <v-icon>{{ removing ? 'mdi-undo' : 'mdi-close' }}</v-icon>
    </v-btn>
</template>

<script setup lang="ts">
    /** Removes a stored credential on save, or keeps it after all (see useStoredSecretRemoval). */
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'

    const props = defineProps<{ removing: boolean }>()
    const emit = defineEmits<{ (e: 'toggle'): void }>()
    const { t } = useI18n()
    const label = computed(() => (props.removing ? t('common.keep_stored_secret') : t('common.remove_stored_secret')))
</script>
