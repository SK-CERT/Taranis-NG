<template>
    <v-container>
        <v-data-table :headers="headers" :items="records" :items-per-page="-1" item-key="id" sort-by="name"
            class="elevation-1" :search="search" :clickable="false" @click.stop disable-pagination hide-default-footer>
            <template v-slot:top>
                <v-row v-bind="UI.TOOLBAR.ROW">
                    <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                        <div :class="UI.CLASS.toolbar_filter_title">{{ $t('nav_menu.data_providers') }}</div>
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

                <v-dialog v-model="dialogEdit" max-width="900px">
                    <v-card>
                        <v-card-title>
                            <span class="text-h5">{{ dialogEditTitle }}</span>
                        </v-card-title>
                        <v-card-text>
                            <v-form ref="form">
                                <v-container>
                                    <v-row>
                                        <v-col cols="8">
                                            <v-text-field v-model="editedItem.name" :label="$t('data_provider.name')"
                                                :rules="[v => !!v || $t('error.validation')]" required></v-text-field>
                                        </v-col>
                                        <v-col cols="4">
                                            <v-select v-model="editedItem.api_type"
                                                :items="['CVE', 'CWE', 'CPE', 'EUVD', 'EPSS']"
                                                :label="$t('data_provider.api_type')"></v-select>
                                        </v-col>
                                        <v-col cols="12">
                                            <v-text-field v-model="editedItem.api_url"
                                                :label="$t('data_provider.api_url')"
                                                :rules="[v => !!v || $t('error.validation')]" required></v-text-field>
                                        </v-col>
                                         <v-col cols="6">
                                            <v-text-field v-model="editedItem.api_key"
                                                :label="$t('settings.api_key')"
                                                :type="showApiKey ? 'text' : 'password'"></v-text-field>
                                        </v-col>
                                        <v-col cols="6">
                                            <v-text-field v-model="editedItem.user_agent"
                                                :label="$t('data_provider.user_agent')"></v-text-field>
                                        </v-col>
                                        <v-col cols="6">
                                            <v-text-field v-model="editedItem.web_url"
                                                :label="$t('data_provider.web_url')"></v-text-field>
                                        </v-col>
                                    </v-row>
                                </v-container>
                            </v-form>
                        </v-card-text>

                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="blue darken-1" text @click="closeEdit"> {{ $t('common.cancel') }} </v-btn>
                            <v-btn color="blue darken-1" text @click="saveRecord"> {{ $t('common.save') }} </v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>

                <v-dialog v-model="dialogDelete" max-width="500px">
                    <v-card>
                        <v-card-title class="text-h5"> {{ $t('common.messagebox.delete') }} </v-card-title>
                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="blue darken-1" text @click="closeDelete"> {{ $t('common.cancel') }} </v-btn>
                            <v-btn color="blue darken-1" text @click="deleteRecord"> {{ $t('common.delete') }} </v-btn>
                            <v-spacer></v-spacer>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </template>

            <template v-slot:item.updated_at="{ item }">
                <span>{{ formatDate(item.updated_at) }}</span>
            </template>

            <template v-slot:item.api_key="{ item }">
                <span>{{ item.api_key ? '••••••••' : '' }}</span>
            </template>

            <template v-slot:item.actions="{ item }">
                <v-tooltip top>
                    <template v-slot:activator="{ on, attrs }">
                        <v-icon small class="mr-2" v-bind="attrs" v-on="on" @click="editItem(item)">
                            mdi-pencil
                        </v-icon>
                    </template>
                    <span>{{ $t('common.edit') }}</span>
                </v-tooltip>
                <v-tooltip top>
                    <template v-slot:activator="{ on, attrs }">
                        <v-icon small v-bind="attrs" v-on="on" @click="deleteItem(item)">
                            mdi-delete
                        </v-icon>
                    </template>
                    <span> {{ $t('common.delete') }} </span>
                </v-tooltip>
            </template>


        </v-data-table>
    </v-container>
</template>

<script>
import { createNewDataProvider, updateDataProvider, deleteDataProvider } from "@/api/config";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import { format } from 'date-fns';
import Settings, { getSetting } from "@/services/settings";

