<template>
    <v-btn icon :size="size" :variant="variant" :disabled="disabled" :title="title" @click="handleClick">
        <v-icon :color="color" :size="icon_size">
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
     * Predefined actions: delete, edit, publish, remove, open, open_source
     * For special cases (e.g., conditional icons, complex states), use v-btn directly.
     */
    import { BUTTON_CONFIGS, ICONS } from '@/config/ui-constants'

    type ActionType = 'delete' | 'edit' | 'publish' | 'remove' | 'open' | 'open_source' | 'lock'
    type ButtonVariant = 'text' | 'flat' | 'plain' | 'outlined' | 'elevated' | 'tonal'
    type ActionConfig = {
        icon?: string
        color?: string
        variant?: ButtonVariant
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
                !value || ['delete', 'edit', 'publish', 'remove', 'open', 'open_source', 'lock'].includes(value)
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
        }
    })

    const emit = defineEmits(['click'])

    // Get configuration based on action type or use custom props
    const config: ActionConfig = props.action
        ? (BUTTON_CONFIGS[(props.action as ActionType).toUpperCase() as keyof typeof BUTTON_CONFIGS] as ActionConfig)
        : {}

    // Use config defaults, fallback to props, then to reasonable defaults
    const icon = props.icon || config.icon || ICONS.HELP
    const color = props.color || config.color || 'primary'
    const variant = ((props.variant as ButtonVariant | null) || config.variant || 'text') as ButtonVariant
    const disabled = props.action === 'lock' ? true : props.disabled

    const handleClick = (event: MouseEvent): void => {
        if (!disabled) {
            emit('click', event)
        }
    }
</script>
