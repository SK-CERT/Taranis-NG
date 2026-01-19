<template>
    <v-row v-bind="UI.DIALOG.ROW.WINDOW">
        <v-btn v-bind="UI.BUTTON.ADD_NEW" v-if="add_button && canCreate" @click="addEmptyReportItem">
            <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
            <span>{{ $t('common.add_btn') }}</span>
        </v-btn>

        <v-dialog v-bind="UI.DIALOG.FULLSCREEN" v-model="visible" @keydown.esc="cancel" report-item>
            <v-overlay :value="overlay" z-index="50000">
                <v-progress-circular indeterminate size="64"></v-progress-circular>
            </v-overlay>

            <!-- Confirmation dialog for unsaved changes -->
            <MessageBox v-model="showCloseConfirmation" :title="$t('confirm_close.title')"
                        :message="$t('report_item.confirm_close.message')" :buttons="confirmCloseButtons"
                        :icon="{ name: 'mdi-help-circle', color: 'warning' }"
                        @continue="showCloseConfirmation = false" @save="saveAndClose" @close="confirmClose" />

            <v-card v-bind="UI.DIALOG.BASEMENT">
                <v-toolbar v-bind="UI.DIALOG.TOOLBAR" data-dialog="report-item">
                    <v-btn icon dark @click="cancel" data-btn="cancel">
                        <v-icon>mdi-close-circle</v-icon>
                    </v-btn>

                    <v-toolbar-title>
                        <span v-if="!edit">{{ $t('report_item.add_new') }}</span>
                        <span v-else-if="read_only">{{ $t('report_item.read') }}</span>
                        <span v-else>{{ $t('report_item.edit') }}</span>
                    </v-toolbar-title>

                    <v-spacer></v-spacer>

                    <v-switch style="padding-top:25px" v-model="verticalView" label="Side-by-side view"></v-switch>

                    <v-spacer></v-spacer>

                    <v-select :key="`state-select-${report_item.state_id}`" :disabled="!canModify"
                              style="padding-top:25px; min-width: 100px; max-width: 200px;" v-model="report_item.state_id"
                              :items="available_states"
                              :item-text="item => $te('workflow.states.' + item.display_name) ? $t('workflow.states.' + item.display_name) : item.display_name"
                              item-value="id" :label="$t('report_item.state')" append-icon="mdi-chevron-down"
                              :menu-props="{ maxWidth: '300px' }" @change="saveReportItem('state_id')">

                        <template v-slot:item="{ item }">
                            <v-list-item-avatar>
                                <v-icon :color="item.color">{{ item.icon }}</v-icon>
                            </v-list-item-avatar>
                            <v-list-item-content>
                                <v-list-item-title>
                                    {{ $te('workflow.states.' + item.display_name) ? $t('workflow.states.' +
                                        item.display_name) : item.display_name }}
                                </v-list-item-title>
                            </v-list-item-content>
                        </template>
                    </v-select>
                    <v-btn v-if="!edit" text dark type="submit" form="form">
                        <v-icon left>mdi-content-save</v-icon>
                        <span>{{ $t('common.save') }}</span>
                    </v-btn>

                </v-toolbar>

                <v-row>
                    <v-col :cols="verticalView ? 6 : 12"
                           :style="verticalView ? 'height:calc(100vh - 3em); overflow-y: auto;' : ''">
                        <v-form @submit.prevent="addReportItem" id="form" ref="form" class="px-4">
                            <v-row no-gutters>
                                <v-col cols="12" v-if="edit">
                                    <span class="caption grey--text">ID: {{ report_item.uuid }}</span>
                                </v-col>
                                <v-col cols="4" class="pr-3">
                                    <v-combobox v-on:change="reportSelected" :disabled="edit" v-model="selected_type"
                                                :items="report_types" item-text="title" :label="$t('report_item.report_type')"
                                                name="report_type" v-validate="'required'" />
                                </v-col>
                                <v-col cols="4" class="pr-3">
                                    <v-text-field @focus="onFocus('title_prefix')"
                                                  @blur="saveReportItem('title_prefix')" @keyup="onKeyUp('title_prefix')"
                                                  :class="getLockedStyle('title_prefix')"
                                                  :disabled="field_locks.title_prefix || !canModify"
                                                  :label="$t('report_item.title_prefix')" name="title_prefix"
                                                  v-model="report_item.title_prefix"
                                                  :spellcheck="$store.state.settings.spellcheck"></v-text-field>
                                </v-col>
                                <v-col cols="4" class="pr-3">
                                    <v-text-field @focus="onFocus('title')" @blur="saveReportItem('title')"
                                                  @keyup="onKeyUp('title')" :class="getLockedStyle('title')"
                                                  :disabled="field_locks.title || !canModify" :label="$t('report_item.title')"
                                                  name="title" type="text" v-model="report_item.title" v-validate="'required'"
                                                  data-vv-name="title" :error-messages="errors.collect('title')"
                                                  :spellcheck="$store.state.settings.spellcheck"></v-text-field>
                                </v-col>
                            </v-row>
                            <v-row no-gutters class="pb-4">
                                <v-col cols="12">
                                    <v-btn v-bind="UI.BUTTON.ADD_NEW_IN" v-if="canModify"
                                           @click="$refs.new_item_selector.openSelector()">
                                        <v-icon left>{{ UI.ICON.PLUS }}</v-icon>
                                        <span>{{ $t('assess.add_news_item') }}</span>
                                    </v-btn>
                                </v-col>
                            </v-row>
                            <v-row no-gutters>
                                <v-col cols="12">
                                    <NewsItemSelector v-if="!verticalView" ref="new_item_selector" :attach="false"
                                                      :values="news_item_aggregates" :modify="modify"
                                                      :report_item_id="this.report_item.id" :edit="edit" :verticalView="false" />
                                </v-col>
                            </v-row>
                            <v-row no-gutters>
                                <v-col cols="12">
                                    <RemoteReportItemSelector :values="remote_report_items" :modify="modify"
                                                              :edit="edit" :report_item_id="this.report_item.id"
                                                              @remote-report-items-changed="updateRemoteAttributes" />
                                </v-col>
                            </v-row>
                            <v-row>
                                <v-col cols="12" class="pa-0 ma-0">
                                    <v-expansion-panels class="mb-1" v-for="(attribute_group, i) in attribute_groups"
                                                        :key="attribute_group.id" v-model="expandPanelGroups" multiple>
                                        <v-expansion-panel>
                                            <v-expansion-panel-header color="primary--text"
                                                                      class="body-1 text-uppercase pa-3">
                                                {{ attribute_group.title }}
                                            </v-expansion-panel-header>
                                            <v-expansion-panel-content>
                                                <!--TYPES-->
                                                <v-expansion-panels multiple focusable class="items"
                                                                    v-model="expand_group_items[i].values">
                                                    <v-expansion-panel v-for="attribute_item in attribute_group.attribute_group_items"
                                                                       :key="attribute_item.id" class="item-panel">
                                                        <v-expansion-panel-header class="pa-2 font-weight-bold primary--text rounded-0">
                                                            <v-row>
                                                                <!--<v-icon small left>mdi-account</v-icon>-->
                                                                <span>
                                                                    {{ attribute_item.attribute_group_item.title }}
                                                                </span>
                                                            </v-row>
                                                        </v-expansion-panel-header>
                                                        <v-expansion-panel-content class="pt-0">
                                                            <v-row align="center">
                                                                <v-col>
                                                                    <AttributeContainer :attribute_item="attribute_item"
                                                                                        :edit="edit" :modify="modify"
                                                                                        :report_item_id="report_item.id"
                                                                                        :read_only="read_only" />
                                                                </v-col>
                                                                <v-col class="d-flex justify-end" cols="auto">
                                                                    <v-btn v-if="!!attribute_item.attribute_group_item.ai_provider_id"
                                                                           text small
                                                                           @click="auto_generate(attribute_item.attribute_group_item.id)"
                                                                           :title="$t('report_item.tooltip.auto_generate')">
                                                                        <v-icon>
                                                                            {{ auto_generate_icon[attribute_item.attribute_group_item.id] || 'mdi-creation' }}
                                                                        </v-icon>
                                                                    </v-btn>
                                                                </v-col>
                                                            </v-row>
                                                        </v-expansion-panel-content>
                                                    </v-expansion-panel>
                                                </v-expansion-panels>
                                            </v-expansion-panel-content>
                                        </v-expansion-panel>
                                    </v-expansion-panels>
                                </v-col>
                            </v-row>

                            <v-row no-gutters class="pt-2">
                                <v-col cols="12">
                                    <v-alert v-if="show_validation_error" dense type="error" text>
                                        {{ $t('error.validation') }}
                                    </v-alert>
                                    <v-alert v-if="show_error" dense type="error" text>
                                        {{ $t('report_item.error') }}
                                    </v-alert>
                                </v-col>
                            </v-row>
                        </v-form>
                    </v-col>
                    <v-col v-if="verticalView" :cols="verticalView ? 6 : 0"
                           style="height:calc(100vh - 3em); overflow-y: auto;" class="pa-5 taranis-ng-vertical-view">
                        <NewsItemSelector ref="new_item_selector" attach=".taranis-ng-vertical-view"
                                          :values="news_item_aggregates" :modify="modify" :report_item_id="this.report_item.id"
                                          :edit="edit" :verticalView="true" />
                    </v-col>
                </v-row>

            </v-card>
        </v-dialog>
    </v-row>
