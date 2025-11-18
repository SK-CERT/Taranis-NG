<template>
    <v-container v-bind="UI.CARD.CONTAINER" class="card-item" data-type="report-item">
        <v-row no-gutters>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged"></v-checkbox>
                </v-row>
            </v-col>

            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{ hover }">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar"
                        :color="selectedColor">

                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + itemStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ card.report_type_name }}</div>
                                    <span>{{ card.title }}</span>
                                </v-col>
                                <v-col>
                                    <div v-if="currentStateObject" class="d-flex align-center">
                                        <v-icon :color="currentStateObject.color" small class="mr-2">{{
                                            currentStateObject.icon }}</v-icon>
                                        <span>{{ $te('workflow.states.' + currentStateObject.display_name) ?
                                            $t('workflow.states.' +
                                                currentStateObject.display_name) : currentStateObject.display_name }}</span>
                                    </div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.created') }}</div>
                                    <span>{{ card.created }}</span>
                                </v-col>
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <!--HOVER TOOLBAR-->
                                    <div v-if="hover">
                                        <v-row v-if="!multiSelectActive && !show_remove_action"
                                            v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS">
                                                <v-btn v-if="canDelete" icon class="red"
                                                    @click.stop="showMsgBox('delete')"
                                                    :title="$t('analyze.tooltip.delete_item')">
                                                    <v-icon color="white">mdi-trash-can-outline</v-icon>
                                                </v-btn>
                                                <v-btn v-if="canCreateProduct" icon @click.stop="cardItemToolbar('new')"
                                                    :title="$t('analyze.tooltip.publish_item')">
                                                    <v-icon color="info">mdi-file-outline</v-icon>
                                                </v-btn>
                                            </v-col>
                                        </v-row>
                                        <v-row v-if="!multiSelectActive && show_remove_action"
                                            v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS">
                                                <v-btn v-if="canModify" icon @click.stop="showMsgBox('remove')"
                                                    :title="$t('analyze.tooltip.remove_item')">
                                                    <v-icon color="accent">mdi-minus-circle-outline</v-icon>
                                                </v-btn>
                                            </v-col>
                                        </v-row>
                                    </div>
                                </v-col>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
        <v-row>
            <MessageBox class="justify-center" v-if="msgbox_visible" @buttonYes="handleMsgBox"
                @buttonCancel="cancelMsgBox" :title="$t(msgBoxTitle)" :message="card.title">
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>
import Permissions from "@/services/auth/permissions";
import AuthMixin from "@/services/auth/auth_mixin";
import MessageBox from "@/components/common/MessageBox.vue";

