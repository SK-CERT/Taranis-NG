import {getManualOSINTSources, getNewsItemsByGroup, getAllNewsItemsByGroup} from "@/api/assess";

const state = {
    newsitems: {total_count: 0, items: []},
    multi_select: false,
    selection: [],
    current_group_id: "",
    manual_osint_sources: [],
    filter: {},
};

const actions = {

    getNewsItemsByGroup(context, data) {

        return getNewsItemsByGroup(data.group_id, data.data)
            .then(response => {
                if (response)
                    context.commit('setNewsItems', response.data);
            })
    },

    multiSelect(context, data) {
        context.commit('setMultiSelect', data);
    },

    select(context, data) {
        context.commit('addSelection', data);
    },

    deselect(context, data) {
        context.commit('removeSelection', data);
    },

    changeCurrentGroup(context, data) {
        context.commit('setCurrentGroup', data);
    },

    getManualOSINTSources(context) {

        return getManualOSINTSources()
            .then(response => {
                context.commit('setManualOSINTSources', response.data);
            })
    },

    filter(context, data) {
        context.commit('setFilter', data);
    },

    selectAllItems(context, data) {
        // Fetch items in batches due to backend limit of 200 items per request
        const fetchBatch = (offset) => {
            const batchData = {
                group_id: data.group_id,
                data: {
                    filter: data.data.filter,
                    offset: offset,
                    limit: 200
                }
            };

            return getAllNewsItemsByGroup(batchData.group_id, batchData.data)
                .then(response => {
                    if (response && response.data && response.data.items) {
                        const items = response.data.items;
                        const totalCount = response.data.total_count;

                        // Add items to selection
                        items.forEach(item => {
                            context.commit('addSelection', {
                                'type': 'AGGREGATE',
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
        context.commit('clearSelection');
        return fetchBatch(0);
    },

    deselectAll(context) {
        context.commit('clearSelection');
    },
};

const mutations = {

    setNewsItems(state, news_items) {
        state.newsitems = news_items
    },

    setMultiSelect(state, enable) {
        state.multi_select = enable
        state.selection = []
    },

    addSelection(state, selected_item) {
        state.selection.push(selected_item)
    },

    removeSelection(state, selectedItem) {
        for (let i = 0; i < state.selection.length; i++) {
            if (state.selection[i].type === selectedItem.type && state.selection[i].id === selectedItem.id) {
                state.selection.splice(i, 1);
                break
            }
        }
    },

    setCurrentGroup(state, group_id) {
        state.current_group_id = group_id
    },

    setManualOSINTSources(state, new_manual_osint_sources) {
        state.manual_osint_sources = new_manual_osint_sources
    },

    setFilter(state, data) {
        state.filter = data
    },

    clearSelection(state) {
        state.selection = []
    },
};

const getters = {

    getNewsItems(state) {
        return state.newsitems
    },

    getMultiSelect(state) {
        return state.multi_select
    },

    getSelection(state) {
        return state.selection
    },

    getCurrentGroup(state) {
        return state.current_group_id
    },

    getManualOSINTSources(state) {
        return state.manual_osint_sources
    },

    getFilter(state) {
        return state.filter
    },
};

export const assess = {
    state,
    actions,
    mutations,
    getters
};
