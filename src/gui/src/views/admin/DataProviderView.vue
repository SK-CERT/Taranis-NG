<template>
    <v-container fluid>
        <v-tabs v-model="activeTab" background-color="transparent" color="primary">
            <v-tab>{{ $t('nav_menu.data_providers') }}</v-tab>
            <v-tab>{{ $t('nav_menu.ai_providers') }}</v-tab>
        </v-tabs>

        <v-tabs-items v-model="activeTab">
            <v-tab-item>
                <DataProvidersTab v-if="activeTab === 0" />
            </v-tab-item>

            <v-tab-item>
                <AiProvidersTab v-if="activeTab === 1" />
            </v-tab-item>
        </v-tabs-items>
    </v-container>
</template>

<script>
import DataProvidersTab from "@/components/config/data_provider/DataProvidersTab.vue";
import AiProvidersTab from "@/components/config/data_provider/AiProvidersTab.vue";

export default {
    name: "DataProviderView",
    components: {
        DataProvidersTab,
        AiProvidersTab
    },
    data() {
        return {
            activeTab: 0
        };
    }
}
</script>
