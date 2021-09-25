import {getAllRemoteAccesses} from "@/api/remote";
import {getAllRemoteNodes} from "@/api/remote";

const state = {
    remote_access: {total_count: 0, items: []},
    remote_nodes: {total_count: 0, items: []},
};

const actions = {

    getAllRemoteAccesses(context, data) {

        return getAllRemoteAccesses(data)
            .then(response => {
                context.commit('setRemoteAccesses', response.data);
            })
    },

    getAllRemoteNodes(context, data) {

        return getAllRemoteNodes(data)
            .then(response => {
                context.commit('setRemoteNodes', response.data);
            })
    }
};

const mutations = {

    setRemoteAccesses(state, new_remote_access) {
        state.remote_access = new_remote_access
    },

    setRemoteNodes(state, new_remote_nodes) {
        state.remote_nodes = new_remote_nodes
    }
};

const getters = {

    getRemoteAccesses(state) {
        return state.remote_access
    },

    getRemoteNodes(state) {
        return state.remote_nodes
    }
};

export const remote = {
    state,
    actions,
    mutations,
    getters
};