<template>
    <v-container v-bind="UI.CARD.CONTAINER" :data-type="this.cardType" :data-open="opened" :data-set="data_set">
        <v-row>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!preselected" v-model="selected" @change="selectionChanged" />
                </v-row>
            </v-col>
            <v-col :class="UI.CLASS.card_offset">
                <v-hover v-slot="{ hover }">
                    <v-card v-bind="UI.CARD.HOVER" :elevation="hover ? 12 : 2" @click.stop="cardItemToolbar"
                            @mouseenter.native="toolbar = true" @mouseleave.native="toolbar = cardFocus"
                            :color="selectedColor">
                        <!--CONTENT-->
                        <v-layout v-bind="UI.CARD.LAYOUT" :class="['status', cardStatus, { 'read': isRead }]">
                            <v-row v-bind="UI.CARD.ROW.CONTENT">
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div v-if="singleAggregate">
                                        {{ $t('card_item.source') }}:
                                        <strong>
                                            {{ card.news_items[0].news_item_data.osint_source_name || card.news_items[0].news_item_data.source }}
                                            ({{ (card.news_items[0].news_item_data.osint_source_type || '').split(' ')[0] }})
                                        </strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div v-if="singleAggregate" align="center">
                                        {{ $t('card_item.published') }}:
                                        <strong>{{ card.news_items[0].news_item_data.published }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div align="right">
                                        {{ $t('card_item.collected') }}: <strong>{{ card.created }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.TITLE">
                                    <div v-if="word_list_regex" v-html="wordCheck(card.title)"></div>
                                    <div v-else>{{ card.title }}</div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.REVIEW" class="review-content">
                                    <div v-if="!compact_mode">
                                        <div v-if="word_list_regex" v-html="wordCheck(card.description)"></div>
                                        <div v-else>{{ card.description }}</div>
                                    </div>
                                </v-col>
                                <v-row v-bind="UI.CARD.FOOTER">
                                    <v-col cols="8" class="footer-content">
                                        <template v-if="!singleAggregate">
                                            <v-btn depressed small color="primary" data-button="aggregate"
                                                   @click.stop="openCard">
                                                <v-icon v-if="opened" left>mdi-arrow-down-drop-circle</v-icon>
                                                <v-icon v-if="!opened" left>mdi-arrow-right-drop-circle</v-icon>
                                                <div class="subtitle-2">
                                                    {{ $t('card_item.aggregated_items') }}: {{ card.news_items.length }}
                                                </div>
                                            </v-btn>
                                        </template>

                                        <span class="caption font-weight-bold px-0 mt-1 pb-0 pt-0 info--text source-link">
                                            {{ itemLink }}
                                        </span>

                                        <span v-if="card.in_reports_count > 0" class="pl-2">
                            <v-btn depressed x-small color="orange lighten-2"
                                   @click.stop="showInReports"
                                   :disabled="disable_reports_button"
                                   :title="$t('assess.tooltip.show_reports')">
                                {{ $t('card_item.in_analyze') }}<span v-if="card.in_reports_count > 1"> ({{ card.in_reports_count }})</span>
                            </v-btn>
                        </span>

                        <v-icon v-if="card.comments != ''" class="pl-2"
                                color="orange lighten-2">mdi-comment</v-icon>
                    </v-col>
                    <v-col cols="4">
                                        <!--TOOLBAR-->
                                        <div>
                                            <v-row v-if="!multiSelectActive && !analyze_selector"
                                                   v-bind="UI.CARD.TOOLBAR.COMPACT"
                                                   :style="UI.STYLE.card_toolbar_strip_bottom">
                                                <v-col v-bind="UI.CARD.COL.TOOLS">
                                                    <span class="ml-5 grey--text">
                                                        <v-btn v-if="canModify" icon
                                                               @click.stop="cardItemToolbar('like')" data-btn="like"
                                                               :title="$t('assess.tooltip.like_item')">
                                                            <v-icon :color="buttonStatus(card.me_like)">
                                                                {{ card.likes ? 'mdi-thumb-up' : 'mdi-thumb-up-outline' }}
                                                            </v-icon>
                                                        </v-btn>
                                                        {{ card.likes }}
                                                    </span>
                                                    <span class="mr-5 grey--text">
                                                        <v-btn v-if="canModify" icon
                                                               @click.stop="cardItemToolbar('unlike')"
                                                               :title="$t('assess.tooltip.dislike_item')"
                                                               data-btn="unlike">
                                                            <v-icon :color="buttonStatus(card.me_dislike)">
                                                                {{ card.dislikes ? 'mdi-thumb-down' : 'mdi-thumb-down-outline' }}
                                                            </v-icon>
                                                        </v-btn>
                                                        {{ card.dislikes }}
                                                    </span>

                                                    <v-btn v-if="singleAggregate" icon
                                                           @click.stop="cardItemToolbar('link')" data-btn="link"
                                                           :title="$t('assess.tooltip.open_source')">
                                                        <a class="alink" :href="card.news_items[0].news_item_data.link"
                                                           target="_blank" rel="noreferer">
                                                            <v-icon color="primary">mdi-open-in-app</v-icon>
                                                        </a>
                                                    </v-btn>
                                                    <v-btn v-if="!singleAggregate && canModify" icon
                                                           @click.stop="cardItemToolbar('ungroup')" data-btn="ungroup"
                                                           :title="$t('assess.tooltip.ungroup_items')">
                                                        <v-icon color="primary">mdi-ungroup</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canCreateReport" icon
                                                           @click.stop="cardItemToolbar('new')"
                                                           :title="$t('assess.tooltip.analyze_item')" data-btn="new">
                                                        <v-icon color="primary">mdi-file-outline</v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('read')"
                                                           data-btn="read" :title="$t('assess.tooltip.read_item')">
                                                        <v-icon :color="buttonStatus(card.read)">
                                                            {{ card.read ? 'mdi-eye' : 'mdi-eye-outline' }}
                                                        </v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canModify" icon
                                                           @click.stop="cardItemToolbar('important')"
                                                           :title="$t('assess.tooltip.important_item')"
                                                           data-btn="important">
                                                        <v-icon :color="buttonStatus(card.important)">
                                                            {{ card.important ? 'mdi-star' : 'mdi-star-outline' }}
                                                        </v-icon>
                                                    </v-btn>
                                                    <v-btn v-if="canDelete" icon @click.stop="showMsgBox()"
                                                           :title="$t('assess.tooltip.delete_item')" data-btn="delete">
                                                        <v-icon color="error">{{ UI.ICON.DELETE }}</v-icon>
                                                    </v-btn>
                                                </v-col>
                                            </v-row>
                                            <v-row v-if="analyze_selector && analyze_can_modify"
                                                   v-bind="UI.CARD.TOOLBAR.COMPACT" :style="UI.STYLE.card_toolbar">
                                                <v-col v-bind="UI.CARD.COL.TOOLS">
                                                    <v-btn icon @click.stop="cardItemToolbar('remove')"
                                                           :title="$t('assess.tooltip.remove_item')">
                                                        <v-icon color="primary">mdi-minus-circle-outline</v-icon>
                                                    </v-btn>
                                                </v-col>
                                            </v-row>
                                        </div>
                                    </v-col>
                                </v-row>
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
        <div v-if="opened" dark class="ml-16 mb-8 rounded">
            <CardAssessItem v-for="news_item in card.news_items" :key="news_item.id" :news_item="news_item"
                            :analyze_selector="analyze_selector" :compact_mode="compact_mode" :word_list_regex="word_list_regex"
                            @show-item-detail="showItemDetail(news_item)" />
        </div>
    </v-container>
</template>

<script>
    import CardAssessItem from "@/components/assess/CardAssessItem";
    import { groupAction, voteNewsItemAggregate } from "@/api/assess";
    import { readNewsItemAggregate } from "@/api/assess";
    import { importantNewsItemAggregate } from "@/api/assess";
    import { deleteNewsItemAggregate } from "@/api/assess";
    import AuthMixin from "@/services/auth/auth_mixin";
    import Permissions from "@/services/auth/permissions";
    import MessageBox from "@/components/common/MessageBox.vue";
    import CardMixin from "@/components/assess/card_mixin";

    export default {
        name: "CardAssess",
        props: {
            card: Object,
            analyze_selector: Boolean,
            analyze_can_modify: Boolean,
            compact_mode: Boolean,
            preselected: Boolean,
            word_list_regex: String,
            aggregate_opened: Boolean,
            data_set: String,
            disable_reports_button: Boolean
        },
        mixins: [AuthMixin, CardMixin],
        components: { CardAssessItem, MessageBox },
        data: () => ({
            opened: false,
        }),
        computed: {
            canModify() {
                return this.checkPermission(Permissions.ASSESS_UPDATE)
            },

            canDelete() {
                return this.checkPermission(Permissions.ASSESS_DELETE)
            },

            singleAggregate() {
                return this.card.news_items.length === 1
            },

            itemLink() {
                if (this.card.news_items.length === 1) {
                    return this.card.news_items[0].news_item_data.link
                } else {
                    return ""
                }
            },

            cardType() {
                if (this.singleAggregate) {
                    return "single";
                } else {
                    return "aggregate";
                }
            },
        },

        methods: {
            showItemDetail(data) {
                this.$emit('show-item-detail', data);

                this.stateChange();
            },

            openCard() {
                this.opened = !this.opened;
                // TODO (JP) this should maybe emit 'aggregate-open'? looks bad..
                this.$emit('i', { 'id': this.card.id, 'opened': this.opened });
                this.$emit('card-items-reindex');
                this.$root.$emit('key-remap');

            },

            selectionChanged() {
                if (this.selected === true) {
                    this.$store.dispatch("select", { 'type': 'AGGREGATE', 'id': this.card.id, 'item': this.card })
                } else {
                    this.$store.dispatch("deselect", { 'type': 'AGGREGATE', 'id': this.card.id, 'item': this.card })
                }
            },

            itemClicked(data) {
                if (this.card.news_items.length === 1) {
                    this.$emit('show-single-aggregate-detail', {
                        'data': data,
                        'isSelector': this.analyze_selector,
                        'id': this.$parent.selfID
                    });
                } else {
                    this.$emit('show-aggregate-detail', {
                        'data': data,
                        'isSelector': this.analyze_selector,
                        'id': this.$parent.selfID
                    });
                }
                this.stateChange();
            },

            showInReports() {
                this.$emit('show-reports-for-item', this.card);
            },

            cardItemToolbar(action) {

                switch (action) {
                    case "like":
                        voteNewsItemAggregate(this.getGroupId(), this.card.id, 1).then(() => {
                        });
                        break;

                    case "unlike":
                        voteNewsItemAggregate(this.getGroupId(), this.card.id, -1).then(() => {
                        });
                        break;

                    case "link":
                        break;

                    case "new":
                        this.$root.$emit('new-report', [this.card]);
                        break;

                    case "remove":
                        this.$emit('remove-item-from-selector', this.card);
                        break;

                    case "important":
                        importantNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
                        });
                        break;

                    case "read":
                        readNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
                        });
                        break;

                    case "delete":
                        deleteNewsItemAggregate(this.getGroupId(), this.card.id).then(() => {
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                        break;

                    case "ungroup":
                        this.opened = false;  // Close the expanded view before ungrouping
                        groupAction({
                            'group': this.getGroupId(),
                            'action': 'UNGROUP',
                            'items': [{ 'type': 'AGGREGATE', 'id': this.card.id }]
                        }).then(() => {
                        }).catch((error) => {
                            this.$root.$emit('notification',
                                {
                                    type: 'error',
                                    loc: 'error.' + error.response.data
                                }
                            )
                        });
                        break;

                    default:
                        this.toolbar = false;
                        this.itemClicked(this.card);
                        break;
                }
            },
        },

        created() {
            this.opened = this.aggregate_opened;
        }
    }
</script>

<style scoped>
    .footer-content {
        min-height: 48px;
    }

    .status.read {
        opacity: 0.5;
    }

    .theme--light .status.read {
        background-color: #f5f5f5;
    }

    .theme--dark .status.read {
        background-color: #2c2c2c;
    }

    .status.read .v-card {
        filter: grayscale(30%);
    }
</style>
