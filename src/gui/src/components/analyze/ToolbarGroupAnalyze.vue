<template>
    <div :class="UI.CLASS.multiselect">
        <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR" :style="multi_select ? UI.STYLE.multiselect_active : ''"
               @click.stop="multiSelect" data-btn="multi_select" :title="$t('assess.tooltip.toggle_selection')">
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
import {deleteReportItem} from "@/api/analyze";
import Permissions from "@/services/auth/permissions";

export default {
    name: "ToolbarGroupAnalyze",
    data: () => ({
        multi_select: false,
        all_selected: false
    }),
    mixins: [AuthMixin],
    computed: {
        canDelete() {
            return this.checkPermission(Permissions.ANALYZE_DELETE)
        },

        canCreateProduct() {
            return this.checkPermission(Permissions.PUBLISH_CREATE)
        },
        actions() {
            const selectAction = this.all_selected
                ? { can: true, disabled: !this.multi_select, action: 'UNSELECT_ALL', data_btn: 'unselect_all', title: this.$t('analyze.tooltip.unselect_all'), ui_icon: 'UNSELECT_ALL' }
                : { can: true, disabled: !this.multi_select, action: 'SELECT_ALL', data_btn: 'select_all', title: this.$t('analyze.tooltip.select_all'), ui_icon: 'SELECT_ALL' };

            return [
                selectAction,
                { can: this.canCreateProduct, disabled: !this.multi_select, action: 'ANALYZE', data_btn: 'analyze', title: this.$t('analyze.tooltip.publish_items'), ui_icon: 'ANALYZE' },
                { can: this.canDelete, disabled: !this.multi_select, action: 'DELETE', data_btn: 'delete', title: this.$t('analyze.tooltip.delete_items'), ui_icon: 'DELETE' }
            ]
        }
    },
    methods: {
        multiSelect() {
            this.multi_select = !this.multi_select
            this.$store.dispatch("multiSelectReport", this.multi_select)
            if (this.multi_select === false) {
                this.all_selected = false;
                this.$store.dispatch('deselectAllReport');
                this.$root.$emit('multi-select-off');
            }
        },

        analyze() {
            let selection = this.$store.getters.getSelectionReport
            let items = []
            for (let i = 0; i < selection.length; i++) {
                items.push(selection[i].item)
            }
            if (items.length > 0) {
                this.multi_select = false
                this.$store.dispatch("multiSelectReport", this.multi_select)
                this.$root.$emit('multi-select-off');
                this.$root.$emit('new-product', items);
            }
        },

        action(type) {
            if (type === 'ANALYZE') {
                this.analyze();
            } else if (type === 'SELECT_ALL') {
                this.selectAll();
            } else if (type === 'UNSELECT_ALL') {
                this.unselectAll();
            } else {
                let selection = this.$store.getters.getSelectionReport
                let items = []
                for (let i = 0; i < selection.length; i++) {
                    items.push({
                        'id': selection[i].id
                    })
                }
                if (type === 'DELETE') {
                    for (let i = 0; i < items.length; i++) {
                        deleteReportItem(items[i]).then(() => {
                            this.multiSelect()
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                    }
                }
            }
        },

        selectAll() {
            // Use default filter structure matching ContentDataAnalyze
            const filter = {
                search: '',
                completed: false,
                incompleted: false,
                range: 'ALL',
                sort: 'DATE_DESC'
            };
            const group = this.$store.getters.getCurrentReportItemGroup;

            this.$store.dispatch('selectAllReportItems', {
                group: group,
                filter: filter
            }).then((count) => {
                this.all_selected = true;
                this.$root.$emit('sync-analyze-selection');
                this.$root.$emit('notification', {
                    type: 'success',
                    loc: 'analyze.select_all_success',
                    params: { count: count }
                });
            }).catch(() => {
                this.$root.$emit('notification', {
                    type: 'error',
                    loc: 'error.select_all_failed'
                });
            });
        },

        unselectAll() {
            this.all_selected = false;
            this.$store.dispatch('deselectAllReport');
            this.$root.$emit('sync-analyze-selection');
        },

        disableMultiSelect() {
            if (this.multi_select === true) {
                this.multiSelect()
            }
        }
    },
    mounted() {
        this.$root.$on('key-multi-select', () => {
            this.multiSelect();
        });
    },
    beforeDestroy() {
        this.$root.$off('key-multi-select')
    }
}
</script>
