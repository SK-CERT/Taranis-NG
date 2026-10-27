<template>
    <v-icon
        v-if="tag && tag.icon"
        :color="tag.color || undefined"
        :title="tagName(tag)"
        size="small"
        :data-test="`tab-status-${status}`"
    >
        {{ tag.icon }}
    </v-icon>
</template>

<script setup lang="ts">
    import { computed, onMounted } from 'vue'
    import type { TagEntityType } from '@/api/tags'
    import { useTagLabels } from '@/composables/useTagLabels'
    import { useTagsStore } from '@/stores/tags'

    /** The translation status of one language as its built-in tag's icon, e.g. on a language tab. */

    const props = defineProps<{ entityType: TagEntityType; status: string | null | undefined }>()

    const tagsStore = useTagsStore()
    const { tagName } = useTagLabels()

    const tag = computed(() => (props.status ? tagsStore.system(props.entityType, props.status) : undefined))

    onMounted(() => void tagsStore.load(props.entityType))
</script>
