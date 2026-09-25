<template>
    <PublicWebNodesTab />
</template>

<script setup lang="ts">
    // Just the nodes and their webs. The Routing & TLS tab that briefly lived
    // here moved to Application Settings - it configures the whole instance
    // (TLS floor, default certificate, HSTS policy), not the public webs alone.
    // Host-scoped settings (per-web HSTS, per-web resolver) are in each web's
    // own dialog.
    import PublicWebNodesTab from '@/components/config/public-web/PublicWebNodesTab.vue'
</script>
