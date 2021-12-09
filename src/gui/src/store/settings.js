import {getProfile} from "@/api/user";
import {updateProfile} from "@/api/user";

const state = {
    hotkeys: [
        // new item navigation
        {key_code: 38, key: 'ArrowUp', alias: 'collection_up', icon: 'mdi-arrow-up-bold-box-outline'},
        {key_code: 40, key: 'ArrowDown', alias: 'collection_down', icon: 'mdi-arrow-down-bold-box-outline'},
        {key_code: 37, key: 'ArrowLeft', alias: 'close_item', icon: 'mdi-close-circle-outline'},
        {key_code: 39, key: 'ArrowRight', alias: 'show_item', icon: 'mdi-text-box'},
        {character: 'k', alias: 'collection_up', icon: 'mdi-arrow-up-bold-box-outline'},
        {character: 'j', alias: 'collection_down', icon: 'mdi-arrow-down-bold-box-outline'},
        {key_code: 13, key: 'Enter', alias: 'show_item', icon: 'mdi-text-box'},
        {key_code: 27, key: 'Escape', alias: 'close_item', icon: 'mdi-close-circle-outline'},
        // news item actions
        {character: 'r', alias: 'read_item', icon: 'mdi-eye'},
        {character: 'i', alias: 'important_item', icon: 'mdi-star'},
        {character: 'l', alias: 'like_item', icon: 'mdi-thumb-up'},
        {character: 'd', alias: 'unlike_item', icon: 'mdi-thumb-down'},
        {key_code: 46, key: 'Delete', alias: 'delete_item', icon: 'mdi-delete'},
        {character: 's', alias: 'selection', icon: 'mdi-checkbox-multiple-marked-outline'},
        {character: 'g', alias: 'group', icon: 'mdi-group'},
        {character: 'u', alias: 'ungroup', icon: 'mdi-ungroup'},
        {character: 'n', alias: 'new_product', icon: 'mdi-file-outline'},
        {character: 'a', alias: 'aggregate_open', icon: 'mdi-arrow-right-drop-circle'}
    ],
    spellcheck: true,
    dark_theme: false,
    word_lists: []
};

const actions = {

    getUserProfile(context) {

        return getProfile()
            .then(response => {
                context.commit('setUserProfile', response.data);
            })
    },

    saveUserProfile(context, data) {

        return updateProfile(data)
            .then(response => {
                context.commit('setUserProfile', response.data);
            })
    },
};

const mutations = {

    setUserProfile(state, profile) {
        state.spellcheck = profile.spellcheck
        state.dark_theme = profile.dark_theme
        state.word_lists = profile.word_lists
        for (let i = 0; i < state.hotkeys.length; i++) {
            for (let j = 0; j < profile.hotkeys.length; j++) {
                if (state.hotkeys[i].alias === profile.hotkeys[j].alias) {
                    state.hotkeys[i].key = profile.hotkeys[j].key
                    state.hotkeys[i].key_code = profile.hotkeys[j].key_code
                }
            }
        }
    }
};

const getters = {

    getProfileSpellcheck(state) {
        return state.spellcheck;
    },

    getProfileDarkTheme(state) {
        return state.dark_theme;
    },

    getProfileHotkeys(state) {
        return state.hotkeys;
    },

    getProfileWordLists(state) {
        return state.word_lists;
    }
};

export const settings = {
    state,
    actions,
    mutations,
    getters
}