</template>

<style>
    .taranis-ng-vertical-view {
        position: relative;
    }

    .v-dialog__content,
    .v-dialog--fullscreen {
        position: fixed;
    }
</style>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import { createNewReportItem, updateReportItem, lockReportItem, unlockReportItem, holdLockReportItem, getReportItem, getReportItemData, getReportItemLocks, aiGenerate } from "@/api/analyze";
    import { getEntityTypeStates } from "@/api/state";
    import AttributeContainer from "@/components/common/attribute/AttributeContainer";
    import NewsItemSelector from "@/components/analyze/NewsItemSelector";
    import RemoteReportItemSelector from "@/components/analyze/RemoteReportItemSelector";
    import MessageBox from "@/components/common/MessageBox";

    export default {
        name: "NewReportItem",
        props: {
            add_button: Boolean,
            read_only: Boolean,
        },
        mixins: [AuthMixin],
        components: { NewsItemSelector, AttributeContainer, RemoteReportItemSelector, MessageBox },

        data: () => ({
            expand_panel_groups: [],
            expand_group_items: [],
            visible: false,
            edit: false,
            modify: true,
            overlay: false,
            local_reports: true,
            key_timeout: null,
            show_validation_error: false,
            show_error: false,
            showCloseConfirmation: false,
            initialFormState: null,
            confirmCloseButtons: [
                { label: 'confirm_close.continue', color: '', action: 'continue'},
                { label: 'confirm_close.save_and_close', color: 'primary', action: 'save'},
                { label: 'confirm_close.close', color: 'error', action: 'close'}
            ],
            report_types: [],
            selected_type: null,
            attribute_groups: [],
            news_item_aggregates: [],
            remote_report_items: [],
            field_locks: {
                title_prefix: false,
                title: false
            },
            report_item: {
                id: null,
                uuid: null,
                title: "",
                title_prefix: "",
                report_item_type_id: null,
                state_id: null,
                news_item_aggregates: [],
                remote_report_items: [],
                attributes: []
            },
            auto_generate_icon: {},
            auto_generate_icon_timer: {},
            // State management
            available_states: [],
        }),

        watch: {
            // Remove double scrollbars when a report item is open
            // There is a very nasty bug: when you open this screen for a second time, two scrollbars are shown.
            // In the past, there was an attempt to fix this, but previous code doesn't work (possibly unfinished?)
            // The problem is that the main 'html' tag is missing the 'overflow-y-hidden' class/style on the second open
            // 1. open: new inicialization works ok    2. open: something remove style when the same screen is visible again
            // This bug exist across mulitple places in Taranis (search for tag: DOUBLE_SCROLLBAR).
            // It's good to find a better solution than this quick fix.
            visible(val) {
                if (val) {
                    document.documentElement.style.overflow = 'hidden'
                }
                else {
                    document.documentElement.style.overflow = 'auto'
                }
            },

            $route() {
                this.local_reports = !window.location.pathname.includes('/group/');
            },
        },

        computed: {
            verticalView: {
                get() {
                    return this.$store.getters.getVerticalView;
                },
                set(val) {
                    this.$store.commit("setVerticalView", val);
                }
            },

            canCreate() {
                return this.checkPermission(Permissions.ANALYZE_CREATE) && this.local_reports === true
            },

            canModify() {
                return this.edit === false || (this.checkPermission(Permissions.ANALYZE_UPDATE) && this.modify === true);
            },

            expandPanelGroups() {
                return this.expand_groups();
            },

        },

        methods: {
            addEmptyReportItem() {
                this.visible = true;
                this.modify = true;
                this.edit = false
                this.overlay = false
                this.show_error = false;
                this.field_locks.title = false;
                this.field_locks.title_prefix = false;
                this.attachmets_attributes_count = 0;
                this.selected_type = null;
                this.attribute_groups = [];
                this.news_item_aggregates = [];
                this.remote_report_items = []
                this.report_item.id = null;
                this.report_item.uuid = null;
                this.report_item.title = "";
                this.report_item.title_prefix = "";
                this.report_item.report_item_type_id = null;
                this.selectDefaultState();
                this.resetValidation();
                this.reset_auto_generate();
                this.initialFormState = this.snapshotForm()
            },

            reportSelected() {

                this.attribute_groups = [];
                this.expand_group_items = [];

                for (let i = 0; i < this.selected_type.attribute_groups.length; i++) {
                    let group = {
                        id: this.selected_type.attribute_groups[i].id,
                        title: this.selected_type.attribute_groups[i].title,
                        attribute_group_items: []
                    };

                    for (let j = 0; j < this.selected_type.attribute_groups[i].attribute_group_items.length; j++) {
                        group.attribute_group_items.push({
                            attribute_group_item: this.selected_type.attribute_groups[i].attribute_group_items[j],
                            values: []
                        })
                    }

                    this.attribute_groups.push(group)
                    this.expand_group_items.push({ values: Array.from(Array(group.attribute_group_items.length).keys()) });
                }
            },

            cancel() {
                // Check for unsaved changes only in create mode (not edit mode)
                if (!this.edit && this.hasUnsavedChanges()) {
                    this.showCloseConfirmation = true;
                    return;
                }

                this.closeDialog();
            },

            confirmClose() {
                this.showCloseConfirmation = false;
                this.closeDialog();
            },

            saveAndClose() {
                this.showCloseConfirmation = false;
                this.addReportItem();
            },

            closeDialog() {
                setTimeout(() => {
                    this.$root.$emit('change-state', 'DEFAULT');
                    this.resetValidation();
                    this.visible = false;
                    this.$root.$emit('first-dialog', '');
                }, 150);
            },

            addReportItem() {
                this.$validator.validateAll().then(() => {

                    if (!this.$validator.errors.any()) {

                        this.overlay = true

                        this.show_validation_error = false;
                        this.show_error = false;

                        this.report_item.report_item_type_id = this.selected_type.id;

                        this.report_item.news_item_aggregates = [];
                        for (let i = 0; i < this.news_item_aggregates.length; i++) {
                            this.report_item.news_item_aggregates.push(
                                {
                                    id: this.news_item_aggregates[i].id
                                }
                            )
                        }

                        this.report_item.remote_report_items = [];
                        for (let i = 0; i < this.remote_report_items.length; i++) {
                            this.report_item.remote_report_items.push(
                                {
                                    id: this.remote_report_items[i].id
                                }
                            )
                        }

                        this.report_item.attributes = [];
                        for (let i = 0; i < this.attribute_groups.length; i++) {

                            for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {

                                for (let k = 0; k < this.attribute_groups[i].attribute_group_items[j].values.length; k++) {

                                    let value = this.attribute_groups[i].attribute_group_items[j].values[k].value
                                    let value_description = this.attribute_groups[i].attribute_group_items[j].values[k].value_description
                                    if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'CPE') {
                                        value = value.replace("*", "%")
                                    } else if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'BOOLEAN') {
                                        if (value === true) {
                                            value = "true"
                                        } else {
                                            value = "false"
                                        }
                                    }

                                    if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type !== 'ATTACHMENT') {
                                        this.report_item.attributes.push({
                                            id: -1,
                                            value: value,
                                            value_description: value_description,
                                            attribute_group_item_id: this.attribute_groups[i].attribute_group_items[j].attribute_group_item.id
                                        })
                                    }
                                }
                            }
                        }

                        createNewReportItem(this.report_item).then((response) => {
                            this.report_item.id = response.data;

                            this.attachmets_attributes_count = 0
                            for (let i = 0; i < this.attribute_groups.length; i++) {
                                for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                                    if (this.attribute_groups[i].attribute_group_items[j].attribute_group_item.attribute.type === 'ATTACHMENT') {
                                        this.attachmets_attributes_count++
                                    }
                                }
                            }

                            if (this.attachmets_attributes_count > 0) {
                                this.$root.$emit('dropzone-new-process', { report_item_id: response.data });
                            } else {
                                this.$root.$emit('attachments-uploaded', {});
                            }

                        }).catch(() => {
                            this.show_error = true;
                            this.overlay = false
                        })

                    } else {
                        this.show_validation_error = true;
                    }
                })
            },

            saveReportItem(field_id) {
                if (!this.edit) {
                    return;
                }

                let data = {}
                data.update = true
                if (field_id === 'title') {
                    data.title = this.report_item.title
                } else if (field_id === 'title_prefix') {
                    data.title_prefix = this.report_item.title_prefix
                } else if (field_id === 'state_id') {
                    data.state_id = this.report_item.state_id
                }

                updateReportItem(this.report_item.id, data).then(() => { })
                unlockReportItem(this.report_item.id, { 'field_id': field_id }).then(() => { })
            },

            resetValidation() {
                this.$validator.reset();
                this.show_validation_error = false;
            },

            getLockedStyle(field_id) {
                return this.field_locks[field_id] === true ? 'locked-style' : ''
            },

            onFocus(field_id) {
                if (this.edit === true) {
                    lockReportItem(this.report_item.id, { 'field_id': field_id }).then(() => { })
                }
            },

            onKeyUp(field_id) {
                if (this.edit === true) {

                    clearTimeout(this.key_timeout);
                    let self = this;
                    this.key_timeout = setTimeout(function () {
                        holdLockReportItem(self.report_item.id, { 'field_id': field_id }).then(() => {
                        })
                    }, 1000);
                }
            },

            report_item_locked(data) {
                if (this.edit === true && this.report_item.id === data.report_item_id) {
                    if (data.user_id !== this.$store.getters.getUserId) {
                        this.field_locks[data.field_id] = true
                    }
                }
            },

            report_item_unlocked(data) {
                if (this.edit === true && this.report_item.id === data.report_item_id) {
                    if (data.user_id !== this.$store.getters.getUserId) {
                        this.field_locks[data.field_id] = false
                    }
                }
            },

            report_item_updated(data_info) {
                if (this.edit === true && this.report_item.id === data_info.report_item_id) {
                    if (data_info.user_id !== this.$store.getters.getUserId) {
                        getReportItemData(this.report_item.id, data_info).then((response) => {
                            let data = response.data
                            if (data.title !== undefined) {
                                this.report_item.title = data.title
                            } else if (data.title_prefix !== undefined) {
                                this.report_item.title_prefix = data.title_prefix
                            } else if (data.state_id !== undefined) {
                                this.report_item.state_id = data.state_id
                            }
                            // if more users work on the same report -> update locked field with new value
                            // there is duplicity code attributes_mixin.js: report_item_updated() but runs later (up 2 seconds) this place is much more faster
                            if (data.update !== undefined) {
                                endLoop: for (let i = 0; i < this.attribute_groups.length; i++) {
                                    for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                                        for (let k = 0; k < this.attribute_groups[i].attribute_group_items[j].values.length; k++) {
                                            if (this.attribute_groups[i].attribute_group_items[j].values[k].id == data.attribute_id) {
                                                this.attribute_groups[i].attribute_group_items[j].values[k].value = data.attribute_value;
                                                this.attribute_groups[i].attribute_group_items[j].values[k].value_description = data.attribute_value_description;
                                                break endLoop;
                                            }
                                        }
                                    }
                                }
                            }
                        })
                    }
                }
            },

            showDetail(report_item) {
                this.initialFormState = null;

                this.reset_auto_generate();
                getReportItem(report_item.id).then((response) => {
                    let data = response.data;

                    this.edit = true;
                    this.overlay = false;
                    this.show_error = false;
                    this.modify = report_item.modify;

                    this.field_locks.title = false;
                    this.field_locks.title_prefix = false;

                    this.selected_type = null;
                    this.attribute_groups = [];
                    this.news_item_aggregates = data.news_item_aggregates;
                    this.remote_report_items = data.remote_report_items;

                    this.report_item.id = data.id;
                    this.report_item.uuid = data.uuid;
                    this.report_item.title = data.title;
                    this.report_item.title_prefix = data.title_prefix;
                    this.report_item.report_item_type_id = data.report_item_type_id;
                    this.report_item.state_id = data.state_id;

                    if (!this.report_types || !this.report_types.length) {
                        return;
                    }

                    for (let i = 0; i < this.report_types.length; i++) {
                        if (this.report_types[i].id === this.report_item.report_item_type_id) {
                            this.selected_type = this.report_types[i];

                            this.expand_panel_groups = Array.from(Array(this.selected_type.attribute_groups.length).keys());
                            this.expand_group_items = [];

                            for (let j = 0; j < this.expand_panel_groups.length; j++) {
                                this.expand_group_items.push({ values: Array.from(Array(this.selected_type.attribute_groups[j].attribute_group_items.length).keys()) });
                            }
                            break;
                        }
                    }
                    this.visible = true;

                    getReportItemLocks(this.report_item.id).then((response) => {
                        let locks_data = response.data

                        if (locks_data.title !== undefined && locks_data.title !== null) {
                            this.field_locks['title'] = true
                        } else if (locks_data.title_prefix !== undefined && locks_data.title_prefix !== null) {
                            this.field_locks['title_prefix'] = true
                        }

                        for (let i = 0; i < this.selected_type.attribute_groups.length; i++) {
                            let group = {
                                id: this.selected_type.attribute_groups[i].id,
                                title: this.selected_type.attribute_groups[i].title,
                                attribute_group_items: []
                            };

                            for (let j = 0; j < this.selected_type.attribute_groups[i].attribute_group_items.length; j++) {

                                let values = [];
                                for (let k = 0; k < data.attributes.length; k++) {
                                    if (data.attributes[k].attribute_group_item_id === this.selected_type.attribute_groups[i].attribute_group_items[j].id) {

                                        let value = data.attributes[k].value
                                        let value_description = data.attributes[k].value_description
                                        if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                            value = value.replace("%", "*")
                                        } else if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                            value = value === "true";
                                        }

                                        let locked = false
                                        if (locks_data["'" + data.attributes[k].id + "'"] !== undefined && locks_data["'" + data.attributes[k].id + "'"] !== null) {
                                            locked = true
                                        }

                                        values.push({
                                            id: data.attributes[k].id,
                                            index: values.length,
                                            value: value,
                                            value_description: value_description,
                                            binary_mime_type: data.attributes[k].binary_mime_type,
                                            binary_size: data.attributes[k].binary_size,
                                            binary_description: data.attributes[k].binary_description,
                                            last_updated: data.attributes[k].last_updated,
                                            user: data.attributes[k].user,
                                            locked: locked,
                                            remote: false
                                        });
                                    }
                                }

                                for (let l = 0; l < data.remote_report_items.length; l++) {
                                    for (let k = 0; k < data.remote_report_items[l].attributes.length; k++) {
                                        if (data.remote_report_items[l].attributes[k].attribute_group_item_title === this.selected_type.attribute_groups[i].attribute_group_items[j].title) {

                                            let value = data.remote_report_items[l].attributes[k].value
                                            let value_description = data.remote_report_items[l].attributes[k].value_description
                                            if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                                value = value.replace("%", "*")
                                            } else if (this.selected_type.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                                value = value === "true";
                                            }

                                            values.push({
                                                id: data.remote_report_items[l].attributes[k].id,
                                                index: values.length,
                                                value: value,
                                                value_description: value_description,
                                                last_updated: data.remote_report_items[l].attributes[k].last_updated,
                                                binary_mime_type: data.remote_report_items[l].attributes[k].binary_mime_type,
                                                binary_size: data.remote_report_items[l].attributes[k].binary_size,
                                                binary_description: data.remote_report_items[l].attributes[k].binary_description,
                                                user: { name: data.remote_report_items[l].remote_user },
                                                locked: false,
                                                remote: true
                                            });
                                        }
                                    }
                                }

                                group.attribute_group_items.push({
                                    attribute_group_item: this.selected_type.attribute_groups[i].attribute_group_items[j],
                                    values: values
                                })
                            }

                            this.attribute_groups.push(group)
                        }
                    })
                })
            },

            updateRemoteAttributes() {
                for (let i = 0; i < this.attribute_groups.length; i++) {
                    for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                        for (let k = 0; k < this.attribute_groups[i].attribute_group_items[j].values.length; k++) {
                            if (this.attribute_groups[i].attribute_group_items[j].values[k].remote === true) {
                                this.attribute_groups[i].attribute_group_items[j].values.splice(k, 1)
                                k--
                            }
                        }

                        for (let l = 0; l < this.remote_report_items.length; l++) {
                            for (let k = 0; k < this.remote_report_items[l].attributes.length; k++) {
                                if (this.remote_report_items[l].attributes[k].attribute_group_item_title === this.attribute_groups[i].attribute_group_items[j].title) {

                                    let value = this.remote_report_items[l].attributes[k].value
                                    if (this.attribute_groups[i].attribute_group_items[j].attribute.type === 'CPE') {
                                        value = value.replace("%", "*")
                                    } else if (this.attribute_groups[i].attribute_group_items[j].attribute.type === 'BOOLEAN') {
                                        value = value === "true";
                                    }

                                    this.attribute_groups[i].attribute_group_items[j].values.push({
                                        id: this.remote_report_items[l].attributes[k].id,
                                        index: this.attribute_groups[i].attribute_group_items[j].values.length,
                                        value: value,
                                        last_updated: this.remote_report_items[l].attributes[k].last_updated,
                                        binary_mime_type: this.remote_report_items[l].attributes[k].binary_mime_type,
                                        binary_size: this.remote_report_items[l].attributes[k].binary_size,
                                        binary_description: this.remote_report_items[l].attributes[k].binary_description,
                                        user: { name: this.remote_report_items[l].remote_user },
                                        locked: false,
                                        remote: true
                                    });
                                }
                            }
                        }
                    }
                }
            },

            expand_groups() {
                return this.expand_panel_groups = Array.from(Array(this.attribute_groups.length).keys());
            },

            auto_generate(attribute_group_item_id) {
                if (!this.auto_generate_icon[attribute_group_item_id]) {
                    this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-creation");
                }
                // Prevent multiple runs if icon indicates a timer is active
                if (this.auto_generate_icon[attribute_group_item_id].startsWith("mdi-timer-sand")) {
                    return;
                }
                this.set_auto_generate_icon(attribute_group_item_id, "wait");
                const news_item_agreggate_ids = this.news_item_aggregates.map(item => item.id);
                aiGenerate(attribute_group_item_id, news_item_agreggate_ids).then((response) => {
                    if (response.data.message) {
                        if (this.setAttributeGroupItemValue(attribute_group_item_id, response.data.message)) {
                            this.set_auto_generate_icon(attribute_group_item_id, "");
                            return;
                        }
                    } else {
                        this.setAttributeGroupItemValue(attribute_group_item_id, JSON.stringify(response.data));
                    }
                    this.set_auto_generate_icon(attribute_group_item_id, "error");
                }).catch((error) => {
                    this.setAttributeGroupItemValue(attribute_group_item_id, JSON.stringify(error.response.data));
                    this.set_auto_generate_icon(attribute_group_item_id, "error");
                });
            },

            setAttributeGroupItemValue(attribute_group_item_id, value) {
                for (let i = 0; i < this.attribute_groups.length; i++) {
                    for (let j = 0; j < this.attribute_groups[i].attribute_group_items.length; j++) {
                        const item = this.attribute_groups[i].attribute_group_items[j];
                        if (item.attribute_group_item.id === attribute_group_item_id) {
                            item.values[0].value = value;
                            return true;
                        }
                    }
                }
                return false;
            },

            set_auto_generate_icon(attribute_group_item_id, state) {
                if (this.auto_generate_icon_timer[attribute_group_item_id]) {
                    clearTimeout(this.auto_generate_icon_timer[attribute_group_item_id]);
                    this.auto_generate_icon_timer[attribute_group_item_id] = null;
                }
                if (state === "wait") {
                    const ico = this.auto_generate_icon[attribute_group_item_id]
                    if (ico == "mdi-timer-sand") {
                        this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-timer-sand-complete");
                    } else if (ico == "mdi-timer-sand-complete") {
                        this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-timer-sand-paused");
                    } else {
                        this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-timer-sand");
                    }
                    this.auto_generate_icon_timer[attribute_group_item_id] = setTimeout(() => { this.set_auto_generate_icon(attribute_group_item_id, state) }, 500);
                } else if (state === "error") {
                    this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-exclamation-thick");
                } else {
                    this.$set(this.auto_generate_icon, attribute_group_item_id, "mdi-creation");
                }
            },

            reset_auto_generate() {
                this.auto_generate_icon = {};
                this.auto_generate_icon_timer = {};
            },

            async loadAvailableStates() {
                try {
                    const response = await getEntityTypeStates('report_item');
                    this.available_states = response.data.states;
                } catch (error) {
                    console.error('Failed to load available states for REPORT:', error);
                    this.available_states = [];
                }
            },

            selectDefaultState() {
                if (!this.available_states) return;

                const defaultState = this.available_states.find(state => state.is_default);
                if (defaultState) {
                    this.report_item.state_id = defaultState.id;
                }
            },

            snapshotForm() {
                return JSON.stringify({
                    report_item: this.report_item,
                    selected_type: this.selected_type,
                    news_item_aggregates: this.news_item_aggregates,
                    remote_report_items: this.remote_report_items,
                })
            },

            hasUnsavedChanges() {
                if (this.initialFormState !== null) {
                    return this.snapshotForm() !== this.initialFormState
                }
                return false
            },
        },

        mounted() {
            this.loadAvailableStates();

            this.$root.$on('attachments-uploaded', () => {
                this.attachmets_attributes_count--
                if (this.attachmets_attributes_count <= 0) {
                    this.$validator.reset();
                    this.visible = false;
                    this.overlay = false
                    this.$root.$emit('notification', { type: 'success', loc: 'report_item.successful' });
                }
            });

            this.local_reports = !window.location.pathname.includes('/group/');

            this.$store.dispatch('getAllReportItemTypes', { search: '' }).then(() => {
                this.report_types = this.$store.getters.getReportItemTypes.items;
            });

            this.$root.$on('new-report', (data) => {
                this.visible = true;
                this.selected_type = null;
                this.attribute_groups = [];
                this.news_item_aggregates = data;
                this.$root.$emit('first-dialog', 'push');
            });

            this.$root.$on('report-item-locked', this.report_item_locked);
            this.$root.$on('report-item-unlocked', this.report_item_unlocked);
            this.$root.$on('report-item-updated', this.report_item_updated);
        },

        beforeDestroy() {
            this.$root.$off('attachments-uploaded')
            this.$root.$off('new-report')
            this.$root.$off('show-edit') // ???

            this.$root.$off('report-item-locked', this.report_item_locked);
            this.$root.$off('report-item-unlocked', this.report_item_unlocked);
            this.$root.$off('report-item-updated', this.report_item_updated);
        }
    }
</script>
