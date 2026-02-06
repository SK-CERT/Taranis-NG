<template>
    <v-container v-bind="UI.CARD.CONTAINER">
        <v-row no-gutters>
            <v-col v-if="multiSelect" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-model="selected" @change="selectionChanged" />
                </v-row>
            </v-col>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{hover}">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2"
                            @click.stop="cardItemToolbar"
                            :color="selectedColor">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="'status ' + cardStatus">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col :style="UI.STYLE.card_tag">
                                    <v-icon center>{{card.tag}}</v-icon>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{card.collector.name}}</div>
                                    <div>{{card.name}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('card_item.description')}}</div>
                                    <div>{{card.description}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('osint_source.last_attempt')}}</div>
                                    <div>{{card.last_attempted}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('osint_source.last_collected')}}</div>
                                    <div>{{card.last_collected}}</div>
                                </v-col>
                                <v-col>
                                    <div class="grey--text">{{$t('osint_source.last_error_message')}}</div>
                                    <div>{{card.last_error_message}}</div>
                                </v-col>
                                <!--TOOLBAR-->
                                <v-col :style="UI.STYLE.card_hover_toolbar">
                                    <v-row v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                        <v-col v-bind="UI.CARD.COL.TOOLS">
                                            <v-btn v-if="checkPermission(deletePermission)" icon @click.stop="showMsgBox">
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
                        :message="card.name">
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>

    import AuthMixin from "@/services/auth/auth_mixin";
    import MessageBox from "@/components/common/MessageBox.vue";

    export default {
        name: "CardSource",
        components: { MessageBox },
        props: ['card', 'deletePermission'],
        data: () => ({
            toolbar: false,
            selected: false,
            msgbox_visible: false,
        }),
        mixins: [AuthMixin],
        computed: {
            cardStatus() {
                if (this.card.status === undefined) {
                    return "status-green"
                } else {
                    return "status-" + this.card.status
                }
            },

            multiSelect() {
                return this.$store.getters.getOSINTSourcesMultiSelect;
            },

            selectedColor() {
                if (this.selected === true && this.multiSelect) {
                    return this.$vuetify.theme.dark ? "blue-grey darken-3" : "orange lighten-4";
                } else {
                    return ""
                }
            },
        },
        methods: {
            selectionChanged() {
                if (this.selected) {
                    this.$store.dispatch('selectOSINTSource', this.card.id);
                } else {
                    this.$store.dispatch('deselectOSINTSource', this.card.id);
                }
            },

            itemClicked(data) {
                this.$root.$emit('show-edit', data)
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

        },
        mounted() {
            this.$root.$on('check-osint-source-card', () => {
                this.selected = true;
                this.$store.commit('addSelection', this.card.id);
            });
            this.$root.$on('uncheck-osint-source-card', () => {
                this.selected = false;
                this.$store.dispatch('deselect', this.card.id);
            });
        },
        beforeDestroy() {
            this.$root.$off('check-osint-source-card');
            this.$root.$off('uncheck-osint-source-card');
        }
    }
</script>
