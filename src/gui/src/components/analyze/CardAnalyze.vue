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
                                    <div v-if="card.state" class="d-flex align-center">
                                        <v-icon :color="card.state.color" class="mr-2">
                                            {{ card.state.icon }}
                                        </v-icon>
                                        <span>
                                            {{ $te('workflow.states.' + card.state.display_name) ?
                                                $t('workflow.states.' + card.state.display_name) :
                                                card.state.display_name }}
                                        </span>
                                    </div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.created') }}</div>
                                    <span>{{ card.created }}</span>
                                </v-col>
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <!--TOOLBAR-->
                                    <div>
                                        <v-row v-if="!multiSelectActive && !show_remove_action"
                                            v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS">
                                                 <v-btn v-if="canCreateProduct" icon @click.stop="cardItemToolbar('new')"
                                                    :title="$t('analyze.tooltip.publish_item')">
                                                    <v-icon color="info">mdi-file-outline</v-icon>
                                                </v-btn>
                                                <DeleteButton outlinedIcon v-if="canDelete" @delete.stop="showMsgBox('delete')" />
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
            <MessageBox v-model="msgbox_visible" @yes="handleMsgBox" @cancel="cancelMsgBox" :title="$t(msgBoxTitle)"
                :message="card.title" :alert=true>
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>
import Permissions from "@/services/auth/permissions";
import AuthMixin from "@/services/auth/auth_mixin";
import MessageBox from "@/components/common/MessageBox.vue";
import DeleteButton from "@/components/common/buttons/DeleteButton.vue";

export default {
    name: "CardAnalyze",
    components: { MessageBox, DeleteButton },
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
            if (this.card.state) {
                return this.card.state.name;
            } else {
                return "no_state";
            }
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

    },
    mounted() {
        this.$root.$on('multi-select-off', this.multiSelectOff);
    },
    beforeDestroy() {
        this.$root.$off('multi-select-off', this.multiSelectOff);
    }
}
</script>
