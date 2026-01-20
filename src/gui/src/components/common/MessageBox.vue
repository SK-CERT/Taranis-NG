<template>
    <v-dialog v-model="dialogVisible" max-width="550" :persistent="!cancelable">
        <v-card outlined>
            <v-card-title class="justify-center" style="text-align: center;">
                <div style="display: inline-flex; align-items: center; max-width: 100%;">
                    <v-icon class="mr-2" size="28" :color="icon.color">
                        {{ icon.name }}
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
                <v-btn v-for="(button, index) in buttons" :key="index" :class="index > 0 ? 'ml-4' : ''"
                       :color="button.color" :text=true @click="emitResult(button.action)">
                    {{ $t(button.label)}}
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
            cancelable: { type: Boolean, default: true },
            title: String,
            message: String,
            icon: {
                type: Object,
                default: () => ({
                    name: 'mdi-alert-circle', // Icon name (e.g., 'mdi-alert-circle', 'mdi-help-circle')
                    color: 'error'            // Icon color (e.g., 'error', 'primary', 'warning')
                })
            },
            buttons: {
                type: Array,
                default() {                   // Array of { label: string, color: string, action: string}
                    return [
                        { label: 'common.messagebox.yes', color: 'error', action: 'yes' },
                        { label: 'common.cancel', color: '', action: 'cancel' },
                    ]
                }
            },
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