export default {
    name: "CardAnalyze",
    components: { MessageBox },
    props: {
        card: Object,
        show_remove_action: Boolean,
        preselected: Boolean,
    },
    mixins: [AuthMixin],
    data: () => ({
        toolbar: false,
        selected: false,
        msgbox_visible: false,
        msgbox_action: "",
    }),
    computed: {

        canModify() {
            return this.checkPermission(Permissions.ANALYZE_UPDATE) && (this.card.modify === true || this.card.remote_user !== null)
        },

        canDelete() {
            return this.checkPermission(Permissions.ANALYZE_DELETE) && (this.card.modify === true || this.card.remote_user !== null)
        },

        canCreateProduct() {
            return this.checkPermission(Permissions.PUBLISH_CREATE) && !window.location.pathname.includes('/group/')
        },

        multiSelectActive() {
            return this.$store.getters.getMultiSelectReport
        },

        selectedColor() {
            if (this.selected === true || this.preselected) {
                return this.$vuetify.theme.dark ? "blue-grey darken-3" : "orange lighten-4"
            } else {
                return ""
            }
        },

        itemStatus() {
            // Use actual state name for CSS class, or fallback to 'no_state'
            if (this.card.states && this.card.states.length > 0) {
                return this.card.states[0].name;
            } else {
                return "no_state";
            }
        },

        //currentState() {
        //    // Get the first state from the states array
        //    if (this.card.states && this.card.states.length > 0) {
        //        return this.card.states[0].display_name || this.card.states[0].name;
        //    }
        //    return 'No state';
        //},

        currentStateObject() {
            // Get the first state object from the states array
            if (this.card.states && this.card.states.length > 0) {
                return this.card.states[0];
            }
            return null;
        },

        msgBoxTitle() {
            switch (this.msgbox_action) {
                case "remove":
                    return "common.messagebox.remove";
                default:
                    return "common.messagebox.delete";
            }
        }
    },
    methods: {

        selectionChanged() {
            if (this.selected === true) {
                this.$store.dispatch("selectReport", { 'id': this.card.id, 'item': this.card })
            } else {
                this.$store.dispatch("deselectReport", { 'id': this.card.id, 'item': this.card })
            }
        },

        itemClicked(data) {
            if (this.checkPermission(Permissions.ANALYZE_ACCESS) && (this.card.access === true || data.remote_user !== null)) {
                if (data.remote_user === null) {
                    this.$emit('show-report-item-detail', data);
                } else {
                    this.$emit('show-remote-report-item-detail', data);
                }
            }
        },

        deleteClicked(data) {
            this.$root.$emit('delete-report-item', data)
        },

        cardItemToolbar(action) {
            switch (action) {
                case "delete":
                    this.deleteClicked(this.card);
                    break;

                case "new":
                    this.$root.$emit('new-product', [this.card]);
                    break;

                case "remove":
                    this.$emit('remove-report-item-from-selector', this.card);
                    break;

                default:
                    this.toolbar = false;
                    this.itemClicked(this.card);
                    break;
            }
        },

        multiSelectOff() {
            this.selected = false
        },

        showMsgBox(action) {
            this.msgbox_action = action;
            this.msgbox_visible = true;
        },

        cancelMsgBox() {
            this.msgbox_action = ""
            this.msgbox_visible = false;
        },

        handleMsgBox() {
            this.msgbox_visible = false;
            this.cardItemToolbar(this.msgbox_action);
        },

        handleStateUpdate(data) {
            // Update card states when states are changed via SSE or NewReportItem
            const targetId = data.report_item_id || data.entity_id;
            if (targetId === this.card.id) {
                console.log('Updating states for report item', targetId, data);

                // Handle single state update
                if (data.state_object) {
                    // Single state object provided
                    this.card.states = [data.state_object];
                } else if (data.state) {
                    // Single state name provided, create minimal state object
                    const availableState = this.$parent && this.$parent.availableStates &&
                        this.$parent.availableStates.find(state => state.display_name === data.state);
                    if (availableState) {
                        this.card.states = [availableState];
                    } else {
                        // Create minimal object with just the state name
                        this.card.states = [{
                            name: data.state,
                            display_name: data.state,
                            color: '#9E9E9E', // Default grey color
                            icon: 'mdi-circle' // Default icon
                        }];
                    }
                } else if (data.state_objects && Array.isArray(data.state_objects)) {
                    // Backward compatibility: multiple state objects (use first)
                    this.card.states = data.state_objects.slice(0, 1);
                } else if (data.stateObjects && Array.isArray(data.stateObjects)) {
                    // Backward compatibility: stateObjects (use first)
                    this.card.states = data.stateObjects.slice(0, 1);
                } else if (data.states && Array.isArray(data.states)) {
                    // Backward compatibility: state names array (use first)
                    const stateName = data.states[0];
                    if (stateName) {
                        const availableState = this.$parent && this.$parent.availableStates &&
                            this.$parent.availableStates.find(state => state.name === stateName);
                        if (availableState) {
                            this.card.states = [availableState];
                        } else {
                            this.card.states = [{
                                name: stateName,
                                display_name: stateName.charAt(0).toUpperCase() + stateName.slice(1).replace(/_/g, ' '),
                                color: '#9E9E9E',
                                icon: 'mdi-circle'
                            }];
                        }
                    } else {
                        this.card.states = [];
                    }
                } else {
                    // No state data provided, clear states
                    this.card.states = [];
                }

                // Force Vue reactivity update
                this.$forceUpdate();
            }
        }
    },
    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);
        this.$root.$on('report-item-states-updated', this.handleStateUpdate);
        this.$root.$on('report-item-updated', this.handleStateUpdate);
    },
    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
        this.$root.$off('report-item-states-updated', this.handleStateUpdate);
        this.$root.$off('report-item-updated', this.handleStateUpdate);
    }
}
</script>
