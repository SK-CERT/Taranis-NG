<template>
    <div class="remote-values">
        <div
            v-for="value in attributeGroup.attributes"
            :key="value.id"
            class="remote-values__item"
        >
            {{ value.value }}
        </div>
    </div>
</template>

<script setup lang="ts">
    type RemoteAttributeValue = {
        id: number | string
        value?: string
    }

    defineProps<{
        attributeGroup: { attributes: RemoteAttributeValue[] }
        reportItemId: number
    }>()
</script>

<style scoped>
    .remote-values {
        display: grid;
        gap: 0.5rem;
        white-space: pre-wrap;
        overflow-wrap: anywhere;
    }

    .remote-values__item + .remote-values__item {
        padding-top: 0.5rem;
        border-top: 1px solid rgba(var(--v-theme-outline), 0.2);
    }
</style>
