<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{ card.tag }}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.title') }}</div>
                                    <div>{{ cardName }}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{ $t('card_item.description') }}</div>
                                    <div>{{ cardDescription }}</div>
                                </v-col>

                                <!--HOVER TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-if="hover" v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="!card.default && checkPermission(deletePermission)" icon class="red"
                                                   @click.stop="showMsgBox">
                                                <v-icon color="white">{{ UI.ICON.DELETE }}</v-icon>
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
            <MessageBox class="justify-center" v-if="msgbox_visible"
                        @buttonYes="handleMsgBox" @buttonCancel="msgbox_visible = false"
                        :title="$t('common.messagebox.delete')" :message="card.name">
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>

    import AuthMixin from "@/services/auth/auth_mixin";
    import MessageBox from "@/components/common/MessageBox.vue";

    export default {
        name: "CardGroup",
        components: { MessageBox },
        props: ['card', 'deletePermission'],
        mixins: [AuthMixin],
        data: () => ({
            toolbar: false,
            msgbox_visible: false,
        }),
        computed: {
            cardName() {
                if (this.card.default) {
                    return this.$t('osint_source_group.default_group')
                } else {
                    return this.card.name
                }
            },
            cardDescription() {
                if (this.card.default) {
                    return this.$t('osint_source_group.default_group_description')
                } else {
                    return this.card.description
                }
            },
            cardStatus() {
                if (this.card.status === undefined) {
                    return "status-green"
                } else {
                    return "status-" + this.card.status
                }
            }
        },
        methods: {
            itemClicked(data) {
                this.$root.$emit('show-edit-src-grp', data)
            },
            deleteClicked(data) {
                this.$root.$emit('delete-item', data)
            },
            cardItemToolbar(action) {
                switch (action) {
                    case "delete":
                        this.deleteClicked(this.card)
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
            }

        }
    }
</script>
