<template>
    <v-tooltip bottom :disabled="!tooltip">
        <template v-slot:activator="{ on }">
            <span v-on="locked ? on : {}" style="display: inline-block;">
                <v-btn
                    v-on="!locked ? on : {}"
                    :icon="icon"
                    :text="text"
                    :outlined="outlined"
                    :small="small"
                    :large="large"
                    :disabled="effectiveDisabled"
                    :loading="loading"
                    :class="buttonClass"
                    :color="effectiveColor"
                    @click="handleClick"
                    :data-btn="dataBtn"
                >
                    <v-icon :left="!icon && showIcon" :color="effectiveIconColor" :class="lockIconClasses" :style="lockIconStyle">{{ editIcon }}</v-icon>
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
    name: "EditButton",
    mixins: [ButtonMixin],
    props: {
        iconColor: {
            type: String,
            default: "brown",
            description: "Icon color"
        },
        dataBtn: {
            type: String,
            default: "edit",
            description: "Data attribute for testing/identification"
        }
    },
    computed: {
        editIcon() {
            if (this.locked) {
                return this.getLockIcon();
            }
            return this.getIconFromUI('EDIT', 'mdi-pencil', 'mdi-pencil-outline');
        },
        buttonLabel() {
            if (this.label) {
                return this.label;
            }
            return this.$t('common.edit');
        },
        tooltipText() {
            if (typeof this.tooltip === 'string') {
                return this.tooltip;
            }
            if (this.tooltip === true) {
                return this.$t('common.edit');
            }
            return "";
        },
        buttonClass() {
            const baseClass = this.color === 'orange' && !this.customClass.includes('orange') ? 'orange' : '';
            return baseClass ? `${baseClass} ${this.customClass}`.trim() : this.customClass;
        }
    },
    methods: {
        handleClick(event) {
            event.stopPropagation();
            this.$emit('edit', event);
            this.$emit('click', event);
        }
    }
}
</script>

<style scoped>
/* Add any custom styles here if needed */
</style>
