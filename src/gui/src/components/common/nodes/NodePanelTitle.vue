<template>
    <v-expansion-panel-title>
        <v-icon
            :icon="node.status === 'green' ? 'mdi-circle' : 'mdi-circle-outline'"
            :color="statusColor"
            size="x-small"
            class="me-2"
            :title="statusTitle"
        />
        <span class="font-weight-medium">{{ node.name }}</span>
        <span class="text-medium-emphasis ms-2">({{ count }})</span>
        <span class="text-medium-emphasis ms-2">{{ node.description }}</span>
        <v-spacer />
        <!-- The panel title is itself a button, so anything interactive inside it has to stop the
             click travelling on - otherwise adding a child collapses the panel it belongs to. -->
        <span
            class="me-1"
            @click.stop
        >
            <slot name="add" />
        </span>
        <ActionButton
            v-if="canUpdate"
            action="edit"
            @click.stop="emit('edit', node)"
        />
        <ActionButton
            v-if="canDelete"
            action="delete"
            @click.stop="emit('delete', node)"
        />
    </v-expansion-panel-title>
</template>

<script setup lang="ts">
    /**
     * The title bar of one node's expansion panel.
     *
     * Public webs and OSINT sources are both "a node, and the things it is responsible for", and
     * both drew this bar for themselves: the same health dot, name, count, description, add
     * button and edit/delete pair, differing only in which of them had the tooltip and which used
     * the house button style. Whatever each node contains is the tab's business; how a node
     * announces itself is this component's.
     */
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'

    type NodeItem = {
        id: string | number
        name?: string
        description?: string
        status?: string
        last_seen?: string
    }

    const props = withDefaults(
        defineProps<{
            node: NodeItem
            count?: number
            canUpdate?: boolean
            canDelete?: boolean
        }>(),
        { count: 0, canUpdate: false, canDelete: false }
    )

    const emit = defineEmits<{
        (e: 'edit', node: NodeItem): void
        (e: 'delete', node: NodeItem): void
    }>()

    const { t } = useI18n()

    // Health status dot: green (reachable) / orange (late) / red (unreachable). Driven by the
    // node's last_seen via the core periodic ping; a node that has never answered is red, never
    // green.
    const statusColor = computed(() => (props.node.status === 'green' ? 'success' : props.node.status === 'orange' ? 'warning' : 'error'))

    const statusTitle = computed(() => {
        if (!props.node.last_seen) return t('common.node_status.never_seen')
        const key = props.node.status === 'green' ? 'alive' : props.node.status === 'orange' ? 'late' : 'unreachable'
        return `${t(`common.node_status.${key}`)} (${t('common.node_status.last_seen')}: ${props.node.last_seen})`
    })
</script>
