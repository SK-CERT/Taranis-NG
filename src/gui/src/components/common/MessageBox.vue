<template>
    <v-overlay :dark="false" style="z-index: 10000">
        <v-card class="mx-auto" outlined>
            <!-- This will be generic messageBox in future. Currently support only YES-CANCEL buttons,
                 later we add support for buttons & icons configuration  -->
            <v-card-title class="justify-center">
                <v-icon style="padding-right: 10px" color="blue">mdi-message-question</v-icon>
                {{ title }}
            </v-card-title>
            <v-card-text class="font-weight-black text-center">
                {{ message }}
            </v-card-text>
            <v-card-actions class="justify-center">
                <v-btn @click.prevent="selectButton('Yes')" class="red accent-1" color="red darken-4" text>{{ $t('common.messagebox.yes') }}</v-btn>
                <v-btn @click.prevent="selectButton('Cancel')" class="mx-4 justify-center">{{ $t('common.cancel') }}</v-btn>
            </v-card-actions>
        </v-card>
    </v-overlay>
</template>

<script>

    export default {
        props: {
            title: String,
            message: String,
        },
        methods: {
            selectButton(buttonType) {
                this.$emit('button' + buttonType);
            },
        }
    }
</script>

<style>
</style>
