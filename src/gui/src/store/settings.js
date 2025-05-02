import { getProfile, updateProfile, getHotkeys, updateHotkeys } from "@/api/user";

const state = {
    hotkeys: [],
    spellcheck: true,
    dark_theme: false,
    language: "",
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

    getUserHotkeys(context) {
        return getHotkeys()
            .then(response => {
                context.commit('setUserHotkeys', response.data);
            })
    },

    saveUserHotkeys(context, data) {
        return updateHotkeys(data)
            .then(response => {
                context.commit('setUserHotkeys', response.data);
            })
    },

    resetHotkeys(context) {
        context.commit('resetHotkeys');
    }

};

const mutations = {

    setUserProfile(state, profile) {
        state.spellcheck = profile.spellcheck
        state.dark_theme = profile.dark_theme
        state.language = profile.language
        state.word_lists = profile.word_lists
    },

    setUserHotkeys(state, hotkeys) {
        mutations.resetHotkeys(state);

        for (let i = 0; i < state.hotkeys.length; i++) {
            for (let j = 0; j < hotkeys.length; j++) {
                if (state.hotkeys[i].alias === hotkeys[j].alias) {
                    state.hotkeys[i].key = hotkeys[j].key
                    break;
                }
            }
        }
    },

    resetHotkeys(state) {
        // we can't process .code, .keyCode property because they can be same up to 4 different .key values. Example: rR = KeyR,82  /? = Slash,191
        state.hotkeys = [
            // assess: new item navigation
            { key: 'ArrowUp', alias: 'collection_up_1', icon: 'mdi-arrow-up' },
            { key: 'k', alias: 'collection_up_2', icon: 'mdi-arrow-up' },
            { key: 'ArrowDown', alias: 'collection_down_1', icon: 'mdi-arrow-down' },
            { key: 'j', alias: 'collection_down_2', icon: 'mdi-arrow-down' },
            { key: 'Enter', alias: 'show_item_1', icon: 'mdi-text-box-outline' },
            { key: 'ArrowRight', alias: 'show_item_2', icon: 'mdi-text-box-outline' },
            { key: 'l', alias: 'show_item_3', icon: 'mdi-text-box-outline' },
            { key: 'Escape', alias: 'close_item_1', icon: 'mdi-close-box-outline' },
            { key: 'ArrowLeft', alias: 'close_item_2', icon: 'mdi-close-box-outline' },
            { key: 'h', alias: 'close_item_3', icon: 'mdi-close-box-outline' },
            { key: 'Home', alias: 'home', icon: 'mdi-arrow-collapse-up' },
            { key: 'End', alias: 'end', icon: 'mdi-arrow-collapse-down' },
            // assess: OSINT source group navigation
            { key: 'K', alias: 'source_group_up', icon: 'mdi-arrow-up-circle-outline' },
            { key: 'J', alias: 'source_group_down', icon: 'mdi-arrow-down-circle-outline' },
            // assess: news item actions
            { key: 'r', alias: 'read_item', icon: 'mdi-eye-outline' },
            { key: 'i', alias: 'important_item', icon: 'mdi-star-outline' },
            { key: 'u', alias: 'like_item', icon: 'mdi-thumb-up-outline' },
            { key: 'U', alias: 'unlike_item', icon: 'mdi-thumb-down-outline' },
            { key: 'Delete', alias: 'delete_item', icon: 'mdi-delete-outline' },
            { key: 's', alias: 'selection', icon: 'mdi-checkbox-multiple-marked-outline' },
            { key: 'g', alias: 'group', icon: 'mdi-group' },
            { key: 'G', alias: 'ungroup', icon: 'mdi-ungroup' },
            { key: 'n', alias: 'new_product', icon: 'mdi-file-outline' },
            { key: 'a', alias: 'aggregate_open', icon: 'mdi-google-circles-extended' },
            { key: 'o', alias: 'open_item_source', icon: 'mdi-open-in-app' },
            { key: '/', alias: 'open_search', icon: 'mdi-card-search-outline' },
            { key: 'R', alias: 'reload', icon: 'mdi-reload' },
            // switch views
            { key: 'v', alias: 'enter_view_mode', icon: 'mdi-view-headline' },
            { key: 'd', alias: 'dashboard_view', icon: 'mdi-view-dashboard-variant-outline' },
            { key: 'z', alias: 'analyze_view', icon: 'mdi-google-circles-communities' },
            { key: 'p', alias: 'publish_view', icon: 'mdi mdi-publish' },
            { key: 'm', alias: 'my_assets_view', icon: 'mdi-file-multiple-outline' },
            { key: 'c', alias: 'configuration_view', icon: 'mdi-ballot-outline' },
            // assess: filter actions
            { key: 'f', alias: 'enter_filter_mode', icon: 'mdi-filter-outline' },
        ];
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
    },

    getProfileLanguage(state) {
        let lng = state.language;
        if (!lng) {
            lng = navigator.language.split('-')[0];
        }
        if (!lng && typeof (process.env.VUE_APP_TARANIS_NG_LOCALE) !== "undefined") {
            lng = process.env.VUE_APP_TARANIS_NG_LOCALE;
        }
        if (!lng) {
            let bash_locale = "$VUE_APP_TARANIS_NG_LOCALE";
            lng = bash_locale;
        }
        if (!lng) {
            lng = "en";
        }
        return lng;
    }
};

export const settings = {
    state,
    actions,
    mutations,
    getters
}
