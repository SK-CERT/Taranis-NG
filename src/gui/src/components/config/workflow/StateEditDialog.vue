<template>
    <v-dialog v-model="dialog" max-width="900px" @input="updateDialog">
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
                                    :rules="[v => !!v || $t('error.validation')]" :disabled="!isEditable"
                                    required></v-text-field>
                            </v-col>
                            <v-col cols="12">
                                <v-textarea v-model="localEditedItem.description"
                                    :label="$t('workflow.states.description')" :disabled="!isEditable"
                                    rows="3"></v-textarea>
                            </v-col>
                            <v-col cols="4">
                                <v-text-field v-model="localEditedItem.color" :label="$t('workflow.states.color')"
                                    :disabled="!isEditable" type="color"></v-text-field>
                            </v-col>
                            <v-col cols="8">
                                <v-text-field v-model="localEditedItem.icon" :label="$t('workflow.states.icon')"
                                    :disabled="!isEditable" placeholder="mdi-check-circle"></v-text-field>
                            </v-col>
                            <v-col cols="12" v-if="!isEditable">
                                <v-alert type="warning" dense outlined>
                                    {{ $t('workflow.states.system_state_warning') }}
                                </v-alert>
                            </v-col>
                        </v-row>
                    </v-container>
                </v-form>
            </v-card-text>

            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="blue darken-1" text @click="close"> {{ $t('common.cancel') }} </v-btn>
                <v-btn color="blue darken-1" text @click="save"> {{ $t('common.save') }} </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
export default {
    name: "StateEditDialog",
    props: {
        value: {
            type: Boolean,
            default: false
        },
        editedItem: {
            type: Object,
            required: true
        },
        editedIndex: {
            type: Number,
            required: true
        },
        isEditable: {
            type: Boolean,
            required: true
        }
    },
    data() {
        return {
            dialog: this.value,
            localEditedItem: { ...this.editedItem }
        };
    },
    computed: {
        dialogEditTitle() {
            return this.editedIndex === -1 ? this.$t("workflow.states.add_new") : this.$t("workflow.states.edit")
        }
    },
    watch: {
        value(newVal) {
            this.dialog = newVal;
        },
        editedItem: {
            handler(newVal) {
                this.localEditedItem = { ...newVal };
            },
            deep: true
        }
    },
    methods: {
        updateDialog(value) {
            this.$emit('input', value);
        },

        close() {
            this.$emit('close');
        },

        save() {
            if (!this.$refs.form.validate()) return;

            // Prepare data for submission
            let submitData = { ...this.localEditedItem };

            this.$emit('save', submitData);
        }
    }
}
</script>
