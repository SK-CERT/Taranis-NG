<template>
    <v-container>
        <v-data-table :headers="headers" :items="records" :items-per-page="-1" item-key="id" sort-by="display_name"
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
                            <span>{{ $t('workflow.states.tab_description') }}</span>
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

                <StateEditDialog v-model="dialogEdit" :edited-item="editedItem" :edited-index="editedIndex"
                    :is-editable="isEditable" @save="saveRecord" @close="closeEdit" />

                <StateDeleteDialog v-model="dialogDelete" :edited-item="editedItem" @delete="deleteRecord"
                    @close="closeDelete" />
            </template>

            <template v-slot:item.display_name="{ item }">
                {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) :
                    item.display_name }}
            </template>

            <template v-slot:item.color="{ item }">
                <v-chip :color="item.color" label :text-color="getContrastColor(item.color)">
                    {{ item.color }}
                </v-chip>
            </template>

            <template v-slot:item.icon="{ item }">
                <v-icon :color="item.color">{{ item.icon }}</v-icon>
            </template>

            <template v-slot:item.actions="{ item }">
                <v-tooltip top>
                    <template v-slot:activator="{ on, attrs }">
                        <v-icon small class="mr-2" v-bind="attrs" v-on="on" @click="item.editable && editItem(item)" :color="item.editable ? undefined : 'error'">
                            {{ item.editable ? 'mdi-pencil' : 'mdi-lock' }}
                        </v-icon>
                    </template>
                    <span>{{ item.editable ? $t('common.edit') : $t('workflow.states.cannot_edit_system_state') }}</span>
                </v-tooltip>
                <v-tooltip top>
                    <template v-slot:activator="{ on, attrs }">
                        <v-icon small v-bind="attrs" v-on="on" @click="item.editable && deleteItem(item)" :color="item.editable ? undefined : 'error'">
                            {{ item.editable ? 'mdi-delete' : 'mdi-lock' }}
                        </v-icon>
                    </template>
                    <span>
                        {{ item.editable ? $t('common.delete') : $t('workflow.states.cannot_delete_system_state')}}
                    </span>
                </v-tooltip>
            </template>

        </v-data-table>
    </v-container>
</template>

<script>
import { createNewStateDefinition, updateStateDefinition, deleteStateDefinition } from "@/api/config";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import StateEditDialog from "./StateEditDialog.vue";
import StateDeleteDialog from "./StateDeleteDialog.vue";

export default {
    name: "StatesTab",
    components: {
        StateEditDialog,
        StateDeleteDialog
    },
    data() {
        return {
            search: "",
            headers: [
                { text: this.$t('workflow.states.display_name'), value: 'display_name'},
                { text: this.$t('workflow.states.description'), value: 'description' },
                { text: this.$t('workflow.states.color'), value: 'color' },
                { text: this.$t('workflow.states.icon'), value: 'icon' },
                { text: this.$t('settings.actions'), value: 'actions', sortable: false },
            ],
            records: [],
            dialogEdit: false,
            dialogDelete: false,
            editedIndex: -1,
            editedItem: {
                id: -1,
                display_name: "",
                description: "",
                color: "#2196F3",
                icon: "mdi-circle",
                editable: true,
            },
            defaultItem: {
                display_name: "",
                description: "",
                color: "#2196F3",
                icon: "mdi-circle",
                editable: true,
            },
        };
    },
    mixins: [AuthMixin],
    computed: {
        isEditable() {
            // For new items (editedIndex === -1), always editable
            // For existing items, check the editable flag
            return this.editedIndex === -1 || this.editedItem.editable;
        }
    },
    methods: {
        getContrastColor(hexColor) {
            // Calculate luminance to determine if text should be light or dark
            const r = parseInt(hexColor.slice(1, 3), 16);
            const g = parseInt(hexColor.slice(3, 5), 16);
            const b = parseInt(hexColor.slice(5, 7), 16);
            const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
            return luminance > 0.5 ? 'black' : 'white';
        },

        fetchRecords() {
            if (this.checkPermission(Permissions.CONFIG_WORKFLOW_ACCESS)) {
                this.$store.dispatch('getAllStateDefinitions', { search: '' }).then(() => {
                    this.records = this.$store.getters.getStateDefinitions.items;
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
            if (!item.editable) {
                this.showMsg("error", "states.cannot_delete_system_state");
                return;
            }
            this.editedIndex = this.records.indexOf(item)
            this.editedItem = Object.assign({}, item)
            this.dialogDelete = true
        },

        closeEdit() {
            this.dialogEdit = false
            this.$nextTick(() => {
                this.editedItem = Object.assign({}, this.defaultItem)
                this.editedIndex = -1
            })
        },

        closeDelete() {
            this.dialogDelete = false
            this.$nextTick(() => {
                this.editedItem = Object.assign({}, this.defaultItem)
                this.editedIndex = -1
            })
        },

        saveRecord(submitData) {
            if (this.editedIndex > -1) {
                updateStateDefinition(submitData).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    Object.assign(this.records[this.editedIndex], this.editedItem);
                    this.showMsg("success", "workflow.states.successful_edit");
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", "workflow.states.error");
                })
            } else {
                createNewStateDefinition(submitData).then((response) => {
                    this.editedItem = Object.assign({}, response.data)
                    this.records.push(this.editedItem);
                    this.showMsg("success", "workflow.states.successful");
                    this.closeEdit();
                }).catch(() => {
                    this.showMsg("error", "workflow.states.error");
                })
            }
        },

        deleteRecord() {
            if (!this.editedItem.editable) {
                this.showMsg("error", "workflow.states.cannot_delete_system_state");
                this.closeDelete();
                return;
            }

            deleteStateDefinition(this.editedItem).then(() => {
                this.records.splice(this.editedIndex, 1);
                this.showMsg("success", "workflow.states.remove");
                this.closeDelete();
            }).catch(() => {
                this.showMsg("error", "workflow.states.removed_error");
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