export default {

    name: "DataProviderTable",
    props: {},
    data() {
        return {
            search: "",
            headers: [
                { text: this.$t('data_provider.name'), value: 'name' },
                { text: this.$t('data_provider.api_type'), value: 'api_type' },
                { text: this.$t('data_provider.api_url'), value: 'api_url' },
                { text: this.$t('settings.api_key'), value: 'api_key' },
                { text: this.$t('data_provider.user_agent'), value: 'user_agent' },
                { text: this.$t('data_provider.web_url'), value: 'web_url' },
                { text: this.$t('settings.updated_by'), value: 'updated_by' },
                { text: this.$t('settings.updated_at'), value: 'updated_at', filterable: false },
                { text: this.$t('settings.actions'), value: 'actions', sortable: false },
            ],
            records: [],
            dialogEdit: false,
            dialogDelete: false,
            editedItem: {
                id: -1,
                name: "",
                api_type: "",
                api_url: "",
                api_key: "",
                user_agent: "",
                web_url: "",
                model: "",
            },
            defaultItem: {
                name: "ENISA EUVD",
                api_type: "EUVD",
                api_url: "https://euvdservices.enisa.europa.eu/api/",
                api_key: "",
                user_agent: "",
                web_url: "https://euvd.enisa.europa.eu/vulnerability/"
            },
            date_format: ""
        };
    },
    mixins: [AuthMixin],
    computed: {
        dialogEditTitle() {
            return this.editedIndex === -1 ? this.$t("data_provider.add_new") : this.$t("data_provider.edit")
        },
    },
    watch: {
        dialogEdit(val) {
            val || this.closeEdit()
        },

        dialogDelete(val) {
            val || this.closeDelete()
        },
    },
    methods: {
        formatDate(dateString) {
            if (dateString) {
                return format(new Date(dateString), this.date_format);
            }
        },

        fetchRecords() {
            if (this.checkPermission(Permissions.CONFIG_DATA_PROVIDER_ACCESS)) {
                this.$store.dispatch('getAllDataProviders', { search: '' }).then(() => {
                    var dateFmt = getSetting(Settings.DATE_FORMAT);
                    var timeFmt = getSetting(Settings.TIME_FORMAT);
                    if (dateFmt != "" && timeFmt != "") {
                        this.date_format = dateFmt + " " + timeFmt;
                    } else {
                        this.date_format = "yyyy-MM-dd HH:mm:ss"; // Default format
                    }

                    this.records = this.$store.getters.getDataProviders.items;
                });
            }
        },

        addItem() {
            this.editedIndex = -1
            this.editedItem = Object.assign({}, this.defaultItem);
            this.dialogEdit = true;
        },

        editItem(item) {
            this.editedIndex = this.records.indexOf(item)
            this.editedItem = Object.assign({}, item)
            this.dialogEdit = true
        },

        deleteItem(item) {
            this.editedIndex = this.records.indexOf(item)
            this.editedItem = Object.assign({}, item)
            this.dialogDelete = true
        },

        closeEdit() {
            this.dialogEdit = false
        },

        closeDelete() {
            this.dialogDelete = false
        },

        saveRecord() {
            if (!this.$refs.form.validate()) return;
            if (this.editedIndex > -1) {
                updateDataProvider(this.editedItem).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    Object.assign(this.records[this.editedIndex], this.editedItem);
                    this.showMsg("success", "data_provider.successful_edit");
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", "data_provider.error");
                })
            } else {
                createNewDataProvider(this.editedItem).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    this.records.push(this.editedItem);
                    this.showMsg("success", "data_provider.successful");
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", "data_provider.error");
                })
            }
        },

        deleteRecord() {
            deleteDataProvider(this.editedItem).then(() => {
                this.records.splice(this.editedIndex, 1);
                this.showMsg("success", "data_provider.remove");
                this.closeDelete();
            }).catch(() => {
                this.showMsg("error", "data_provider.removed_error");
            })
        },

        showMsg(type, message) {
            this.$root.$emit('notification', { type: type, loc: message })
        },

    },
    mounted() {
        this.fetchRecords();
    }
}
</script>
