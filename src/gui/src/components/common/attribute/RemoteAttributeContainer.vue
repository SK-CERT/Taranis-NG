<template>
    <v-card
        variant="outlined"
        class="remote-attribute"
    >
        <v-card-title class="remote-attribute__title">
            {{ attributeGroup.title }}
        </v-card-title>
        <v-divider />
        <v-card-text class="remote-attribute__body">
            <component
                :is="attributeComponent"
                :attribute-group="attributeGroup"
                :report-item-id="reportItemId"
            />
        </v-card-text>
    </v-card>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import RemoteAttributeString from './RemoteAttributeString.vue'
    import RemoteAttributeAttachment from './RemoteAttributeAttachment.vue'

    type RemoteAttributeGroup = {
        title: string
        attributeType?: string
        attributes: Array<{
            id: number | string
            value?: string
            binary_size?: number | null
            binary_description?: string | null
            [key: string]: unknown
        }>
    }

    const props = defineProps<{
        attributeGroup: RemoteAttributeGroup
        reportItemId: number
    }>()

    const attributeComponent = computed(() =>
        props.attributeGroup.attributeType?.toUpperCase() === 'ATTACHMENT' ? RemoteAttributeAttachment : RemoteAttributeString
    )
</script>

<style scoped>
    .remote-attribute__title {
        padding: 0.75rem 1rem;
        font-size: 1rem;
        font-weight: 700;
    }

    .remote-attribute__body {
        padding: 0.75rem 1rem;
    }
</style>
