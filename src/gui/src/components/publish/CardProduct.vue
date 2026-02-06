<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{ hover }">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" class="status">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ card.product_type_name }}</div>
                                    <span>{{ card.title }}</span>
                                    <span v-if="card.report_items_count">&nbsp;&nbsp;({{ card.report_items_count }})</span>
                                </v-col>
                                <v-col>
                                    <div v-if="card.state" class="d-flex align-center">
                                        <v-icon :color="card.state.color" class="mr-2">
                                            {{ card.state.icon }}
                                        </v-icon>
                                        <span>
                                            {{ $te('workflow.states.' + card.state.display_name) ?
                                               $t('workflow.states.' +
                                               card.state.display_name) : card.state.display_name }}
                                        </span>
                                    </div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.description') }}</div>
                                    <span>{{ card.subtitle }}</span>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.updated') }}</div>
                                    <span>{{ card.updated_at }}</span>
                                    <span v-if="card.updated_by">&nbsp;&nbsp;&nbsp;&nbsp;{{ card.updated_by }}</span>
                                </v-col>

                                <!--TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="canDelete" icon @click.stop="showMsgBox"
                                                   :title="$t('publish.tooltip.delete_item')">
                                                <v-icon color="error">{{ UI.ICON.DELETE }}</v-icon>
                                            </v-btn>
                                        </v-col>
                                    </v-row>
                                </v-col>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
        <v-row>
            <MessageBox v-model="msgbox_visible"
                        @yes="handleMsgBox"
                        @cancel="msgbox_visible = false"
                        :title="$t('common.messagebox.delete')"
                        :message="card.title">
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import MessageBox from "@/components/common/MessageBox.vue";

    export default {
        name: "CardProduct",
        components: { MessageBox },
        props: ['card'],
        data: () => ({
            toolbar: false,
            msgbox_visible: false,
        }),
        mixins: [AuthMixin],
        computed: {
            canDelete() {
                return this.checkPermission(Permissions.PUBLISH_DELETE) && this.card.modify === true
            },
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-product-edit', data)
            },
            deleteClicked(data) {
                this.$root.$emit('delete-product', data)
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "edit":
                        break;

                    case "delete":
                        this.deleteClicked(this.card);
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            },
            showMsgBox() {
                this.msgbox_visible = true;
            },
            handleMsgBox() {
                this.msgbox_visible = false;
                this.cardItemToolbar('delete')
            },
        },
    }
</script>
