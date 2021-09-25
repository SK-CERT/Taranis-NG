import {getAllPublishersNodes} from "@/api/publishers";
import {getAllPublisherPresets} from "@/api/publishers";
import {getAllUserPublishersPresets} from "@/api/user";

const state = {
    publishers_nodes: {total_count: 0, items: []},
    publisher_presets: {total_count: 0, items: []}
};

const actions = {

    getAllPublishersNodes(context, data) {

        return getAllPublishersNodes(data)
            .then(response => {
                context.commit('setPublishersNodes', response.data);
            })
    },

    getAllPublisherPresets(context, data) {

        return getAllPublisherPresets(data)
            .then(response => {
                context.commit('setPublisherPresets', response.data);
            })
    },

    getAllUserPublishersPresets(context, data) {

        return getAllUserPublishersPresets(data)
            .then(response => {
                context.commit('setPublisherPresets', response.data);
            })
    }
};

const mutations = {

    setPublishersNodes(state, new_publishers_nodes) {
        state.publishers_nodes = new_publishers_nodes
    },

    setPublisherPresets(state, new_publisher_presets) {
        state.publisher_presets = new_publisher_presets
    }
};

const getters = {

    getPublishersNodes(state) {
        return state.publishers_nodes
    },

    getPublisherPresets(state) {
        return state.publisher_presets
    }
};

export const publishers = {
    state,
    actions,
    mutations,
    getters
};