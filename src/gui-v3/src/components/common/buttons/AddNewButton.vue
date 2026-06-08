<template>
    <v-btn
        v-if="show"
        :prepend-icon="ICONS.PLUS"
        color="primary"
        variant="flat"
        class="add-new-button"
        v-bind="sanitizedAttrs"
        @click="onButtonClick"
    >
        {{ translatedLabel }}
    </v-btn>
</template>

<script setup lang="ts">
    import { computed, useAttrs, type VNodeProps } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const props = defineProps({
        label: {
            type: String,
            default: 'common.add_btn'
        },
        show: {
            type: Boolean,
            default: true
        }
    })

    const { t } = useI18n()
    const attrs = useAttrs()

    const translatedLabel = computed(() => t(props.label))

    // ONLY strip real conflicts (not color)
    const sanitizedAttrs = computed(() => {
        const { onClick, ...rest } = attrs
        return rest
    })

    // proper click forwarding
    const onButtonClick = (event: MouseEvent): void => {
        const clickHandler = (
            attrs as VNodeProps & {
                onClick?: ((e: MouseEvent) => void) | Array<(e: MouseEvent) => void>
            }
        ).onClick

        if (Array.isArray(clickHandler)) {
            clickHandler.forEach((h) => h(event))
        } else if (clickHandler) {
            clickHandler?.(event)
        }
    }
</script>
<style scoped>
    .add-new-button {
        color: rgb(var(--v-theme-on-primary)) !important;
    }
</style>
