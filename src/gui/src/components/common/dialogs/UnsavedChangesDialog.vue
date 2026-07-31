<template>
    <v-dialog
        v-model="isOpen"
        max-width="500px"
        persistent
    >
        <v-card>
            <v-card-title class="text-h5">
                {{ t('confirm_close.title') }}
            </v-card-title>
            <v-card-text>{{ message || t('confirm_close.message') }}</v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    color="primary"
                    variant="elevated"
                    class="confirm-btn"
                    @click="emit('continue')"
                >
                    {{ t('confirm_close.continue') }}
                </v-btn>
                <v-btn
                    color="success"
                    variant="elevated"
                    class="confirm-btn"
                    @click="emit('save')"
                >
                    {{ t('confirm_close.save_and_close') }}
                </v-btn>
                <v-btn
                    color="error"
                    variant="elevated"
                    class="confirm-btn"
                    @click="emit('discard')"
                >
                    {{ t('confirm_close.close') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            /** Optional override for the body text (already translated). */
            message?: string
        }>(),
        {
            modelValue: false,
            message: ''
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'continue'): void
        (e: 'save'): void
        (e: 'discard'): void
    }>()

    const { t } = useI18n()

    const isOpen = computed<boolean>({
        get: () => props.modelValue,
        set: (value: boolean) => emit('update:modelValue', value)
    })
</script>

<style scoped>
    /* Keep the button labels white regardless of theme on-* colors. */
    .confirm-btn,
    .confirm-btn :deep(.v-btn__content) {
        color: #fff !important;
    }
</style>
