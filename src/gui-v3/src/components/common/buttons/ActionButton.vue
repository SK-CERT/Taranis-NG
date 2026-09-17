<template>
    <v-btn
        icon
        :size="size"
        :variant="variant"
        :disabled="disabled"
        :loading="loading"
        :title="title"
        @click="handleClick"
    >
        <v-icon
            :color="color"
            :size="icon_size"
        >
            {{ icon }}
        </v-icon>
    </v-btn>
</template>

<script setup lang="ts">
    /**
     * ActionButton - Centralized action button component
     *
     * Provides consistent styling for common action buttons across the application.
     * Inspired by Vue2's UI.ICON constants for maintaining visual consistency.
     *
     * Usage:
     *   <ActionButton action="delete" :title="t('common.delete')" @click="handleDelete" />
     *   <ActionButton action="edit" :title="t('common.edit')" @click="handleEdit" />
     *   <ActionButton icon="mdi-custom" color="primary" @click="custom" />
     *
     * Predefined actions: delete, edit, publish, remove, open, open_source, collect
     * For special cases (e.g., conditional icons, complex states), use v-btn directly.
     */
    import { BUTTON_CONFIGS, ICONS } from '@/config/ui-constants'
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'

    type ActionType = 'delete' | 'edit' | 'publish' | 'remove' | 'open' | 'open_source' | 'lock' | 'collect'
    type ButtonVariant = 'text' | 'flat' | 'plain' | 'outlined' | 'elevated' | 'tonal'
    type ActionConfig = {
        icon?: string
        color?: string
        variant?: ButtonVariant
        titleKey?: string
    }

    const props = defineProps({
        /**
         * Action type - matches BUTTON_CONFIGS keys (delete, edit, publish, etc.)
         * If provided, uses predefined configuration
         */
        action: {
            type: String,
            default: null,
            validator: (value: string | null) =>
                !value || ['delete', 'edit', 'publish', 'remove', 'open', 'open_source', 'lock', 'collect'].includes(value)
        },
        /**
         * Custom icon override (if not using action presets)
         */
        icon: {
            type: String,
            default: null
        },
        /**
         * Button color
         */
        color: {
            type: String,
            default: null
        },
        /**
         * Button variant
         */
        variant: {
            type: String,
            default: null
        },
        /**
         * Button size
         */
        size: {
            type: String,
            default: 'small'
        },
        /**
         * Icon size
         */
        icon_size: {
            type: String,
            default: 'large'
        },
        /**
         * Disabled state
         */
        disabled: {
            type: Boolean,
            default: false
        },
        /**
         * Tooltip title
         */
        title: {
            type: String,
            default: ''
        },
        /**
         * Shows a spinner and blocks clicks while the action is in flight
         */
        loading: {
            type: Boolean,
            default: false
        }
    })

    const emit = defineEmits(['click'])
    const { t } = useI18n()

    // Get configuration based on action type or use custom props.
    // These are computed rather than read once at setup: a caller may drive any of them from
    // state that changes while the button stays mounted - a toolbar toggle that switches colour
    // when selection mode turns on, a select-all that swaps its icon, a row action that becomes
    // available once its source stops collecting. Read once, such a button keeps whatever it was
    // given on the frame it happened to mount.
    const config = computed<ActionConfig>(() =>
        props.action ? (BUTTON_CONFIGS[(props.action as ActionType).toUpperCase() as keyof typeof BUTTON_CONFIGS] as ActionConfig) : {}
    )

    // Use config defaults, fallback to props, then to reasonable defaults
    const icon = computed(() => props.icon || config.value.icon || ICONS.HELP)
    const color = computed(() => props.color || config.value.color || 'primary')
    const variant = computed(() => ((props.variant as ButtonVariant | null) || config.value.variant || 'text') as ButtonVariant)
    // Title: explicit prop wins, otherwise translate the action config's title key, so callers
    // that render <ActionButton action="delete" /> without :title still get a correct tooltip
    // (CardCompact omits it; its button would otherwise have title="", breaking button[title=]
    // selectors and leaving the tooltip empty).
    const title = computed(() => props.title || (config.value.titleKey ? t(config.value.titleKey) : ''))
    const disabled = computed(() => (props.action === 'lock' ? true : props.disabled))

    const handleClick = (event: MouseEvent): void => {
        // v-btn already swallows clicks while loading, but the guard keeps the contract explicit
        // and testable rather than relying on Vuetify's internals.
        if (!disabled.value && !props.loading) {
            emit('click', event)
        }
    }
</script>
