<template>
    <v-container
        fluid
        class="pa-2"
    >
        <div
            class="card-container d-flex align-center"
            :class="{ 'ga-3': multiSelectActive }"
        >
            <!-- Checkbox for multi-select -->
            <div
                v-if="multiSelectActive"
                class="checkbox-column"
                @click.stop
            >
                <v-checkbox
                    v-model="internalSelected"
                    density="compact"
                    hide-details
                    @update:model-value="emitSelectionChange"
                />
            </div>

            <!-- Card -->
            <v-hover v-slot="{ isHovering, props: hoverProps }">
                <v-card
                    v-bind="hoverProps"
                    :elevation="isHovering ? 12 : 2"
                    class="card-compact flex-grow-1"
                    @click="handleClick"
                >
                    <v-card-text>
                        <v-row align="center">
                            <!-- Icon/Tag -->
                            <v-col
                                cols="auto"
                                class="pr-4"
                            >
                                <v-icon
                                    size="large"
                                    color="primary"
                                >
                                    {{ card.tag || ICONS.FILE_DOCUMENT }}
                                </v-icon>
                            </v-col>

                            <!-- Title -->
                            <v-col>
                                <div class="text-label-small text-grey">
                                    {{ typeLabel }}
                                </div>
                                <div class="text-body-large">
                                    {{ typeValue }}
                                </div>
                            </v-col>

                            <!-- Description/Subtitle -->
                            <v-col v-if="card.subtitle || card.description || isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.description') }}
                                </div>
                                <div class="text-body-medium">
                                    {{ card.subtitle || card.description || '' }}
                                </div>
                            </v-col>

                            <!-- URL (nodes) -->
                            <v-col v-if="card.api_url">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.url') }}
                                </div>
                                <div class="text-body-medium">
                                    {{ card.api_url }}
                                </div>
                            </v-col>

                            <!-- Last Seen (nodes) -->
                            <v-col v-if="card.last_seen">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_seen') }}
                                </div>
                                <div class="text-body-medium">
                                    {{ card.last_seen || '' }}
                                </div>
                            </v-col>

                            <!-- Last Attempt / Last Collected (OSINT sources) — last_collected is
                                 empty until a source is collected successfully. -->
                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_attempted') }}
                                </div>
                                <div class="text-body-medium">
                                    {{ card.last_attempted || ' ' }}
                                </div>
                            </v-col>

                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_collected') }}
                                </div>
                                <div class="text-body-medium">
                                    {{ card.last_collected || ' ' }}
                                </div>
                            </v-col>

                            <!-- Last Error (OSINT sources) -->
                            <v-col v-if="isOsintSource">
                                <div class="text-label-small text-grey">
                                    {{ t('card_item.last_error') }}
                                </div>
                                <div class="text-body-medium text-error">
                                    {{ card.last_error_message || ' ' }}
                                </div>
                            </v-col>

                            <!-- Actions -->
                            <v-col
                                v-if="canDelete"
                                cols="auto"
                            >
                                <ActionButton
                                    action="delete"
                                    :disabled="isProtected"
                                    @click.stop="showDeleteDialog"
                                />
                            </v-col>
                        </v-row>
                    </v-card-text>
                </v-card>
            </v-hover>
        </div>

        <!-- Delete confirmation dialog -->
        <ConfirmationDialog
            v-model="deleteDialog"
            :message="card.title || card.name || ''"
            max-width="400"
            @confirm="handleDelete"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { ref, computed, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import type { PermissionKey } from '@/types/permissions'
    import { ICONS } from '@/config/ui-constants'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type CardData = {
        id?: string | number
        title?: string
        name?: string
        subtitle?: string
        description?: string
        tag?: string
        api_url?: string
        last_seen?: string
        collector_id?: string
        last_attempted?: string
        last_collected?: string
        last_error_message?: string
        default?: boolean
        report_type_name?: string
        product_type_name?: string
        news_items?: Array<{
            news_item_data?: {
                osint_source_name?: string
                source?: string
                osint_source_type?: string
            }
        }>
    }

    const props = withDefaults(
        defineProps<{
            card: CardData
            deletePermission?: string
            multiSelectActive?: boolean
            preselected?: boolean
            lockDefault?: boolean
        }>(),
        {
            deletePermission: '',
            multiSelectActive: false,
            preselected: false,
            lockDefault: false
        }
    )

    const emit = defineEmits(['click', 'delete', 'edit', 'selection-change'])

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const deleteDialog = ref(false)
    const internalSelected = ref<boolean>(props.preselected)

    // Watch preselected prop and sync with internalSelected
    watch(
        () => props.preselected,
        (newValue: boolean) => {
            internalSelected.value = newValue
        }
    )

    const canDelete = computed(() => {
        if (!props.deletePermission) return false
        return checkPermission(props.deletePermission as PermissionKey)
    })

    // Protected (default) items cannot be deleted — the backend forbids it (e.g. the default
    // "Uncategorized" OSINT source group). The card stays clickable; the dialog opens read-only.
    // Enabled per view via lock-default.
    const isProtected = computed(() => props.lockDefault && props.card?.default === true)

    // OSINT source cards always carry a collector_id; for them we always render the
    // description and collection-status columns (matching the Vue 2 card), with an em-dash
    // fallback when a value is empty.
    const isOsintSource = computed(() => props.card?.collector_id != null)

    const typeLabel = computed(() => {
        // Node-type items (collectors/presenters/publishers/bots nodes) carry an api_url.
        if (props.card?.api_url) {
            return t('card_item.node')
        }
        if (props.card?.report_type_name) {
            return props.card.report_type_name
        }
        if (props.card?.product_type_name) {
            return props.card.product_type_name
        }
        const sourceName =
            props.card?.news_items?.[0]?.news_item_data?.osint_source_name || props.card?.news_items?.[0]?.news_item_data?.source
        const sourceType = props.card?.news_items?.[0]?.news_item_data?.osint_source_type
        if (sourceName) {
            return sourceType ? `${sourceName} (${sourceType})` : sourceName
        }
        return t('card_item.title')
    })

    const typeValue = computed(() => {
        return props.card?.title || props.card?.name || ''
    })

    const handleClick = (): void => {
        emit('edit', props.card as CardData)
    }

    const showDeleteDialog = (): void => {
        deleteDialog.value = true
    }

    const handleDelete = (): void => {
        deleteDialog.value = false
        emit('delete', props.card as CardData)
    }

    const emitSelectionChange = (): void => {
        emit('selection-change', internalSelected.value)
    }
</script>

<style scoped>
    .card-container {
        width: 100%;
        display: flex;
        flex-direction: row;
        align-items: center;
        flex: 1 1 0;
    }

    .checkbox-column {
        flex-shrink: 0;
        display: flex;
        align-items: flex-start;
        padding-top: 12px;
    }

    .card-compact {
        cursor: pointer;
        transition: all 0.3s ease;
        flex-grow: 1;
    }

    .card-compact:hover {
        transform: translateY(-2px);
    }
</style>
