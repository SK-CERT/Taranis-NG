<template>
    <div>
        <!-- TODO: Implement remote attribute container -->
        <!-- Phase 3: Abstract dispatcher for remote read-only attributes -->
        <!-- Handle: RemoteAttributeString, RemoteAttributeAttachment variants -->
        <component
            :is="getRemoteComponentName(attributeGroup.attribute?.attribute_type)"
            v-if="getRemoteComponentName(attributeGroup.attribute?.attribute_type)"
            :attribute-group="attributeGroup"
            :report-item-id="reportItemId"
        />
        <div v-else class="alert alert-warning">Unknown attribute type: {{ attributeGroup.attribute?.attribute_type }}</div>
    </div>
</template>

<script setup lang="ts">
    import RemoteAttributeString from './RemoteAttributeString.vue'
    import RemoteAttributeAttachment from './RemoteAttributeAttachment.vue'

    type RemoteAttributeGroup = {
        attribute?: {
            attribute_type?: string
            [key: string]: unknown
        }
        [key: string]: unknown
    }

    const props = defineProps<{
        attributeGroup: RemoteAttributeGroup
        reportItemId: number
    }>()

    const getRemoteComponentName = (type: string | undefined): unknown => {
        // TODO: Map attribute types to remote components
        // Phase 3: Add mappings as remote variants are created
        const componentMap: Record<string, unknown> = {
            text: RemoteAttributeString,
            string: RemoteAttributeString,
            attachment: RemoteAttributeAttachment
            // TODO: Add more as needed
        }
        return (type && componentMap[type]) || null
    }
</script>

<style scoped>
    /* TODO: Add remote container styling if needed */
</style>
