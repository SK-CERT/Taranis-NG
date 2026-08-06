<template>
    <div>
        <BaseCard
            :multi-select-active="multiSelectActive"
            :show-selection-checkbox="true"
            :preselected="preselected"
            card-class="review-list__row"
            :card-id="card.id"
            @card-click="cardItemClick"
            @selection-change="selectionChanged"
        >
            <!-- Content Slot -->
            <template #content>
                <article class="product-card">
                    <div class="product-card__icon">
                        <v-icon
                            :icon="productIcon"
                            size="22"
                        />
                    </div>

                    <div class="product-card__content">
                        <div class="product-card__meta-row">
                            <span class="product-card__type">{{ card.product_type_name }}</span>
                            <span class="product-card__updated">
                                <v-icon size="14">mdi-clock-outline</v-icon>
                                {{ t('card_item.updated') }} {{ card.updated_at }}
                                <span v-if="card.updated_by">· {{ card.updated_by }}</span>
                            </span>
                        </div>

                        <h2 class="product-card__title">{{ card.title }}</h2>

                        <div class="product-card__details">
                            <v-chip
                                v-if="card.state"
                                :color="card.state.color"
                                variant="tonal"
                                size="small"
                                :title="card.state.description"
                                class="product-card__state"
                            >
                                <v-icon
                                    v-if="card.state.icon"
                                    start
                                    size="15"
                                >
                                    {{ card.state.icon }}
                                </v-icon>
                                {{
                                    $te('workflow.states.' + card.state.display_name)
                                        ? $t('workflow.states.' + card.state.display_name)
                                        : card.state.display_name
                                }}
                            </v-chip>

                            <span
                                v-if="card.report_items_count"
                                class="product-card__report-count"
                                :title="t('nav_menu.report_items')"
                            >
                                <v-icon size="15">mdi-file-document-multiple-outline</v-icon>
                                {{ card.report_items_count }}
                            </span>

                            <span
                                v-if="card.subtitle"
                                class="product-card__subtitle"
                            >
                                {{ card.subtitle }}
                            </span>
                        </div>
                    </div>

                    <div
                        v-if="canDelete"
                        class="product-card__actions"
                    >
                        <!-- Delete -->
                        <ActionButton
                            action="delete"
                            :title="t('publish.tooltip.delete_item')"
                            @click.stop="showDeleteDialog = true"
                        />
                    </div>
                </article>
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

    const canDelete = computed(() => {
        // Check permission - modify check may not be needed or property may be named differently
        return checkPermission(PERMISSIONS.PUBLISH_DELETE)
    })

    const productIcon = computed(() => {
        return props.card.tag === 'mdi-file-pdf-outline' ? 'mdi-file-pdf-box' : props.card.tag || 'mdi-send'
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
    .product-card {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        gap: 0.65rem;
        min-width: 0;
    }

    .product-card__icon {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        border-radius: 4px;
        color: rgb(var(--v-theme-primary));
        background: rgba(var(--v-theme-primary), 0.1);
        box-shadow: inset 0 0 0 1px rgba(var(--v-theme-primary), 0.14);
    }

    .product-card__content {
        min-width: 0;
    }

    .product-card__meta-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        min-width: 0;
    }

    .product-card__type {
        overflow: hidden;
        color: rgb(var(--v-theme-primary));
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .product-card__updated {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        color: rgba(var(--v-theme-on-surface), 0.55);
        font-size: 0.72rem;
        white-space: nowrap;
    }

    .product-card__title {
        margin: 0.15rem 0 0.3rem;
        color: rgb(var(--v-theme-on-surface));
        font-size: clamp(0.95rem, 1.2vw, 1.05rem);
        font-weight: 650;
        line-height: 1.25;
        overflow-wrap: anywhere;
    }

    .product-card__details {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        min-height: 22px;
        min-width: 0;
    }

    .product-card__state {
        border-radius: 3px;
        font-weight: 650;
    }

    .product-card__report-count {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.76rem;
        font-weight: 650;
    }

    .product-card__subtitle {
        overflow: hidden;
        min-width: 0;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.78rem;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .product-card__actions {
        padding-inline-start: 0.5rem;
        border-inline-start: 1px solid rgba(var(--v-theme-outline), 0.24);
    }

    .product-card__actions :deep(.v-btn) {
        border-radius: 3px;
    }

    @media (max-width: 760px) {
        .product-card__updated,
        .product-card__subtitle {
            display: none;
        }
    }
</style>
