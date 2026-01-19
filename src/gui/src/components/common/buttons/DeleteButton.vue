<template>
    <v-tooltip bottom :disabled="!tooltip">
        <template v-slot:activator="{ on }">
            <span v-on="locked ? on : {}" style="display: inline-block;">
                <v-btn v-on="!locked ? on : {}" :icon="icon" :text="text" :outlined="outlined" :small="small"
                    :large="large" :disabled="effectiveDisabled" :loading="loading" :class="buttonClass"
                    :color="effectiveColor" @click="handleClick" :data-btn="dataBtn">
                    <v-icon :left="!icon && showIcon" :color="effectiveIconColor" :class="lockIconClasses"
                        :style="lockIconStyle">{{ deleteIcon }}</v-icon>
                    <span v-if="!icon && showLabel">{{ buttonLabel }}</span>
                </v-btn>
            </span>
        </template>
        <span>{{ tooltipText }}</span>
    </v-tooltip>
</template>

<script>
import ButtonMixin from './ButtonMixin.js';

export default {
    name: "DeleteButton",
    mixins: [ButtonMixin],
    props: {
        iconColor: {
            type: String,
            default: "red",
            description: "Icon color (defaults to red)"
        },
        dataBtn: {
            type: String,
            default: "delete",
            description: "Data attribute for testing/identification"
        },
        confirmDelete: {
            type: Boolean,
            default: false,
            description: "If true, emits 'confirm' event instead of 'delete'"
        }
    },
    computed: {
        deleteIcon() {
            if (this.locked) {
                return this.getLockIcon();
            }
            return this.getIconFromUI('DELETE', 'mdi-delete', 'mdi-delete-outline');
        },
        buttonLabel() {
            if (this.label) {
                return this.label;
            }
            return this.$t('common.delete');
        },
        tooltipText() {
            if (typeof this.tooltip === 'string') {
                return this.tooltip;
            }
            if (this.tooltip === true) {
                return this.$t('common.delete');
            }
            return "";
        }
    },
    methods: {
        handleClick(event) {
            event.stopPropagation();
            if (this.confirmDelete) {
                this.$emit('confirm', event);
            } else {
                this.$emit('delete', event);
            }
            this.$emit('click', event);
        }
    }
}
</script>

<style scoped>
/* Add any custom styles here if needed */
</style>
