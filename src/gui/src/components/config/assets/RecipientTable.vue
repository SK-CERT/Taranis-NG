<template>
    <v-data-table :headers="headers" :items="recipients" sort-by="value" class="elevation-1">
        <template v-slot:top>
            <v-toolbar flat>
                <v-toolbar-title>{{ $t('notification_template.recipients') }}</v-toolbar-title>
                <v-divider class="mx-4" inset vertical></v-divider>
                <v-spacer></v-spacer>
                <v-dialog v-model="dialog" max-width="500px">
                    <template v-slot:activator="{ on }">
                        <v-btn color="primary" dark class="mb-2" v-on="on">
                            <v-icon left>mdi-plus</v-icon>
                            <span>{{ $t('notification_template.new_recipient') }}</span>
                        </v-btn>
                    </template>
                    <v-card>
                        <v-card-title>
                            <span class="headline">{{ formTitle }}</span>
                        </v-card-title>

                        <v-card-text>

                            <v-text-field v-model="edited_recipient.email" :label="$t('notification_template.email')"
                                :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                            <v-text-field v-model="edited_recipient.name"
                                :label="$t('notification_template.recipient_name')"
                                :spellcheck="$store.state.settings.spellcheck"></v-text-field>

                        </v-card-text>

                        <v-card-actions>
                            <v-spacer></v-spacer>
                            <v-btn color="primary" dark @click="save">{{ $t('common.save') }}</v-btn>
                            <v-btn color="primary" text @click="close">{{ $t('common.cancel') }}</v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </v-toolbar>
        </template>
        <template v-slot:item.action="{ item }">
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
                <span>{{ $t('common.delete') }}</span>
            </v-tooltip>
        </template>
    </v-data-table>
</template>

<script>
export default {
    name: "RecipientTable",
    props: {
        recipients: Array,
    },
    data: () => ({
        dialog: false,
        selected_recipient: null,
        edited_index: -1,
        edited_recipient: {
            email: "",
            name: "",
        },
        default_recipient: {
            email: "",
            name: "",
        },
    }),
    computed: {
        headers() {
            return [
                { text: this.$t('notification_template.email'), value: 'email', align: 'left', sortable: true },
                { text: this.$t('notification_template.recipient_name'), value: 'name', sortable: true },
                { text: this.$t('settings.actions'), value: 'action', align: 'right', sortable: false },
            ];
        },
        formTitle() {
            return this.edited_index === -1 ? this.$t('notification_template.add_recipient') : this.$t('notification_template.edit_recipient')
        }
    },
    watch: {
        dialog(val) {
            val || this.close()
        },
    },
    methods: {
        close() {
            this.dialog = false;
            setTimeout(() => {
                this.edited_recipient = Object.assign({}, this.default_recipient);
                this.edited_index = -1
            }, 300)
        },

        save() {
            if (this.edited_index > -1) {
                Object.assign(this.recipients[this.edited_index], this.edited_recipient)
            } else {
                this.recipients.push(this.edited_recipient)
            }
            this.selected_recipient = null;
            this.close()
        },

        editItem(item) {
            this.edited_index = this.recipients.indexOf(item);
            this.edited_recipient = Object.assign({}, item);
            this.dialog = true;
        },

        moveItemUp(item) {
            const index = this.recipients.indexOf(item);
            if (index > 0) {
                this.recipients.splice(index - 1, 0, this.recipients.splice(index, 1)[0]);
            }
        },

        moveItemDown(item) {
            const index = this.recipients.indexOf(item);
            if (index < this.recipients.length - 1) {
                this.recipients.splice(index + 1, 0, this.recipients.splice(index, 1)[0]);
            }
        },

        deleteItem(item) {
            const index = this.recipients.indexOf(item);
            this.recipients.splice(index, 1)
        },
    }
}
</script>
