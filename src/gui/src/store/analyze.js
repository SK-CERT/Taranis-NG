import {getAllReportItems, getAllReportItemsUnpaginated} from "@/api/analyze";
import {getAllReportItemTypes} from "@/api/analyze";
import {getAllReportItemGroups} from "@/api/analyze";

const state = {
    report_items: {total_count: 0, items: []},
    report_item_types: {total_count: 0, items: []},
    multi_select_report: false,
    selection_report: [],
    report_item_groups: [],
    current_report_item_group_id: null
};

const actions = {

    getAllReportItemGroups(context, data) {

        return getAllReportItemGroups(data)
            .then(response => {
                context.commit('setReportItemGroups', response.data);
            })
    },

    getAllReportItems(context, data) {

        return getAllReportItems(data)
            .then(response => {
                if (response)
                    context.commit('setReportItems', response.data);
            })
    },

    getAllReportItemTypes(context, data) {

        return getAllReportItemTypes(data)
            .then(response => {
                context.commit('setReportItemTypes', response.data);
            })
    },

    multiSelectReport(context, data) {
        context.commit('setMultiSelectReport', data);
    },

    selectReport(context, data) {
        context.commit('addSelectionReport', data);
    },

    deselectReport(context, data) {
        context.commit('removeSelectionReport', data);
    },

    changeCurrentReportItemGroup(context, data) {
        context.commit('setCurrentReportItemGroup', data);
    },

    selectAllReportItems(context, data) {
        // Fetch items in batches due to backend limit of 200 items per request
        const fetchBatch = (offset) => {
            const batchData = {
                group: data.group,
                filter: data.filter,
                offset: offset,
                limit: 200
            };

            return getAllReportItemsUnpaginated(batchData)
                .then(response => {
                    if (response && response.data && response.data.items) {
                        const items = response.data.items;
                        const totalCount = response.data.total_count;

                        // Add items to selection
                        items.forEach(item => {
                            context.commit('addSelectionReport', {
                                'id': item.id,
                                'item': item
                            });
                        });

                        // Check if we need to fetch more
                        const nextOffset = offset + items.length;
                        if (nextOffset < totalCount) {
                            // Fetch next batch
                            return fetchBatch(nextOffset);
                        }

                        // Return total count when done
                        return totalCount;
                    }
                    return 0;
                });
        };

        // Clear existing selection and start fetching from offset 0
        context.commit('clearSelectionReport');
        return fetchBatch(0);
    },

    deselectAllReport(context) {
        context.commit('clearSelectionReport');
    },
};

const mutations = {

    setReportItemGroups(state, new_report_item_groups) {
        state.report_item_groups = new_report_item_groups
    },

    setCurrentReportItemGroup(state, new_current_report_item_group) {
        state.current_report_item_group_id = new_current_report_item_group
    },

    setReportItems(state, new_report_items) {
        state.report_items = new_report_items
    },

    setReportItemTypes(state, new_report_item_types) {
        state.report_item_types = new_report_item_types
    },

    setMultiSelectReport(state, enable) {
        state.multi_select_report = enable
        state.selection_report = []
    },

    addSelectionReport(state, selected_item) {
        state.selection_report.push(selected_item)
    },

    removeSelectionReport(state, selectedItem) {
        for (let i = 0; i < state.selection_report.length; i++) {
            if (state.selection_report[i].id === selectedItem.id) {
                state.selection_report.splice(i, 1);
                break
            }
        }
    },

    clearSelectionReport(state) {
        state.selection_report = []
    },
};

const getters = {

    getReportItemGroups(state) {
        return state.report_item_groups
    },

    getCurrentReportItemGroup(state) {
        return state.current_report_item_group_id
    },

    getReportItems(state) {
        return state.report_items
    },

    getReportItemTypes(state) {
        return state.report_item_types
    },

    getMultiSelectReport(state) {
        return state.multi_select_report
    },

    getSelectionReport(state) {
        return state.selection_report
    }
};

export const analyze = {
    state,
    actions,
    mutations,
    getters
};
