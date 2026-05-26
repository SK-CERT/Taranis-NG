<template>
    <AttributeItemLayout :add-button="false" :values="attributeGroup.attributes">
        <template #content>
            <div v-for="value in attributeGroup.attributes" :key="value.id" class="remote-value">
                <span class="text-sm text-gray-300">{{ value.value }}</span>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    import AttributeItemLayout from './AttributeItemLayout.vue'

    type RemoteAttributeValue = {
        id: number | string
        value?: string
        [key: string]: unknown
    }

    type RemoteAttributeGroup = {
        attributes: RemoteAttributeValue[]
        [key: string]: unknown
    }

    const props = defineProps<{
        attributeGroup: RemoteAttributeGroup
        reportItemId: number
    }>()

    // TODO: Phase 3 - Add remote-specific features:
    // - Display source/origin information
    // - Show when data came from API feed
    // - Prevent editing with clear UI indication
    // - Link to original source if available
</script>

<style scoped>
    .remote-value {
        width: 100%;
        padding: 8px 0;
    }
</style>
