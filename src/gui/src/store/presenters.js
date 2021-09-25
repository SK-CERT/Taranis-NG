import {getAllPresentersNodes} from "@/api/presenters";

const state = {
    presenters_nodes: {total_count: 0, items: []},
};

const actions = {

    getAllPresentersNodes(context, data) {

        return getAllPresentersNodes(data)
            .then(response => {
                context.commit('setPresentersNodes', response.data);
            })
    }
};

const mutations = {

    setPresentersNodes(state, new_presenters_nodes) {
        state.presenters_nodes = new_presenters_nodes
    }
};

const getters = {

    getPresentersNodes(state) {
        return state.presenters_nodes
    }
};

export const presenters = {
    state,
    actions,
    mutations,
    getters
};