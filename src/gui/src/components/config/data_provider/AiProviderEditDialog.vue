<template>
    <ProviderEditDialog
        v-model="value"
        :edited-item="editedItem"
        :edited-index="editedIndex"
        provider-type="ai_provider"
        @save="$emit('save', $event)"
        @close="$emit('close')"
    >
        <template v-slot="{ localItem, showApiKey, toggleApiKey }">
            <v-row>
                <v-col cols="8">
                    <v-text-field v-model="localItem.name" :label="$t('ai_provider.name')"
                        :rules="[v => !!v || $t('error.validation')]" required></v-text-field>
                </v-col>
                <v-col cols="4">
                    <v-select v-model="localItem.api_type" :items="['openai']"
                        :label="$t('ai_provider.api_type')"></v-select>
                </v-col>
                <v-col cols="12">
                    <v-text-field v-model="localItem.api_url"
                        :label="$t('ai_provider.api_url')"
                        :rules="[v => !!v || $t('error.validation')]" required></v-text-field>
                </v-col>
                <v-col cols="6">
                    <v-text-field v-model="localItem.api_key"
                        :label="$t('settings.api_key')"
                        :type="showApiKey ? 'text' : 'password'"
                        :append-icon="showApiKey ? 'mdi-eye-off' : 'mdi-eye'"
                        @click:append="toggleApiKey"></v-text-field>
                </v-col>
                <v-col cols="6">
                    <v-text-field v-model="localItem.model" :label="$t('ai_provider.model')"
                        :rules="[v => !!v || $t('error.validation')]" required></v-text-field>
                </v-col>
            </v-row>
        </template>
    </ProviderEditDialog>
</template>

<script>
import ProviderEditDialog from "./ProviderEditDialog.vue";

export default {
    name: "AiProviderEditDialog",
    components: {
        ProviderEditDialog
    },
    props: {
        value: Boolean,
        editedItem: Object,
        editedIndex: Number
    }
}
</script>
