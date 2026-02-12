<template>
    <v-dialog v-model="visible" max-width="900px" @click:outside="close">
        <v-card>
            <v-toolbar dark color="primary" flat>
                <v-toolbar-title>
                    {{$t('assess.reports_dialog.title') }}
                </v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn icon dark @click="close">
                    <v-icon>mdi-close</v-icon>
                </v-btn>
            </v-toolbar>

            <v-card-text class="pa-4">
                <div v-if="loading" class="text-center pa-4">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                </div>

                <div v-else-if="error" class="text-center pa-4">
                    <v-icon color="error" large>mdi-alert-circle</v-icon>
                    <p class="mt-2">{{ error }}</p>
                </div>

                <div v-else-if="reports.length === 0" class="text-center pa-4">
                    <v-icon large>mdi-information-outline</v-icon>
                    <p class="mt-2">{{ $t('assess.reports_dialog.no_reports') }}</p>
                </div>

                <div v-else>
                    <CardAnalyze
                        v-for="report in reports"
                        :key="report.id"
                        :card="report"
                        :show_remove_action="true"
                        :preselected="false"
                        :remove_tooltip="'assess.tooltip.remove_from_report'"
                        @show-report-item-detail="openReportItemDialog"
                        @remove-report-item-from-selector="removeAggregateFromReport"
                    />
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script>
    import { getReportItemsByAggregate, deleteReportItem, updateReportItem } from "@/api/analyze";
    import CardAnalyze from "@/components/analyze/CardAnalyze";

    export default {
        name: "ReportsListDialog",
        components: {
            CardAnalyze
        },
        data: () => ({
            visible: false,
            loading: false,
            error: null,
            reports: [],
            currentCard: null
        }),
        methods: {
            open(card) {
                this.currentCard = card;

                // If only one report, open the report item dialog directly
                if (card.in_reports_count === 1) {
                    getReportItemsByAggregate(card.id)
                        .then((response) => {
                            const reportItems = response.data.data || response.data;

                            if (reportItems && reportItems.length === 1) {
                                this.enrichReportItems([reportItems[0]]);
                                this.openReportItemDialog(reportItems[0]);
                            } else {
                                // Fallback to showing dialog if count was wrong
                                this.showDialog(card);
                            }
                        })
                        .catch((error) => {
                            console.error('Error fetching report:', error);
                            this.showDialog(card);
                        });
                } else {
                    this.showDialog(card);
                }
            },

            showDialog(card) {
                this.visible = true;
                this.loading = true;
                this.error = null;
                this.reports = [];

                getReportItemsByAggregate(card.id)
                    .then((response) => {
                        const reportItems = response.data.data || response.data;
                        this.enrichReportItems(reportItems);
                        this.reports = reportItems;
                        this.loading = false;
                    })
                    .catch((error) => {
                        console.error('Error fetching reports:', error);
                        this.error = this.$t('assess.reports_dialog.error_loading');
                        this.loading = false;
                    });
            },

            enrichReportItems(items) {
                // Ensure report types are loaded
                if (!this.$store.getters.getReportItemTypes.items ||
                    Object.keys(this.$store.getters.getReportItemTypes.items).length === 0) {
                    // Load report types first, then enrich items
                    this.$store.dispatch('getAllReportItemTypes', { search: '' }).then(() => {
                        this.addReportTypeNames(items);
                    });
                } else {
                    this.addReportTypeNames(items);
                }
            },

            addReportTypeNames(items) {
                // Add report_type_name to each report item
                const reportTypes = Object.values(this.$store.getters.getReportItemTypes.items);
                for (let i = 0; i < items.length; i++) {
                    const reportType = reportTypes.find(x => x.id == items[i].report_item_type_id);
                    if (reportType) {
                        items[i].report_type_name = reportType.title;
                    } else {
                        items[i].report_type_name = this.$t('card_item.title');
                    }
                }
            },

            close() {
                this.visible = false;
                this.reports = [];
                this.currentCard = null;
                this.error = null;
            },

            openReportItemDialog(report) {
                // Emit event to open the report item in the NewReportItem dialog
                this.$root.$emit('show-report-item', report);
                // Close this dialog after emitting the event
                this.close();
            },

            removeAggregateFromReport(report) {
                // Remove the aggregate from this specific report item
                const data = {
                    delete: true,
                    aggregate_id: this.currentCard.id
                };

                updateReportItem(report.id, data).then(() => {
                    // Remove the report from the list since the aggregate was removed
                    this.reports = this.reports.filter(r => r.id !== report.id);

                    // If no reports left, close the dialog
                    if (this.reports.length === 0) {
                        this.close();
                    }

                    this.$root.$emit('notification', {
                        type: 'success',
                        loc: 'report_item.removed_from_report'
                    });

                    // Refresh the news items list to update the in_reports_count
                    this.$root.$emit('news-items-updated');
                }).catch(() => {
                    this.$root.$emit('notification', {
                        type: 'error',
                        loc: 'report_item.removed_error'
                    });
                });
            },

            handleDeleteReportItem(item) {
                deleteReportItem(item).then(() => {
                    // Remove the deleted item from the reports array
                    this.reports = this.reports.filter(report => report.id !== item.id);

                    // Update the in_reports_count on the original card
                    if (this.currentCard && this.currentCard.in_reports_count > 0) {
                        this.currentCard.in_reports_count--;
                    }

                    // If no reports left, close the dialog
                    if (this.reports.length === 0) {
                        this.close();
                    }

                    this.$root.$emit('notification', {
                        type: 'success',
                        loc: 'report_item.removed'
                    });
                }).catch(() => {
                    this.$root.$emit('notification', {
                        type: 'error',
                        loc: 'report_item.removed_error'
                    });
                });
            }
        },

        mounted() {
            this.$root.$on('delete-report-item', this.handleDeleteReportItem);
        },

        beforeDestroy() {
            this.$root.$off('delete-report-item', this.handleDeleteReportItem);
        }
    }
</script>
