<template>
    <v-dialog v-model="dialogVisible" max-width="900px">
        <v-card>
            <v-card-title>
                <span class="text-h5">{{ dialogEditTitle }}</span>
            </v-card-title>

            <v-card-text>
                <v-form ref="form">
                    <v-container>
                        <v-row>
                            <v-col cols="12">
                                <v-text-field v-model="localEditedItem.display_name"
                                              :label="$t('workflow.states.display_name')"
                                              :rules="[v => !!v || $t('error.validation')]"
                                              :disabled="!isEditable"
                                              required />
                            </v-col>

                            <v-col cols="12">
                                <v-textarea v-model="localEditedItem.description"
                                            :label="$t('workflow.states.description')"
                                            :disabled="!isEditable"
                                            rows="3" />
                            </v-col>

                            <v-col cols="4">
                                <v-text-field v-model="localEditedItem.color"
                                              :label="$t('workflow.states.color')"
                                              :disabled="!isEditable"
                                              type="color" />
                            </v-col>

                            <v-col cols="8">
                                <v-text-field v-model="localEditedItem.icon"
                                              :label="$t('workflow.states.icon')"
                                              :disabled="!isEditable"
                                              placeholder="mdi-check-circle" />
                            </v-col>

                            <v-col cols="12" v-if="!isEditable">
                                <v-alert type="warning" dense outlined>
                                    {{ $t('workflow.states.cannot_edit_system_state') }}
                                </v-alert>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-form>
            </v-card-text>

            <v-card-actions>
                <v-spacer />
                <v-btn text color="primary" @click="save">
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
        name: "StateEditDialog",

        props: {
            value: Boolean,
            editedItem: Object,
            editedIndex: Number,
            isEditable: Boolean
        },

        data() {
            return {
                localEditedItem: { ...this.editedItem }
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

            dialogEditTitle() {
                return this.editedIndex === -1
                    ? this.$t("workflow.states.add_new")
                    : this.$t("workflow.states.edit");
            }
        },

        watch: {
            editedItem: {
                handler(val) {
                    this.localEditedItem = { ...val };
                },
                deep: true
            }
        },

        methods: {
            save() {
                if (!this.$refs.form.validate()) return;

                this.$emit('save', { ...this.localEditedItem });
            }
        }
    };
</script>
