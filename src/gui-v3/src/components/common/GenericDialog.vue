<template>
    <v-dialog
        v-model="dialogVisible"
        :max-width="maxWidth"
        persistent
    >
        <template #activator="{ props: activatorProps }">
            <AddNewButton
                v-if="showButton && canCreate"
                :label="buttonText || 'common.add_btn'"
                v-bind="activatorProps"
            />
        </template>

        <v-card>
            <DialogToolbar
                :title="dialogTitle"
                :saving="saving"
                @cancel="handleCancel"
                @save="handleSubmit"
            />

            <v-card-text>
                <v-form
                    ref="formRef"
                    @submit.prevent="handleSubmit"
                >
                    <slot
                        name="form"
                        :item="item"
                        :is-edit="isEdit"
                    />
                </v-form>

                <v-alert
                    v-if="showValidationError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showValidationError = false"
                >
                    {{ t('error.validation') }}
                </v-alert>

                <v-alert
                    v-if="showError"
                    type="error"
                    variant="tonal"
                    class="mt-4"
                    closable
                    @click:close="showError = false"
                >
                    {{ errorMessage || t('common.error') }}
                </v-alert>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'

    const props = defineProps({
        modelValue: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            default: ''
        },
        editTitle: {
            type: String,
            default: ''
        },
        item: {
            type: Object,
            required: true
        },
        isEdit: {
            type: Boolean,
            default: false
        },
        canCreate: {
            type: Boolean,
            default: true
        },
        showButton: {
            type: Boolean,
            default: true
        },
        buttonText: {
            type: String,
            default: ''
        },
        maxWidth: {
            type: [String, Number],
            default: 600
        },
        errorMessage: {
            type: String,
            default: ''
        }
    })

    const emit = defineEmits<{
        (e: 'update:modelValue', value: boolean): void
        (e: 'save', item: Record<string, unknown>): void
        (e: 'cancel'): void
    }>()

    const { t } = useI18n()

    const formRef = ref<any>(null)
    const showValidationError = ref(false)
    const showError = ref(false)
    const saving = ref(false)

    const dialogVisible = computed({
        get: () => props.modelValue,
        set: (value) => emit('update:modelValue', value)
    })

    const dialogTitle = computed(() => {
        if (props.isEdit && props.editTitle) {
            return props.editTitle
        }
        if (props.isEdit) {
            return `${t('common.edit')} ${props.title}`
        }
        return props.title || t('common.add_new')
    })

    async function handleSubmit(): Promise<void> {
        showValidationError.value = false
        showError.value = false

        const { valid } = await formRef.value.validate()
        if (!valid) {
            showValidationError.value = true
            return
        }

        saving.value = true
        try {
            await emit('save', props.item)
        } catch (error) {
            showError.value = true
            saving.value = false
        }
    }

    function handleCancel(): void {
        showValidationError.value = false
        showError.value = false
        formRef.value?.reset()
        emit('cancel')
        dialogVisible.value = false
    }

    watch(
        () => props.modelValue,
        (newVal: boolean) => {
            if (!newVal) {
                showValidationError.value = false
                showError.value = false
                saving.value = false
            }
        }
    )
</script>
