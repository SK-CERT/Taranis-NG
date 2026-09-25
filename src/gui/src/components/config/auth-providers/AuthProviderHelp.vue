<template>
    <p
        :id="id"
        class="auth-provider-help text-caption text-medium-emphasis mb-0"
    >
        <slot />
    </p>
</template>

<script setup lang="ts">
    defineProps<{
        id?: string
    }>()
</script>

<style scoped>
    .auth-provider-help {
        min-height: 1.25rem;
        line-height: 1.25rem;
    }
</style>
