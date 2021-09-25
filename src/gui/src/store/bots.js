import {getAllBotPresets} from "@/api/bots";
import {getAllBotsNodes} from "@/api/bots";

const state = {
    bots_nodes: {total_count: 0, items: []},
    bot_presets: {total_count: 0, items: []}
};

const actions = {

    getAllBotsNodes(context, data) {

        return getAllBotsNodes(data)
            .then(response => {
                context.commit('setBotsNodes', response.data);
            })
    },

    getAllBotPresets(context, data) {

        return getAllBotPresets(data)
            .then(response => {
                context.commit('setBotPresets', response.data);
            })
    }
};

const mutations = {

    setBotsNodes(state, new_bots_nodes) {
        state.bots_nodes = new_bots_nodes
    },

    setBotPresets(state, new_bot_presets) {
        state.bot_presets = new_bot_presets
    }
};

const getters = {

    getBotsNodes(state) {
        return state.bots_nodes
    },

    getBotPresets(state) {
        return state.bot_presets
    }
};

export const bots = {
    state,
    actions,
    mutations,
    getters
};