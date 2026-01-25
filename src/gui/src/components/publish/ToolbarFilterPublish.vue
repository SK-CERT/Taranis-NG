<template>
    <v-container v-bind="UI.TOOLBAR.CONTAINER" :style="UI.STYLE.shadow">
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.LEFT">
                <div :class="UI.CLASS.toolbar_filter_title">{{$t( title )}}</div>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.MIDDLE">
                <v-text-field v-bind="UI.ELEMENT.SEARCH" v-model="filter.search"
                              :placeholder="$t('toolbar_filter.search')"
                              v-on:keyup="filterSearch" />
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
                        <div class="px-2" :title="$t('publish.tooltip.range.' + day.filter)">{{$t(day.title)}}</div>
                    </v-chip>
                </v-chip-group>

                <v-icon v-bind="UI.TOOLBAR.ICON.CHIPS_SEPARATOR">{{ UI.ICON.SEPARATOR }}</v-icon>

                <!-- FAVORITES -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.FAVORITES">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterCompleted">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('publish.tooltip.filter_completed')">{{ UI.ICON.COMPLETED }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterIncompleted">
                        <v-icon v-bind="UI.TOOLBAR.ICON.FAVORITES_CHIP" :title="$t('publish.tooltip.filter_incomplete')">{{ UI.ICON.INCOMPLETED }}</v-icon>
                    </v-chip>
                </v-chip-group>

                <!-- SORT -->
                <v-chip-group v-bind="UI.TOOLBAR.GROUP.SORT">
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_DESC')" :title="$t('publish.tooltip.sort.date.descending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.DESC }}</v-icon>
                    </v-chip>
                    <v-chip v-bind="UI.TOOLBAR.CHIP.GROUP" @click="filterSort('DATE_ASC')" :title="$t('publish.tooltip.sort.date.ascending')">
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_A">{{ UI.ICON.CLOCK }}</v-icon>
                        <v-icon v-bind="UI.TOOLBAR.ICON.SORT_CHIP_B">{{ UI.ICON.ASC }}</v-icon>
                    </v-chip>
                </v-chip-group>
            </v-col>
        </v-row>
        <v-divider></v-divider>
        <v-row v-bind="UI.TOOLBAR.ROW">
            <v-col v-bind="UI.TOOLBAR.COL.INFO">
                <span>{{$t(total_count_title)}}<strong>{{totalCount}}</strong></span>
            </v-col>
            <v-col v-bind="UI.TOOLBAR.COL.RIGHT"></v-col>
        </v-row>
    </v-container>
</template>

<script>
    import AuthMixin from "../../services/auth/auth_mixin";

    export default {
        name: "ToolbarFilterPublish",
        props: {
            title: String,
            dialog: String,
            total_count_title: String
        },
        computed: {
            totalCount() {
                return this.$store.getters.getProducts.total_count
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
            filter: {
                search: "",
                range: "ALL",
                completed: false,
                incompleted: false,
                sort: "DATE_DESC"
            },
            timeout: null
        }),
        mixins: [AuthMixin],
        methods: {
            filterCompleted() {
                this.filter.completed = !this.filter.completed;
                this.filter.incompleted = false;
                this.$root.$emit('update-products-filter', this.filter);
            },

            filterIncompleted() {
                this.filter.incompleted = !this.filter.incompleted;
                this.filter.completed = false;
                this.$root.$emit('update-products-filter', this.filter);
            },

            filterSort(sort) {
                this.filter.sort = sort;
                this.$root.$emit('update-products-filter', this.filter);
            },

            filterRange(range) {
                this.filter.range = range;
                this.$root.$emit('update-products-filter', this.filter);
            },

            filterSearch: function () {
                clearTimeout(this.timeout);

                let self = this;
                this.timeout = setTimeout(function () {
                    self.$root.$emit('update-products-filter', self.filter);
                }, 800);
            },

            remove(item) {
                this.chips.splice(this.chips.indexOf(item), 1);
                this.chips = [...this.chips]
            },
            cancel() {
            },
            add() {
            }

        }
    }
</script>
