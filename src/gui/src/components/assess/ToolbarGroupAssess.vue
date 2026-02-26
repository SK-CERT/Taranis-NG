<template>
    <div :class="UI.CLASS.multiselect">
        <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR" :style="multiSelectActive ? UI.STYLE.multiselect_active : '' "
               @click.stop="multiSelect" data-btn="multi_select_button" :title="$t('assess.tooltip.toggle_selection')">
            <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON.MULTISELECT }}</v-icon>
        </v-btn>
        <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>
        <div v-for="btn in actions" :key="btn.action" :class="UI.CLASS.multiselect_buttons">
            <v-btn v-bind="UI.TOOLBAR.BUTTON.SELECTOR"
                   v-if="btn.can" :disabled="btn.disabled" @click.stop="action(btn.action)" :data-btn="btn.data_btn" :title="btn.title">
                <v-icon v-bind="UI.TOOLBAR.ICON.SELECTOR">{{ UI.ICON[btn.ui_icon] }}</v-icon>
            </v-btn>
        </div>
    </div>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";
    import { groupAction } from "@/api/assess";
    import Permissions from "@/services/auth/permissions";

    export default {
        name: "ToolbarGroupAssess",
        components: {
        },
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
                    ? { can: true, disabled: !this.multiSelectActive, action: 'UNSELECT_ALL', data_btn: 'unselect_all', title: this.$t('assess.tooltip.unselect_all'), ui_icon: 'UNSELECT_ALL' }
                    : { can: true, disabled: !this.multiSelectActive, action: 'SELECT_ALL', data_btn: 'select_all', title: this.$t('assess.tooltip.select_all'), ui_icon: 'SELECT_ALL' };

                return [
                    selectAction,
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'GROUP', data_btn: 'group', title: this.$t('assess.tooltip.group_items'), ui_icon: 'GROUP' },
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'UNGROUP', data_btn: 'ungroup', title: this.$t('assess.tooltip.ungroup_items'), ui_icon: 'UNGROUP' },
                    { can: this.canCreateReport, disabled: !this.multiSelectActive, action: 'ANALYZE', data_btn: 'analyze', title: this.$t('assess.tooltip.analyze_items'), ui_icon: 'ANALYZE' },
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'READ', data_btn: 'read', title: this.$t('assess.tooltip.read_items'), ui_icon: 'READ' },
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'IMPORTANT', data_btn: 'important', title: this.$t('assess.tooltip.important_items'), ui_icon: 'IMPORTANT' },
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'LIKE', data_btn: 'like', title: this.$t('assess.tooltip.like_items'), ui_icon: 'LIKE' },
                    { can: this.canModify, disabled: !this.multiSelectActive, action: 'DISLIKE', data_btn: 'dislike', title: this.$t('assess.tooltip.dislike_items'), ui_icon: 'UNLIKE' },
                    { can: this.canDelete, disabled: !this.multiSelectActive, action: 'DELETE', data_btn: 'delete', title: this.$t('assess.tooltip.delete_items'), ui_icon: 'DELETE' }
                ]
            },

            multiSelectActive() {
                return this.$store.getters.getMultiSelectNews;
            },
        },
        methods: {
            getGroupId() {
                if (window.location.pathname.includes("/group/")) {
                    let i = window.location.pathname.indexOf("/group/");
                    let len = window.location.pathname.length;
                    return window.location.pathname.substring(i + 7, len);
                } else {
                    return null;
                }
            },

            multiSelect() {
                this.$store.dispatch("multiSelectNews", !this.multiSelectActive)
                if (this.multiSelectActive === false) {
                    this.all_selected = false;
                    this.$store.dispatch('deselectAll');
                    this.$root.$emit('multi-select-off');
                }
            },

            analyze() {
                let selection = this.$store.getters.getSelection
                let items = []
                for (let i = 0; i < selection.length; i++) {
                    if (selection[i].type === 'AGGREGATE') {
                        items.push(selection[i].item)
                    }
                }
                if (items.length > 0) {
                    this.$store.dispatch("multiSelectNews", false)
                    this.$root.$emit('multi-select-off');
                    this.$root.$emit('new-report', items);
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
                    let selection = this.$store.getters.getSelection
                    let items = []
                    for (let i = 0; i < selection.length; i++) {
                        items.push({
                            'type': selection[i].type,
                            'id': selection[i].id
                        })
                    }
                    if (items.length > 0) {
                        groupAction({ 'group': this.getGroupId(), 'action': type, 'items': items }).then(() => {
                            this.multiSelect()
                            this.$root.$emit('news-items-updated');
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
            },

            selectAll() {
                let filter = this.$store.getters.getFilter;
                const group_id = this.getGroupId();

                // If filter is empty or doesn't have required properties, use default
                if (!filter || !filter.hasOwnProperty('search')) {
                    filter = {
                        search: "",
                        range: "ALL",
                        read: false,
                        important: "ALL",
                        relevant: "ALL",
                        sort: "DATE_DESC"
                    };
                }

                this.$store.dispatch('selectAllItems', {
                    group_id: group_id,
                    data: { filter: filter }
                }).then((count) => {
                    this.all_selected = true;
                    this.$root.$emit('sync-assess-selection');
                    this.$root.$emit('notification', {
                        type: 'success',
                        loc: 'assess.select_all_success',
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
                this.$store.dispatch('deselectAll');
                this.$root.$emit('sync-assess-selection');
            },

            disableMultiSelect() {
                if (this.multiSelectActive) {
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
