import {getAllCollectorsNodes} from "@/api/collectors";
import {getAllOSINTSources} from "@/api/collectors";
import {getAllOSINTSourceGroups} from "@/api/collectors";
import {getManualOSINTSources} from "@/api/collectors";
import {getAllOSINTSourceGroupsAssess} from "@/api/assess";

const state = {
    collectors_nodes: {total_count: 0, items: []},
    osint_sources: {total_count: 0, items: []},
    osint_source_groups: {total_count: 0, items: []},
    manual_osint_sources: [],
};

const actions = {

    getAllCollectorsNodes(context, data) {

        return getAllCollectorsNodes(data)
            .then(response => {
                context.commit('setCollectorsNodes', response.data);
            })
    },

    getAllOSINTSources(context, data) {

        return getAllOSINTSources(data)
            .then(response => {
                context.commit('setOSINTSources', response.data);
            })
    },

    getAllOSINTSourceGroups(context, data) {

        return getAllOSINTSourceGroups(data)
            .then(response => {
                context.commit('setOSINTSourceGroups', response.data);
            })
    },

    getAllOSINTSourceGroupsAssess(context, data) {

        return getAllOSINTSourceGroupsAssess(data)
            .then(response => {
                context.commit('setOSINTSourceGroups', response.data);
            })
    },

    getManualOSINTSources(context) {

        return getManualOSINTSources()
            .then(response => {
                context.commit('setManualOSINTSources', response.data);
            })
    },
};

const mutations = {

    setCollectorsNodes(state, new_collectors_nodes) {
        state.collectors_nodes = new_collectors_nodes
    },

    setOSINTSources(state, new_osint_sources) {
        state.osint_sources = new_osint_sources
    },

    setOSINTSourceGroups(state, new_osint_source_groups) {
        state.osint_source_groups = new_osint_source_groups
    },

    setManualOSINTSources(state, new_manual_osint_sources) {
        state.manual_osint_sources = new_manual_osint_sources
    }
};

const getters = {

    getCollectorsNodes(state) {
        return state.collectors_nodes
    },

    getOSINTSources(state) {
        return state.osint_sources
    },

    getOSINTSourceGroups(state) {
        return state.osint_source_groups
    },

    getManualOSINTSources(state) {
        return state.manual_osint_sources
    }
};

export const collectors = {
    state,
    actions,
    mutations,
    getters
};