<template>
    <v-dialog v-model="isOpen" :max-width="maxWidth">
        <v-card>
            <v-card-title class="d-flex align-center" style="white-space: normal">
                <v-icon color="error" class="mr-2">
                    {{ ICONS.ALERT_CIRCLE }}
                </v-icon>
                {{ t(titleKey) }}
            </v-card-title>
            <v-card-text class="text-center">
                <slot>{{ message }}</slot>
            </v-card-text>
            <v-card-actions>
                <v-spacer />
                <v-btn variant="text" @click="isOpen = false">
                    {{ t('common.cancel') }}
                </v-btn>
                <v-btn color="error" variant="text" @click="confirmDelete">
                    {{ t(confirmLabelKey) }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const props = withDefaults(
        defineProps<{
            modelValue?: boolean
            message?: string
            titleKey?: string
            confirmLabelKey?: string
            maxWidth?: string
        }>(),
        {
            modelValue: false,
            message: '',
            titleKey: 'common.messagebox.delete',
            confirmLabelKey: 'common.delete',
            maxWidth: '600px'
        }
    )

    const emit = defineEmits(['update:modelValue', 'confirm'])

    const { t } = useI18n()
    const titleKey = props.titleKey
    const confirmLabelKey = props.confirmLabelKey

    const isOpen = ref<boolean>(false)

    watch(
        () => props.modelValue,
        (newVal: boolean) => {
            isOpen.value = newVal
        }
    )

    watch(isOpen, (newVal: boolean) => {
        emit('update:modelValue', newVal)
    })

    const confirmDelete = (): void => {
        emit('confirm')
        isOpen.value = false
    }
</script>

<style scoped></style>
