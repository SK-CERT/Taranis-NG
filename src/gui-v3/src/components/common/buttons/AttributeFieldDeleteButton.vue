<template>
    <!-- Delete button intended for a field's append-inner slot.
         tabindex -1 keeps it out of the tab order. mousedown.stop.prevent stops the host field
         from reacting (e.g. a v-select opening its menu / a text field focusing) before the
         click fires; click.stop then keeps the click from bubbling to the field. -->
    <v-btn
        v-if="visible"
        icon
        variant="text"
        density="compact"
        tabindex="-1"
        :title="t('report_item.tooltip.delete_value')"
        @mousedown.stop.prevent
        @click.stop="emit('delete')"
    >
        <v-icon>{{ ICONS.CLOSE }}</v-icon>
    </v-btn>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    defineProps<{ visible?: boolean }>()
    const emit = defineEmits<{ (e: 'delete'): void }>()
    const { t } = useI18n()
</script>
