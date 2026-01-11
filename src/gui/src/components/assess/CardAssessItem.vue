<template>
    <v-container v-bind="UI.CARD.CONTAINER" data-type="item">
        <v-row>
            <v-col v-if="multiSelectActive" :style="UI.STYLE.card_selector_zone">
                <v-row justify="center" align="center">
                    <v-checkbox v-if="!analyze_selector" v-model="selected" @change="selectionChanged"></v-checkbox>
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
                                <!--COLLECTED, PUBLISHED, SOURCE-->
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div>
                                        {{ $t('card_item.source') }}:
                                        <strong>{{ news_item.news_item_data.osint_source_type }} - {{
                                            news_item.news_item_data.osint_source_name ||
                                            news_item.news_item_data.source }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div align="center">
                                        {{ $t('card_item.published') }}:
                                        <strong>{{ news_item.news_item_data.published }}</strong>
                                    </div>
                                </v-col>
                                <v-col v-bind="UI.CARD.COL.INFO">
                                    <div align="right">
                                        {{ $t('card_item.collected') }}: <strong>{{ news_item.news_item_data.collected
                                        }}</strong>
                                    </div>
                                </v-col>

                                <!--TITLE-->
                                <v-col v-bind="UI.CARD.COL.TITLE">
                                    <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.title)">
                                    </div>
                                    <div v-else>{{ news_item.news_item_data.title }}</div>
                                </v-col>

                                <!--REVIEW-->
                                <v-col v-bind="UI.CARD.COL.REVIEW" class="review-content">
                                    <div v-if="!compact_mode">
                                        <div v-if="word_list_regex" v-html="wordCheck(news_item.news_item_data.review)">
                                        </div>
                                        <div v-else>{{ news_item.news_item_data.review }}</div>
                                    </div>
                                </v-col>

                                <!--FOOTER-->
                                <v-row v-bind="UI.CARD.FOOTER">
                                    <v-col cols="11">
                                        <span v-if="canModify" class="caption font-weight-bold pl-2 pr-1"
                                            style="cursor: pointer;" @click.stop="cardItemToolbar('like')"
                                            :title="$t('assess.tooltip.like_item')">
                                            <v-icon :color="buttonStatus(news_item.me_like)"
                                                size="12">mdi-thumb-up</v-icon> {{ news_item.likes }}
                                        </span>
                                        <span v-else class="caption font-weight-bold grey--text pl-2 pr-1">
                                            <v-icon color="grey" size="12">mdi-thumb-up</v-icon> {{ news_item.likes }}
                                        </span>

                                        <span v-if="canModify" class="caption font-weight-bold pl-1 pr-2"
                                            style="cursor: pointer;" @click.stop="cardItemToolbar('unlike')"
                                            :title="$t('assess.tooltip.dislike_item')">
                                            <v-icon :color="buttonStatus(news_item.me_dislike)"
                                                size="12">mdi-thumb-down</v-icon> {{ news_item.dislikes }}
                                        </span>
                                        <span v-else class="caption font-weight-bold grey--text pl-1 pr-2">
                                            <v-icon color="grey" size="12">mdi-thumb-down</v-icon> {{ news_item.dislikes
                                            }}
                                        </span>
                                        <span v-if="canAccess"
                                            class="caption font-weight-bold px-0 mt-1 pb-0 pt-0 info--text source-link">
                                            {{ news_item.news_item_data.link }}
                                        </span>
                                    </v-col>

                                    <!--TOOLBAR-->
                                    <v-col cols="1">
                                        <v-row v-if="!multiSelectActive && !analyze_selector"
                                            :style="UI.STYLE.card_toolbar">
                                            <v-col v-bind="UI.CARD.COL.TOOLS"
                                                :style="UI.STYLE.card_toolbar_strip_bottom">
                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('ungroup')"
                                                    data-btn="ungroup" :title="$t('assess.tooltip.ungroup_item')">
                                                    <v-icon color="primary">mdi-ungroup</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canAccess" icon @click.stop="cardItemToolbar('link')"
                                                    data-btn="link" :title="$t('assess.tooltip.open_source')">
                                                    <a class="alink" :href="news_item.news_item_data.link"
                                                        target="_blank" rel="noreferer">
                                                        <v-icon color="primary">mdi-open-in-app</v-icon>
                                                    </a>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('read')"
                                                    data-btn="read" :title="$t('assess.tooltip.read_item')">
                                                    <v-icon :color="buttonStatus(news_item.read)">mdi-eye</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canModify" icon @click.stop="cardItemToolbar('important')"
                                                    data-btn="important" :title="$t('assess.tooltip.important_item')">
                                                    <v-icon :color="buttonStatus(news_item.important)">mdi-star</v-icon>
                                                </v-btn>

                                                <v-btn v-if="canDelete" icon @click.stop="showMsgBox" data-btn="delete"
                                                    :title="$t('assess.tooltip.delete_item')">
                                                    <v-icon color="primary">mdi-delete</v-icon>
                                                </v-btn>

                                            </v-col>
                                        </v-row>
                                    </v-col>
                                </v-row>
                            </v-row>
                        </v-layout>
                    </v-card>
                </v-hover>
            </v-col>
        </v-row>
        <v-row>
            <MessageBox v-model="msgbox_visible" @yes="handleMsgBox" @cancel="msgbox_visible = false"
                :title="$t('common.messagebox.delete')" :message="news_item.news_item_data.title" :alert=true>
            </MessageBox>
        </v-row>
    </v-container>
