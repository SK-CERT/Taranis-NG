<template>
    <v-container v-bind="UI.TOOLBAR.CONTAINER" :style="UI.STYLE.shadow">
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                <div :class="UI.CLASS.toolbar_filter_title">{{$t( title )}}</div>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="filter.search"
                              :placeholder="$t('toolbar_filter.search')"
                              v-on:keyup="filterSearch"
                              id="search" />
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <slot name="addbutton"></slot>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col class="py-0">
                <!-- DAY-S -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.DAYS">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP"
                            v-for="day in days" :key="day.filter" @click="filterRange(day.filter)">
                        <div class="px-2" :title="$t('assess.tooltip.range.' + day.filter)">{{$t(day.title)}}</div>
                    </v-chip>
                </v-chip-group>

                <v-icon v-bind="UI.TOOLBAR.ICON.CHIPS_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>

                <!-- FILTER -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.FILTER_MULTI" v-model="activeFilters">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterRead" id="button_filter_read" value="read">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP" :title="readFilterTooltip">{{ readFilterIcon }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterImportant" id="button_filter_important" value="important">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP" :title="importantFilterTooltip">{{ importantFilterIcon }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterRelevant" id="button_filter_relevant" value="relevant">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP" :title="relevantFilterTooltip">{{ relevantFilterIcon }}</v-icon>
                    </v-chip>
                </v-chip-group>

                <!-- SORT -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.SORT">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_DESC')" :title="$t('assess.tooltip.sort.date.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_ASC')" :title="$t('assess.tooltip.sort.date.ascending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>

                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('RELEVANCE_DESC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_A">{{ UI.ICON.LIKE }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('RELEVANCE_ASC')" :title="$t('assess.tooltip.sort.relevance.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_A">{{ UI.ICON.UNLIKE }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>
                </v-chip-group>
            </v-col>
        </v-row>
        <v-divider v-if="!analyze_selector"></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW" v-if="!analyze_selector">
            <v-col v-bind="UI.TOOLBAR.COL.SELECTOR">
                <ToolbarGroupAssess ref="toolbarGroupAssess" />
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>
                <span class="total-count-text mx-5" v-if="multiSelectActive">{{$t(selected_count_title)}}<strong>{{selectedCount}}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT">
                <div class="d-flex align-center justify-end">
                    <!-- Review Toggle -->
                    <v-btn x-small text @click="hideReview" class="ma-0 pa-0 mr-1" :title="$t('assess.tooltip.hide_review')">
                        <v-icon v-if="review_toggle" center color="black">mdi-text-box-remove-outline</v-icon>
                        <v-icon v-else center color="amber darken-2">mdi-text-box-outline</v-icon>
                    </v-btn>
                    <!-- Source link Toggle -->
                    <v-btn x-small text @click="hideSourceLink" class="ma-0 pa-0 mr-1" :title="$t('assess.tooltip.hide_source_link')">
                        <v-icon v-if="source_link_toggle" center color="black">mdi-web-remove</v-icon>
                        <v-icon v-else center color="amber darken-2">mdi-web</v-icon>
                    </v-btn>
                    <!-- Wordlist Togle -->
                    <v-btn x-small text @click="hideWordlist" class="ma-0 pa-0" :title="$t('assess.tooltip.highlight_wordlist')">
                        <v-icon v-if="word_list_toggle" center color="black">mdi-alphabetical-variant-off</v-icon>
                        <v-icon v-else center color="amber darken-2">mdi-alphabetical-variant</v-icon>
                    </v-btn>
                </div>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";
    import ToolbarGroupAssess from "@/components/assess/ToolbarGroupAssess";
    import { getLocalStorageBoolean } from "@/services/settings";

    export default {
        name: "ToolbarFilterAssess",
        components: {
            ToolbarGroupAssess
        },
        props: {
            title: String,
            dialog: String,
            analyze_selector: Boolean,
            total_count_title: String,
            selected_count_title: String,
        },
        computed: {
            totalCount() {
                return this.data_count
            },

            selectedCount() {
                return this.$store.getters.getSelection.length;
            },

            multiSelectActive() {
                return this.$store.getters.getMultiSelect;
            },

            // this exists only because we want initialise selection on start
            activeFilters: {
                get() {
                    const result = []
                    if (this.filter.read === true || this.filter.read === 'unread') result.push('read')
                    if (this.filter.important === true || this.filter.important === 'unimportant') result.push('important')
                    if (this.filter.relevant === true || this.filter.relevant === 'irrelevant') result.push('relevant')
                    return result
                },
                set() {
                    // Chip-group requires a setter, but we handle clicks manually
                }
            },

            readFilterIcon() {
                if (this.filter.read === true) return this.UI.ICON.READ
                return this.UI.ICON.UNREAD
            },

            readFilterTooltip() {
                if (this.filter.read === true) return this.$t('assess.tooltip.filter_read')
                return this.$t('assess.tooltip.filter_unread')
            },

            importantFilterIcon() {
                if (this.filter.important === true) return this.UI.ICON.IMPORTANT
                if (this.filter.important === 'unimportant') return this.UI.ICON.UNIMPORTANT
                return this.UI.ICON.IMPORTANT
            },

            importantFilterTooltip() {
                if (this.filter.important === true) return this.$t('assess.tooltip.filter_important')
                if (this.filter.important === 'unimportant') return this.$t('assess.tooltip.filter_unimportant')
                return this.$t('assess.tooltip.filter_important')
            },

            relevantFilterIcon() {
                if (this.filter.relevant === true) return this.UI.ICON.LIKE
                if (this.filter.relevant === 'irrelevant') return this.UI.ICON.UNLIKE
                return this.UI.ICON.LIKE
            },

            relevantFilterTooltip() {
                if (this.filter.relevant === true) return this.$t('assess.tooltip.filter_relevant')
                if (this.filter.relevant === 'irrelevant') return this.$t('assess.tooltip.filter_irrelevant')
                return this.$t('assess.tooltip.filter_relevant')
            }
        },
        data: () => ({
            status: [],
            days: [
                { title: 'toolbar_filter.all', icon: 'mdi-information-outline', type: 'info', filter: 'ALL' },
                { title: 'toolbar_filter.today', icon: 'mdi-calendar-today', type: 'info', filter: 'TODAY' },
                { title: 'toolbar_filter.this_week', icon: 'mdi-calendar-range', type: 'info', filter: 'WEEK' },
                { title: 'toolbar_filter.this_month', icon: 'mdi-calendar-month', type: 'info', filter: 'MONTH' },
                { title: 'toolbar_filter.last_7_days', icon: 'mdi-calendar-range', type: 'info', filter: 'LAST_7_DAYS' },
                { title: 'toolbar_filter.last_31_days', icon: 'mdi-calendar-month', type: 'info', filter: 'LAST_31_DAYS' }
            ],
            data_count: 0,
            filter: {
                search: "",
                range: "ALL",
                read: 'unread',
                important: false,
                relevant: false,
                sort: "DATE_DESC"
            },
            timeout: null,
            word_list_toggle: false,
            review_toggle: false,
            source_link_toggle: false,
        }),
        mixins: [AuthMixin],
        methods: {
            updateDataCount(count) {
                this.data_count = count
            },

            filterRead() {
                // Cycle through three states: false (off) -> true (read) -> 'unread' -> false
                if (this.filter.read === false) {
                    this.filter.read = true;
                } else if (this.filter.read === true) {
                    this.filter.read = 'unread';
                } else {
                    this.filter.read = false;
                }
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterImportant() {
                // Cycle through three states: false (off) -> true (important) -> 'unimportant' -> false
                if (this.filter.important === false) {
                    this.filter.important = true;
                } else if (this.filter.important === true) {
                    this.filter.important = 'unimportant';
                } else {
                    this.filter.important = false;
                }
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterRelevant() {
                // Cycle through three states: false (off) -> true (relevant/thumbs up) -> 'irrelevant' (thumbs down) -> false
                if (this.filter.relevant === false) {
                    this.filter.relevant = true;
                } else if (this.filter.relevant === true) {
                    this.filter.relevant = 'irrelevant';
                } else {
                    this.filter.relevant = false;
                }
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterSort(sort) {
                this.filter.sort = sort;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterRange(range) {
                this.filter.range = range;
                this.$emit('update-news-items-filter', this.filter);
                if (this.analyze_selector === false) {
                    this.$refs.toolbarGroupAssess.disableMultiSelect()
                }
            },

            filterSearch: function () {
                clearTimeout(this.timeout);

                let self = this;
                this.timeout = setTimeout(function () {
                    self.$emit('update-news-items-filter', self.filter)
                    if (self.analyze_selector === false) {
                        self.$refs.toolbarGroupAssess.disableMultiSelect()
                    }
                }, 300);
            },
            remove(item) {
                this.chips.splice(this.chips.indexOf(item), 1);
                this.chips = [...this.chips]
            },
            cancel() {
            },
            add() {
            },

            setHideStyle(settingsName, styleName, value, saveSetting) {
                if (value) {
                    document.getElementById("app").classList.add(styleName);
                } else {
                    document.getElementById("app").classList.remove(styleName);
                }
                if (saveSetting) {
                    localStorage.setItem(settingsName, value);
                }
            },

            hideReview() {
                this.review_toggle = !this.review_toggle;
                this.setHideStyle("review-hide", "hide-review", this.review_toggle, true);
            },

            hideSourceLink() {
                this.source_link_toggle = !this.source_link_toggle;
                this.setHideStyle("source-link-hide", "hide-source-link", this.source_link_toggle, true);
            },

            hideWordlist() {
                this.word_list_toggle = !this.word_list_toggle;
                this.setHideStyle("word-list-hide", "hide-wordlist", this.word_list_toggle, true);
            },

        },
        created() {
            this.review_toggle = getLocalStorageBoolean('review-hide', false);
            this.source_link_toggle = getLocalStorageBoolean('source-link-hide', false);
            this.word_list_toggle = getLocalStorageBoolean('word-list-hide', false);
        },
        mounted() {
            this.setHideStyle("review-hide", "hide-review", this.review_toggle, false);
            this.setHideStyle("source-link-hide", "hide-source-link", this.source_link_toggle, false);
            this.setHideStyle("word-list-hide", "hide-wordlist", this.word_list_toggle, false);
        }
    }
</script>
