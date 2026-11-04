<template>
    <v-dialog
        v-model="isOpen"
        :max-width="maxWidth"
        @keydown.stop="handleDialogKeydown"
        @after-enter="focusCancelButton"
    >
        <v-card style="min-width: min(500px, calc(100vw - 48px))">
            <v-card-title
                class="d-flex align-center"
                style="white-space: normal; font-size: 1.1rem; line-height: 1.4"
            >
                <v-icon
                    color="error"
                    class="me-2"
                >
                    {{ icon }}
                </v-icon>
                {{ t(titleKey) }}
            </v-card-title>
            <v-card-text class="text-center">
                <slot>{{ message }}</slot>
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn
                    ref="cancelButton"
                    variant="text"
                    @click="isOpen = false"
                >
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn
                    ref="deleteButton"
                    color="error"
                    variant="text"
                    @click="confirmDelete"
                >
                    {{ t(confirmLabelKey) }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            message?: string
            titleKey?: string
            confirmLabelKey?: string
            maxWidth?: string
            icon?: string
        }>(),
        {
            modelValue: false,
            message: '',
            titleKey: 'common.messagebox.delete',
            confirmLabelKey: 'common.delete',
            maxWidth: '600px',
            icon: ICONS.ALERT_CIRCLE
        }
    )

    const emit = defineEmits(['update:modelValue', 'confirm'])

    const { t } = useI18n()
    const titleKey = props.titleKey
    const confirmLabelKey = props.confirmLabelKey

    const isOpen = computed({
        get: () => props.modelValue,
        set: (value: boolean) => emit('update:modelValue', value)
    })

    const cancelButton = ref<{ $el: HTMLElement } | null>(null)
    const deleteButton = ref<{ $el: HTMLElement } | null>(null)

    const focusButton = (button: HTMLElement | undefined): void => {
        button?.focus({ focusVisible: true })
    }

    const focusCancelButton = (): void => {
        focusButton(cancelButton.value?.$el)
    }

    const handleDialogKeydown = (event: KeyboardEvent): void => {
        if (event.key === 'ArrowLeft') {
            event.preventDefault()
            focusCancelButton()
        } else if (event.key === 'ArrowRight') {
            event.preventDefault()
            focusButton(deleteButton.value?.$el)
        } else if (event.key === 'Escape') {
            event.preventDefault()
            isOpen.value = false
        }
    }

    const confirmDelete = (): void => {
        emit('confirm')
        isOpen.value = false
    }
</script>
