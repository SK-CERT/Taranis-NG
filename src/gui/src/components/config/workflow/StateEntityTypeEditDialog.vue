<template>
    <v-dialog v-model="dialogVisible" max-width="800px">
        <v-card>
            <v-card-title>
                <span class="headline">{{ isNew ? $t('workflow.state_workflow.add_state_association') : $t('workflow.state_workflow.edit_state_association') }}</span>
            </v-card-title>

            <v-card-text>
                <v-container>
                    <v-row>
                        <v-col cols="12" sm="6">
                            <v-select v-model="localItem.entity_type"
                                      :items="entityTypes"
                                      :label="$t('workflow.state_workflow.entity_type')"
                                      :disabled="!isEditable"
                                      :rules="[v => !!v || $t('workflow.state_workflow.entity_type_required')]"
                                      required>
                                <template v-slot:item="{ item }">
                                    {{ $t('workflow.entity_types.' + item) }}
                                </template>
                                <template v-slot:selection="{ item }">
                                    {{ $t('workflow.entity_types.' + item) }}
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12" sm="6">
                            <v-select v-model="localItem.state_id"
                                      :items="availableStates"
                                      item-text="display_name"
                                      item-value="id"
                                      :label="$t('workflow.state_workflow.state')"
                                      :disabled="!isEditable"
                                      :rules="[v => !!v || $t('workflow.state_workflow.state_required')]"
                                      required>
                                <template v-slot:item="{ item }">
                                    <v-icon left :color="item.color">{{ item.icon }}</v-icon>
                                    {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name }}
                                </template>
                                <template v-slot:selection="{ item }">
                                    <v-icon left :color="item.color" small>{{ item.icon }}</v-icon>
                                    {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name }}
                                </template>
                            </v-select>
                        </v-col>
                    </v-row>

                    <v-row>
                        <v-col cols="12" sm="6">
                            <v-select v-model="localItem.state_type"
                                      :items="stateTypes"
                                      :label="$t('workflow.state_workflow.state_type')"
                                      :disabled="!isEditable">
                                <template v-slot:item="{ item }">
                                    {{ $t('workflow.state_types.' + item) }}
                                </template>
                                <template v-slot:selection="{ item }">
                                    {{ $t('workflow.state_types.' + item) }}
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12" sm="6">
                            <v-text-field v-model.number="localItem.sort_order"
                                          :label="$t('workflow.state_workflow.sort_order')"
                                          type="number"
                                          :disabled="!isEditable"></v-text-field>
                        </v-col>
                    </v-row>

                    <v-row>
                        <v-col cols="12">
                            <v-switch v-model="localItem.is_active"
                                      :label="$t('workflow.state_workflow.is_active')"
                                      :disabled="!isEditable"></v-switch>
                        </v-col>
                    </v-row>

                    <v-row v-if="!isEditable">
                        <v-col cols="12">
                            <v-alert type="warning" outlined dense>
                                {{ $t('workflow.state_workflow.cannot_edit_system_association') }}
                            </v-alert>
                        </v-col>
                    </v-row>
                </v-container>
            </v-card-text>

            <v-card-actions>
                <v-spacer />
                <v-btn text color="primary" @click="save" :disabled="!canSave">
                    {{ $t('common.save') }}
                </v-btn>
                <v-btn text color="primary" @click="dialogVisible = false">
                    {{ $t('common.cancel') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
    export default {
        name: "StateEntityTypeEditDialog",
        props: {
            value: Boolean,
            editedItem: Object,
            editedIndex: Number,
            isEditable: Boolean,
            availableStates: Array
        },
        data() {
            return {
                localItem: {
                    entity_type: "",
                    state_id: null,
                    state_type: "normal",
                    is_active: true,
                    sort_order: 0
                },
                entityTypes: ["report_item", "product"],
                stateTypes: ["normal", "initial", "final"]
            };
        },
        computed: {
            dialogVisible: {
                get() {
                    return this.value;
                },
                set(v) {
                    this.$emit('input', v);
                }
            },
            isNew() {
                return this.editedIndex === -1;
            },
            canSave() {
                return this.localItem.entity_type && this.localItem.state_id;
            }
        },
        watch: {
            editedItem: {
                handler(newVal) {
                    if (newVal) {
                        this.localItem = Object.assign({}, newVal);
                    }
                },
                deep: true
            }
        },
        methods: {
            save() {
                const submitData = {
                    entity_type: this.localItem.entity_type,
                    state_id: this.localItem.state_id,
                    state_type: this.localItem.state_type,
                    is_active: this.localItem.is_active,
                    sort_order: this.localItem.sort_order
                };

                if (!this.isNew) {
                    submitData.id = this.localItem.id;
                }

                this.$emit('save', submitData);
            }
        },
    }
</script>
