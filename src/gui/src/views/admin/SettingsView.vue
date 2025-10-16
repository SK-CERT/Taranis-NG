<template>
    <SettingsTable :glob_setting="true"></SettingsTable>
</template>
<script>
    import SettingsTable from "@/components/config/SettingsTable.vue";

    export default {
        name: "GlobalSettings",
        components: {
            SettingsTable
        },
    }
</script>
