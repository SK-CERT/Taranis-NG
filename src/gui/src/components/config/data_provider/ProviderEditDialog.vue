<template>
    <v-dialog v-model="visible" max-width="900px">
        <v-card>
            <v-card-title>
                <span class="text-h5">{{ dialogTitle }}</span>
            </v-card-title>
            <v-card-text>
                <v-form ref="form">
                    <v-container>
                        <slot :localItem="localItem" :showApiKey="showApiKey" :toggleApiKey="toggleApiKey"></slot>
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
    name: "ProviderEditDialog",
    props: {
        value: Boolean,
        editedItem: Object,
        editedIndex: Number,
        providerType: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            showApiKey: false,
            localItem: {}
        };
    },
    computed: {
        visible: {
            get() {
                return this.value;
            },
            set(value) {
                this.$emit('input', value);
            }
        },
        dialogTitle() {
            return this.editedIndex === -1
                ? this.$t(`${this.providerType}.add_new`)
                : this.$t(`${this.providerType}.edit`)
        }
    },
    watch: {
        editedItem: {
            handler(newVal) {
                this.localItem = Object.assign({}, newVal);
            },
            deep: true,
            immediate: true
        }
    },
    methods: {
        toggleApiKey() {
            this.showApiKey = !this.showApiKey;
        },
        close() {
            this.showApiKey = false;
            this.$emit('close');
        },
        save() {
            if (!this.$refs.form.validate()) return;
            this.$emit('save', this.localItem);
            this.showApiKey = false;
        }
    }
}
</script>