</template>

<script>
import { groupAction, voteNewsItem } from "@/api/assess";
import { readNewsItem } from "@/api/assess";
import { importantNewsItem } from "@/api/assess";
import { deleteNewsItem } from "@/api/assess";
import AuthMixin from "@/services/auth/auth_mixin";
import Permissions from "@/services/auth/permissions";
import MessageBox from "@/components/common/MessageBox.vue";
import AssessMixin from "@/components/assess/AssessMixin";
import CardMixin from "@/components/assess/CardMixin";

export default {
    name: "CardAssessItem",
    components: { MessageBox },
    props: {
        news_item: Object,
        analyze_selector: Boolean,
        compact_mode: Boolean,
        word_list_regex: String
    },
    mixins: [AuthMixin, AssessMixin, CardMixin],
    data: () => ({}),
    computed: {
        canAccess() {
            return this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true
        },

        canModify() {
            return this.checkPermission(Permissions.ASSESS_UPDATE) && this.news_item.modify === true
        },

        canDelete() {
            return this.checkPermission(Permissions.ASSESS_DELETE) && this.news_item.modify === true
        },

        canCreateReport() {
            return this.checkPermission(Permissions.ANALYZE_CREATE)
        },
    },
    methods: {
        itemClicked(data) {
            if (this.checkPermission(Permissions.ASSESS_ACCESS) && this.news_item.access === true) {
                this.$emit('show-item-detail', data);
                this.stateChange();
            }
        },
        selectionChanged() {
            if (this.selected === true) {
                this.$store.dispatch("select", { 'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item })
            } else {
                this.$store.dispatch("deselect", { 'type': 'ITEM', 'id': this.news_item.id, 'item': this.news_item })
            }
        },
        stateChange() {
            this.$root.$emit('change-state', 'SHOW_ITEM');
            this.$root.$emit('check-focus', this.$el.dataset.id);
            this.$root.$emit('update-pos', parseInt(this.$el.dataset.id));
        },
        cardItemToolbar(action) {
            switch (action) {
                case "like":
                    voteNewsItem(this.getGroupId(), this.news_item.id, 1).then(() => {
                    });
                    break;

                case "unlike":
                    voteNewsItem(this.getGroupId(), this.news_item.id, -1).then(() => {
                    });
                    break;

                case "link":
                    break;

                case "important":
                    importantNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                    });
                    break;

                case "read":
                    readNewsItem(this.getGroupId(), this.news_item.id).then(() => {
                    });
                    break;

                case "delete":
                    deleteNewsItem(this.getGroupId(), this.news_item.id).then(() => {
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
                    // Emit event to parent to close the expanded aggregate view
                    this.$parent.opened = false;
                    groupAction({
                        'group': this.getGroupId(),
                        'action': 'UNGROUP',
                        'items': [{ 'type': 'ITEM', 'id': this.news_item.id }]
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
                    this.itemClicked(this.news_item);
                    break;
            }
        },
    }
}
</script>
<style scoped>
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
<style>
.v-dialog--fullscreen {
    position: fixed !important;
    top: 0;
}
</style>
