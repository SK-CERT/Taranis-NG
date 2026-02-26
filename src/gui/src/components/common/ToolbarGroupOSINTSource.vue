<template>
    <div :class="UI.CLASS.multiselect">
        <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR" :style="multiSelectActive ? UI.STYLE.multiselect_active : ''"
               @click.stop="multiSelect" data-btn="multi_select_button" :title="$t('assess.tooltip.toggle_selection')">
            <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON.MULTISELECT }}</v-icon>
        </v-btn>
        <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>
        <div v-for="btn in actions" :key="btn.action" :class="UI.CLASS.multiselect_buttons">
            <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR"
                   v-if="btn.can" :disabled="btn.disabled" @click.stop="action(btn.action)" :data-btn="btn.like" :title="btn.title">
                <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON[btn.ui_icon] }}</v-icon>
            </v-btn>
        </div>
    </div>
</template>

<script>
import AuthMixin from "../../services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";

export default {
    name: "ToolbarGroupOSINTSource",
    data: () => ({
        all_selected: false
    }),
    mixins: [AuthMixin],
    computed: {
        canModify() {
            return this.checkPermission(Permissions.ASSESS_UPDATE)
        },

        canDelete() {
            return this.checkPermission(Permissions.ASSESS_DELETE)
        },

        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },

        actions() {
            const selectAction = this.all_selected
                ? { can: true, disabled: !this.multiSelectActive, action: 'UNSELECT_ALL', data_btn: 'unselect_all', title: this.$t('osint_source.tooltip.unselect_all'), ui_icon: 'UNSELECT_ALL' }
                : { can: true, disabled: !this.multiSelectActive, action: 'SELECT_ALL', data_btn: 'select_all', title: this.$t('osint_source.tooltip.select_all'), ui_icon: 'SELECT_ALL' };

            return [
                selectAction,
            ]
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelectOSINTSource;
        },
    },
    methods: {

        multiSelect() {
            this.$store.dispatch('multiSelectOSINTSource', !this.multiSelectActive);
            if (this.multiSelectActive === false) {
                this.all_selected = false;
                this.$root.$emit('uncheck-osint-source-card');
            }
        },

        action(type) {
            if(type === 'SELECT_ALL') {
                this.$root.$emit('uncheck-osint-source-card');
                setTimeout(() => {
                    this.$root.$emit('check-osint-source-card');
                    this.all_selected = true;
                }, 50);
            } else if(type === 'UNSELECT_ALL') {
                this.$root.$emit('uncheck-osint-source-card');
                this.all_selected = false;
            }
        },

        disableMultiSelect() {
            if (this.multiSelectActive) {
                this.multiSelect()
            }
        }

    }
}
</script>
