<template>
    <v-dialog v-model="dialogVisible"
              max-width="550"
              :persistent="!cancelable">
        <v-card outlined>
            <v-card-title class="justify-center" style="text-align: center;">
                <div style="display: inline-flex; align-items: center; max-width: 100%;">
                    <v-icon class="mr-2" size="28" :color="alert ? 'error' : 'primary'">
                        {{ alert ? 'mdi-alert-circle' : 'mdi-help-circle' }}
                    </v-icon>

                    <span class="text-h6" style="word-break: break-word;">
                        {{ title }}
                    </span>
                </div>
            </v-card-title>

            <v-card-text class="font-weight-black text-center">
                {{ message }}
            </v-card-text>

            <v-card-actions class="justify-center">
                <v-btn
                       @click="emitResult('yes')">
                    {{ $t('common.messagebox.yes') }}
                </v-btn>
                <v-btn class="ml-4"
                       @click="emitResult('cancel')">
                    {{ $t('common.cancel') }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script>
    export default {
        name: "MessageBox",

        props: {
            value: { type: Boolean, default: false },
            title: String,
            message: String,
            alert: Boolean,
            cancelable: { type: Boolean, default: true }
        },

        computed: {
            dialogVisible: {
                get() { return this.value },
                set(v) { this.$emit('input', v) }
            }
        },

        methods: {
            emitResult(type) {
                this.$emit(type)
                this.dialogVisible = false
            }
        }
    }
</script>
