<template>
    <div>
        <BaseCard
            :multi-select-active="multiSelectActive"
            :show-selection-checkbox="true"
            :preselected="preselected"
            :card-class="'card-item'"
            :card-color="selectedColor"
            @card-click="cardItemClick"
            @selection-change="selectionChanged"
        >
            <!-- Content Slot -->
            <template #content>
                <v-row class="align-center">
                    <!-- Reserve space for an icon (products have none) so content aligns like Analyze -->
                    <v-col cols="auto">
                        <div
                            class="ms-2"
                            style="width: 32px"
                        />
                    </v-col>
                    <!-- Main content (grows to push actions to the right) -->
                    <v-col>
                        <!-- Label Row: Type Name, Description, Updated Info -->
                        <v-row
                            align="center"
                            class="text-label-medium text-grey"
                        >
                            <!-- Type Name (label for title) -->
                            <v-col
                                cols="12"
                                md="6"
                                class="d-flex align-center"
                            >
                                <span>{{ card.product_type_name }}</span>
                            </v-col>
                            <!-- Description label (for subtitle) -->
                            <v-col>
                                <span>{{ t('card_item.description') }}</span>
                            </v-col>
                            <!-- Updated Info -->
                            <v-col
                                cols="auto"
                                class="d-flex align-center"
                            >
                                <span>
                                    {{ t('card_item.updated') }}:
                                    {{ card.updated_at }}
                                    <span
                                        v-if="card.updated_by"
                                        class="ms-2"
                                        >{{ card.updated_by }}</span
                                    >
                                </span>
                            </v-col>
                        </v-row>
                        <!-- Value Row: Title, Subtitle, State (below Updated) -->
                        <v-row
                            class="mt-2"
                            align="center"
                        >
                            <v-col
                                cols="12"
                                md="6"
                            >
                                <div class="text-title-medium">
                                    {{ card.title }}
                                    <span
                                        v-if="card.report_items_count"
                                        class="text-grey ms-1"
                                        >({{ card.report_items_count }})</span
                                    >
                                </div>
                            </v-col>
                            <v-col>
                                <div class="text-body-medium">
                                    {{ card.subtitle }}
                                </div>
                            </v-col>
                            <v-col
                                v-if="card.state"
                                cols="auto"
                                class="d-flex justify-end align-center"
                                :title="card.state.description"
                            >
                                <v-icon :color="card.state.color">
                                    {{ card.state.icon }}
                                </v-icon>
                                <span class="text-body-large ms-2">
                                    {{
                                        $te('workflow.states.' + card.state.display_name)
                                            ? $t('workflow.states.' + card.state.display_name)
                                            : card.state.display_name
                                    }}
                                </span>
                            </v-col>
                        </v-row>
                    </v-col>
                    <!-- Actions - right side, vertically centered, like Analyze -->
                    <v-col
                        cols="auto"
                        class="d-flex justify-end"
                    >
                        <!-- Delete -->
                        <ActionButton
                            v-if="canDelete"
                            action="delete"
                            :title="t('publish.tooltip.delete_item')"
                            @click.stop="showDeleteDialog = true"
                        />
                    </v-col>
                </v-row>
            </template>
        </BaseCard>

        <!-- Delete Confirmation Dialog -->
        <ConfirmationDialog
            v-model="showDeleteDialog"
            :message="card.title || ''"
            max-width="500px"
            @confirm="handleDelete"
        />
    </div>
</template>

<script setup lang="ts">
    import { ref, computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { usePublishStore } from '@/stores/publish'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { deleteProduct } from '@/api/publish'
    import BaseCard from '@/components/common/BaseCard.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type ProductCard = {
        id: number | string
        title?: string
        subtitle?: string
        tag?: string
        product_type_name?: string
        product_type_id?: number | string
        report_items_count?: number
        report_items?: unknown[]
        updated_at?: string
        updated_by?: string
        modify?: boolean
        access?: boolean
        state?: {
            id?: number | string | null
            color?: string
            icon?: string
            display_name?: string
            description?: string
        } | null
        [key: string]: any
    }

    const props = withDefaults(
        defineProps<{
            card: ProductCard
            preselected?: boolean
        }>(),
        {
            preselected: false
        }
    )

    const { t } = useI18n()
    const publishStore = usePublishStore()
    const { checkPermission } = useAuth()

    const showDeleteDialog = ref<boolean>(false)

    const multiSelectActive = computed(() => publishStore.getMultiSelect)

    const selectedColor = computed(() => {
        return publishStore.selectedProducts.has(props.card.id) ? 'orange-lighten-4' : ''
    })

    const canDelete = computed(() => {
        // Check permission - modify check may not be needed or property may be named differently
        return checkPermission(PERMISSIONS.PUBLISH_DELETE)
    })

    const selectionChanged = (isSelected: boolean): void => {
        if (isSelected) {
            publishStore.select({ id: props.card.id, item: props.card })
        } else {
            publishStore.deselect({ id: props.card.id })
        }
    }

    const cardItemClick = (): void => {
        // Emit event to open edit dialog
        const editData = {
            id: props.card.id,
            title: props.card.title,
            description: props.card.subtitle || '',
            product_type_id: props.card.product_type_id,
            state_id: props.card.state?.id || null,
            report_items: props.card.report_items || [],
            modify: props.card.modify === true,
            access: props.card.access === true
        }
        window.dispatchEvent(new CustomEvent('show-product-edit', { detail: editData }))
    }

    const handleDelete = async (): Promise<void> => {
        showDeleteDialog.value = false
        try {
            await deleteProduct(props.card)

            // Show success notification
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'success', loc: 'common.deleted_successfully' }
                })
            )

            // Emit event to refresh the list
            window.dispatchEvent(new CustomEvent('product-updated'))
        } catch (error: unknown) {
            console.error('Error deleting product:', error)

            // Show error notification
            window.dispatchEvent(
                new CustomEvent('notification', {
                    detail: { type: 'error', loc: 'common.error_deleting' }
                })
            )
        }
    }
</script>

<style scoped>
    .card-item {
        cursor: pointer;
        transition: all 0.3s ease;
    }
</style>
