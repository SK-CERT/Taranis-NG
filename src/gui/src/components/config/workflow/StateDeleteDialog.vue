<template>
    <v-dialog v-model="dialog" max-width="500px" @input="updateDialog">
        <v-card>
            <v-card-title class="text-h5"> {{ $t('common.messagebox.delete') }} </v-card-title>
            <v-card-text>
                <v-alert v-if="!editedItem.editable" type="error" dense>
                    {{ $t('workflow.states.cannot_delete_system_state') }}
                </v-alert>
            </v-card-text>
            <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn color="blue darken-1" text @click="close"> {{ $t('common.cancel') }} </v-btn>
                <v-btn color="blue darken-1" text @click="deleteRecord" :disabled="!editedItem.editable">
                    {{ $t('common.delete') }}
                </v-btn>
                <v-spacer></v-spacer>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
export default {
    name: "StateDeleteDialog",
    props: {
        value: {
            type: Boolean,
            default: false
        },
        editedItem: {
            type: Object,
            required: true
        }
    },
    data() {
        return {
            dialog: this.value
        };
    },
    watch: {
        value(newVal) {
            this.dialog = newVal;
        }
    },
    methods: {
        updateDialog(value) {
            this.$emit('input', value);
        },

        close() {
            this.$emit('close');
        },

        deleteRecord() {
            this.$emit('delete');
        }
    }
}
</script>
