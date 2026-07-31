<template>
    <div>
        <!-- Publish has no navigation sidebar -->
    </div>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useTheme } from 'vuetify'

    const { global: themeGlobal } = useTheme()

    const isDark = computed(() => themeGlobal.name.value === 'dark')
    const iconColor = computed(() => (isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)'))
</script>

<style scoped>
    .v-list-item {
        min-height: auto;
    }
</style>
