<template>
    <div
        class="card-container d-flex align-center"
        :class="[rtlClasses, { 'ga-3': multiSelectActive && showSelectionCheckbox }]"
    >
        <!-- Checkbox outside card to prevent triggering card click -->
        <div
            v-if="multiSelectActive && showSelectionCheckbox"
            class="checkbox-column"
            @click.stop
        >
            <v-checkbox
                v-model="internalSelected"
                :aria-label="resolvedCheckboxLabel"
                density="compact"
                hide-details
                @update:model-value="emitSelectionChange"
            />
        </div>

        <!-- Card content -->
        <v-hover v-slot="{ isHovering, props: hoverProps }">
            <v-card
                v-bind="hoverProps"
                class="base-card card-item mb-1 flex-grow-1"
                :class="[cardClass, { 'selected-item': internalSelected }]"
                :elevation="0"
                tabindex="0"
                :data-id="cardId"
                @click="handleCardClick"
            >
                <v-card-text class="base-card__body">
                    <!-- Content slot -->
                    <div>
                        <slot
                            name="content"
                            :is-hovering="isHovering"
                        />
                    </div>
                    <!-- Actions slot (always visible if multiselect is not active) -->
                    <div
                        v-if="!multiSelectActive && slots['actions']"
                        class="d-flex ga-1 mt-2 justify-end"
                    >
                        <slot name="actions" />
                    </div>
                </v-card-text>
            </v-card>
        </v-hover>
    </div>
</template>

<script setup lang="ts">
    import { computed, ref, watch, useSlots } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRtl } from 'vuetify'

    const slots = useSlots()

    const props = defineProps({
        cardId: {
            type: [String, Number],
            default: undefined
        },
        multiSelectActive: {
            type: Boolean,
            default: false
        },
        showSelectionCheckbox: {
            type: Boolean,
            default: true
        },
        checkboxLabel: {
            type: String,
            default: undefined
        },
        preselected: {
            type: Boolean,
            default: false
        },
        cardClass: {
            type: [String, Object],
            default: ''
        }
    })

    const emit = defineEmits<{
        (e: 'card-click'): void
        (e: 'selection-change', selected: boolean): void
    }>()

    const { t } = useI18n()
    const { rtlClasses } = useRtl()
    const resolvedCheckboxLabel = computed(() => props.checkboxLabel ?? t('common.select'))
    const internalSelected = ref<boolean>(props.preselected)

    // Watch preselected prop and sync with internalSelected
    watch(
        () => props.preselected,
        (newValue: boolean) => {
            internalSelected.value = newValue
        }
    )

    const handleCardClick = (): void => {
        emit('card-click')
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

    .card-item {
        overflow: hidden;
        border: 1px solid rgba(var(--v-theme-outline), 0.26);
        border-radius: 4px;
        transition:
            border-color 0.18s ease,
            background-color 0.18s ease,
            box-shadow 0.18s ease;
        cursor: pointer;
        width: 100%;
        flex: 1 1 0;
    }

    .card-item:hover {
        border-color: rgba(var(--v-theme-primary), 0.42);
        background: rgba(var(--v-theme-primary), 0.035);
    }

    .base-card__body {
        padding: 0.55rem 0.7rem !important;
    }
</style>

<style>
    /* Card deletion/transition animations - non-scoped to apply to TransitionGroup children */
    .card-list-move,
    .card-list-enter-active,
    .card-list-leave-active {
        transition: all 0.3s ease;
    }

    .card-list-enter-from {
        opacity: 0;
        transform: translateY(-20px);
    }

    .card-list-leave-to {
        opacity: 0;
        transform: translateX(-30px);
    }

    .v-locale--is-rtl.card-list-leave-to {
        transform: translateX(30px);
    }

    .card-list-leave-active {
        position: absolute;
        width: 100%;
    }

    .review-list__row {
        position: relative;
        margin-bottom: 0 !important;
        border-color: var(--review-list-border) !important;
        border-inline-width: 0 !important;
        border-bottom-width: 0 !important;
        border-radius: 0 !important;
        background: var(--review-list-row) !important;
        box-shadow: none !important;
    }

    /* Selected state overrides default background with same specificity */
    .review-list__row.selected-item {
        background: var(--review-list-row-selected) !important;
    }

    .review-list__row::before {
        content: '';
        position: absolute;
        inset: 0;
        background: rgba(var(--v-theme-primary), 0);
        transition: background 0.18s ease;
        pointer-events: none;
    }

    .review-list__row:hover::before,
    .review-list__row:focus-visible::before {
        background: rgba(var(--v-theme-primary), 0.05);
    }

    .review-list__row::after {
        position: absolute;
        z-index: 1;
        inset: 0;
        border: 1px solid transparent;
        border-radius: inherit;
        content: '';
        pointer-events: none;
    }

    .review-list__row:hover::after,
    .review-list__row:focus-visible::after {
        border-color: rgba(var(--v-theme-primary), 0.52);
    }

    .assess-list > :first-child .review-list__row,
    .analyze-list > :first-child .review-list__row,
    .publish-list > :first-child .review-list__row {
        border-start-start-radius: 4px !important;
        border-start-end-radius: 4px !important;
    }

    .assess-list > :last-child .review-list__row,
    .analyze-list > :last-child .review-list__row,
    .publish-list > :last-child .review-list__row {
        border-bottom-width: 1px !important;
        border-end-start-radius: 4px !important;
        border-end-end-radius: 4px !important;
    }
</style>
