<template>
    <v-container>
        <v-card class="mt-6">
            <v-data-table :headers="headers" :items="records" :items-per-page="-1" item-key="id" sort-by="entity_type"
                          class="elevation-1" :search="search" disable-pagination hide-default-footer>
                <template v-slot:top>
                    <v-row v-bind="UI.TOOLBAR.ROW">
                        <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                            <v-tooltip right>
                                <template v-slot:activator="{ on, attrs }">
                                    <v-icon color="blue" v-bind="attrs" v-on="on" class="ml-2">
                                        {{ UI.ICON.HELP }}
                                    </v-icon>
                                </template>
                                <span>{{ $t('workflow.state_workflow.tab_description') }}</span>
                            </v-tooltip>
                        </v-col>
                        <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                            <v-select v-model="filterEntityType" :items="entityTypeFilter"
                                      :label="$t('workflow.state_workflow.filter_by_entity_type')" clearable dense
                                      hide-details class="mr-4">
                                <template v-slot:item="{ item }">
                                    {{ item.text }}
                                </template>
                                <template v-slot:selection="{ item }">
                                    {{ item.text }}
                                </template>
                            </v-select>
                        </v-col>
                        <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                            <v-btn v-bind="UI.BUTTON.ADD_NEW" @click="addItem">
                                <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                <span>{{ $t('common.add_btn') }}</span>
                            </v-btn>
                        </v-col>
                    </v-row>

                    <StateEntityTypeEditDialog v-model="dialogEdit" :edited-item="editedItem"
                                               :edited-index="editedIndex" :is-editable="isEditable" :available-states="availableStates"
                                               @save="saveRecord" @close="closeEdit" />

                    <MessageBox v-model="dialogDelete"
                                @yes="deleteRecord"
                                @cancel="closeDelete"
                                :title="$t('common.messagebox.delete')">
                    </MessageBox>
                </template>

                <template v-slot:item.entity_type="{ item }">
                    <v-chip label :color="getEntityTypeColor(item.entity_type)">
                        <v-icon left>{{ getEntityTypeIcon(item.entity_type) }}</v-icon>
                        {{ $t('workflow.entity_types.' + item.entity_type) }}
                    </v-chip>
                </template>

                <template v-slot:item.state_name="{ item }">
                    <v-icon left :color="item.state.color">{{ item.state.icon }}</v-icon>
                    {{ $te('workflow.states.' + item.state.display_name) ? $t('workflow.states.' +
                        item.state.display_name) : item.state.display_name }}
                </template>

                <template v-slot:item.state_type="{ item }">
                    <v-chip label :color="'grey'">
                        <v-icon left>{{ getStateTypeIcon(item.state_type) }}</v-icon>
                        {{ $t('workflow.state_types.' + item.state_type) }}
                    </v-chip>
                </template>

                <template v-slot:item.is_active="{ item }">
                    <v-icon :color="item.is_active ? 'green' : 'error'">
                        {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
                    </v-icon>
                </template>

                <template v-slot:item.actions="{ item }">
                    <v-tooltip top>
                        <template v-slot:activator="{ on, attrs }">
                            <v-icon small class="mr-2" v-bind="attrs" v-on="on" @click="item.editable && editItem(item)" :color="item.editable ? 'primary' : 'warning'">
                                {{ item.editable ? 'mdi-pencil' : 'mdi-lock-outline' }}
                            </v-icon>
                        </template>
                        <span>{{ item.editable ? $t('common.edit') : $t('workflow.state_workflow.cannot_edit_system_association') }}</span>
                    </v-tooltip>
                    <v-tooltip top>
                        <template v-slot:activator="{ on, attrs }">
                            <v-icon small v-bind="attrs" v-on="on" @click="item.editable && deleteItem(item)" :color="item.editable ? 'error' : 'warning'">
                                {{ item.editable ? 'mdi-delete-outline' : 'mdi-lock-outline' }}
                            </v-icon>
                        </template>
                        <span>
                            {{ item.editable ? $t('common.delete') : $t('workflow.state_workflow.cannot_delete_system_association') }}
                        </span>
                    </v-tooltip>
                </template>
            </v-data-table>
        </v-card>
    </v-container>
</template>

<script>
    import { createNewStateEntityType, updateStateEntityType, deleteStateEntityType } from "@/api/config";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import StateEntityTypeEditDialog from "./StateEntityTypeEditDialog.vue";
    import MessageBox from "@/components/common/MessageBox.vue";

    export default {
        name: "StateWorkflowTab",
        components: {
            MessageBox,
            StateEntityTypeEditDialog,
        },
        data() {
            return {
                search: "",
                filterEntityType: null,
                headers: [
                    { text: this.$t('workflow.state_workflow.entity_type'), value: 'entity_type' },
                    { text: this.$t('workflow.state_workflow.state'), value: 'state_name' },
                    { text: this.$t('workflow.state_workflow.state_type'), value: 'state_type' },
                    { text: this.$t('workflow.state_workflow.is_active'), value: 'is_active' },
                    { text: this.$t('workflow.state_workflow.sort_order'), value: 'sort_order' },
                    { text: this.$t('settings.actions'), value: 'actions', sortable: false },
                ],
                records: [],
                dialogEdit: false,
                dialogDelete: false,
                editedIndex: -1,
                editedItem: {
                    id: -1,
                    entity_type: "",
                    state_id: null,
                    state_type: "normal",
                    is_active: true,
                    editable: true,
                    sort_order: 0
                },
                defaultItem: {
                    id: -1,
                    entity_type: "",
                    state_id: null,
                    state_type: "normal",
                    is_active: true,
                    editable: true,
                    sort_order: 0
                },
                entityTypeFilter: [
                    { text: this.$t('workflow.entity_types.product'), value: 'product' },
                    { text: this.$t('workflow.entity_types.report_item'), value: 'report_item' },
                ]
            };
        },
        mixins: [AuthMixin],
        computed: {
            isEditable() {
                return this.editedIndex === -1 || this.editedItem.editable;
            },
            availableStates() {
                return (this.$store.getters.getStateDefinitions && this.$store.getters.getStateDefinitions.items) || [];
            }
        },
        watch: {
            filterEntityType() {
                this.fetchRecords();
            }
        },
        methods: {
            getContrastColor(hexColor) {
                if (!hexColor) return 'black';
                const r = parseInt(hexColor.slice(1, 3), 16);
                const g = parseInt(hexColor.slice(3, 5), 16);
                const b = parseInt(hexColor.slice(5, 7), 16);
                const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
                return luminance > 0.5 ? 'black' : 'white';
            },

            getEntityTypeColor(entityType) {
                const colors = {
                    'report_item': '#2196F3',
                    'product': '#4CAF50'
                };
                return colors[entityType] || 'grey';
            },

            getEntityTypeIcon(entityType) {
                const icons = {
                    'report_item': 'mdi-file-document',
                    'product': 'mdi-package-variant'
                };
                return icons[entityType] || 'mdi-help';
            },

            getStateTypeIcon(stateType) {
                const icons = {
                    'normal': 'mdi-circle',
                    'initial': 'mdi-star',
                    'final': 'mdi-flag-checkered'
                };
                return icons[stateType] || 'mdi-help';
            },

            fetchRecords() {
                if (this.checkPermission(Permissions.CONFIG_WORKFLOW_ACCESS)) {
                    // First ensure we have state definitions loaded
                    this.$store.dispatch('getAllStateDefinitions', { search: '' }).then(() => {
                        // Then fetch state-entity type associations
                        const filter = {};
                        if (this.filterEntityType) {
                            filter.entity_type = this.filterEntityType;
                        }

                        this.$store.dispatch('getAllStateEntityTypes', filter).then(() => {
                            this.records = this.$store.getters.getStateEntityTypes.items;
                        });
                    });
                }
            },

            addItem() {
                this.editedIndex = -1;
                this.editedItem = Object.assign({}, this.defaultItem);
                this.dialogEdit = true;
            },

            editItem(item) {
                this.editedIndex = this.records.indexOf(item);
                this.editedItem = Object.assign({}, item);
                this.dialogEdit = true;
            },

            deleteItem(item) {
                if (!item.editable) {
                    this.showMsg("error", "workflow.cannot_delete_system_association");
                    return;
                }
                this.editedIndex = this.records.indexOf(item);
                this.editedItem = Object.assign({}, item);
                this.dialogDelete = true;
            },

            closeEdit() {
                this.dialogEdit = false;
                this.$nextTick(() => {
                    this.editedItem = Object.assign({}, this.defaultItem);
                    this.editedIndex = -1;
                });
            },

            closeDelete() {
                this.dialogDelete = false;
                this.$nextTick(() => {
                    this.editedItem = Object.assign({}, this.defaultItem);
                    this.editedIndex = -1;
                });
            },

            saveRecord(submitData) {
                if (this.editedIndex > -1) {
                    updateStateEntityType(submitData).then((response) => {
                        this.editedItem = Object.assign({}, response.data);
                        Object.assign(this.records[this.editedIndex], this.editedItem);
                        this.showMsg("success", "workflow.state_workflow.successful_edit");
                        this.closeEdit();
                        this.fetchRecords(); // Refresh to get updated state info
                    }).catch(() => {
                        this.showMsg("error", "workflow.state_workflow.error");
                    });
                } else {
                    createNewStateEntityType(submitData).then(() => {
                        this.showMsg("success", "workflow.state_workflow.successful");
                        this.closeEdit();
                        this.fetchRecords(); // Refresh to get complete data
                    }).catch((error) => {
                        if (error.response && error.response.status === 409) {
                            this.showMsg("error", "workflow.state_workflow.association_already_exists");
                        } else {
                            this.showMsg("error", "workflow.state_workflow.error");
                        }
                    });
                }
            },

            deleteRecord() {
                if (!this.editedItem.editable) {
                    this.showMsg("error", "workflow.state_workflow.cannot_delete_system_association");
                    this.closeDelete();
                    return;
                }

                deleteStateEntityType(this.editedItem).then(() => {
                    this.records.splice(this.editedIndex, 1);
                    this.showMsg("success", "workflow.state_workflow.remove");
                    this.closeDelete();
                }).catch(() => {
                    this.showMsg("error", "workflow.state_workflow.removed_error");
                });
            },

            showMsg(type, message) {
                this.$root.$emit('notification', { type: type, loc: message });
            },
        },
        mounted() {
            this.fetchRecords();
        }
    }
</script>
