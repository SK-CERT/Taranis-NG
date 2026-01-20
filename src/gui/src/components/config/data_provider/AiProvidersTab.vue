<template>
    <v-container>
        <v-data-table :headers="headers" :items="records" :items-per-page="-1" item-key="id" sort-by="name"
                      class="elevation-1" :search="search" :clickable="false" @click.stop disable-pagination hide-default-footer>
            <template v-slot:top>
                <v-row v-bind="UI.TOOLBAR.ROW">
                    <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                        <v-tooltip top>
                            <template v-slot:activator="{ on, attrs }">
                                <v-icon color="blue" v-bind="attrs" v-on="on" class="ml-2">
                                    {{ UI.ICON.HELP }}
                                </v-icon>
                            </template>
                            <span>{{ $t('data_provider.ai_providers.tab_description') }}</span>
                        </v-tooltip>
                    </v-col>
                    <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                        <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="search" :label="$t('toolbar_filter.search')"
                                      single-line hide-details></v-text-field>
                    </v-col>
                    <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                        <v-btn v-bind="UI.BUTTON.ADD_NEW" @click="addItem">
                            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                            <span>{{ $t('common.add_btn') }}</span>
                        </v-btn>
                    </v-col>
                </v-row>

                <AiProviderEditDialog v-model="dialogEdit"
                                      :edited-item="editedItem"
                                      :edited-index="editedIndex"
                                      @save="saveRecord"
                                      @close="closeEdit" />

                <MessageBox v-model="dialogDelete"
                            @yes="deleteRecord"
                            @cancel="closeDelete"
                            :title="$t('common.messagebox.delete')"
                            :message="editedItem.name"
                            :alert=true>
                </MessageBox>
            </template>

            <template v-slot:item.updated_at="{ item }">
                <span>{{ formatDate(item.updated_at) }}</span>
            </template>

            <template v-slot:item.api_key="{ item }">
                <span>{{ item.api_key ? '••••••••' : '' }}</span>
            </template>

            <template v-slot:item.actions="{ item }">
                <EditButton small
                            class="mr-2"
                            @edit="editItem(item)" />
                <DeleteButton small
                              @delete="deleteItem(item)" />
            </template>

        </v-data-table>
    </v-container>
</template>

<script>
    import { createNewAiProvider, updateAiProvider, deleteAiProvider } from "@/api/config";
    import Permissions from "@/services/auth/permissions";
    import AiProviderEditDialog from "./AiProviderEditDialog.vue";
    import ProviderTabMixin from "./provider_tab_mixin";

    export default {
        name: "AiProvidersTab",
        mixins: [ProviderTabMixin],
        components: {
            AiProviderEditDialog
        },
        data() {
            return {
                headers: [
                    { text: this.$t('ai_provider.name'), value: 'name' },
                    { text: this.$t('ai_provider.api_type'), value: 'api_type' },
                    { text: this.$t('ai_provider.api_url'), value: 'api_url' },
                    { text: this.$t('settings.api_key'), value: 'api_key', sortable: false, filterable: false },
                    { text: this.$t('ai_provider.model'), value: 'model' },
                    { text: this.$t('settings.updated_by'), value: 'updated_by' },
                    { text: this.$t('settings.updated_at'), value: 'updated_at', filterable: false },
                    { text: this.$t('settings.actions'), value: 'actions', sortable: false },
                ]
            };
        },
        methods: {
            getDefaultItem() {
                return {
                    id: -1,
                    name: "Ollama - llama3:8b",
                    api_type: "openai",
                    api_url: "http://localhost:11434/v1",
                    api_key: "secret",
                    model: "llama3:8b"
                };
            },

            getMessageKey(key) {
                return `ai_provider.${key}`;
            },

            createProvider(data) {
                return createNewAiProvider(data);
            },

            updateProvider(data) {
                return updateAiProvider(data);
            },

            deleteProvider(data) {
                return deleteAiProvider(data);
            },

            fetchRecords() {
                if (this.checkPermission(Permissions.CONFIG_AI_ACCESS)) {
                    this.$store.dispatch('getAllAiProviders', { search: '' }).then(() => {
                        this.initializeDateFormat();
                        this.records = this.$store.getters.getAiProviders.items;
                    });
                }
            }
        }
    }
</script>
