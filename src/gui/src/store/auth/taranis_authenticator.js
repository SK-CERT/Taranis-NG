import { login as loginApi, logout as logoutApi, refresh } from "@/api/auth";
import ApiService from "@/services/api_service";

const state = {
    jwt: ''
};

const actions = {

    login(context, userData) {
        return loginApi(userData)
            .then(response => {
                context.commit('setJwtToken', response.data.access_token);
                context.dispatch('setUser', context.getters.getUserData);
            })
            .catch(() => {
                context.commit('clearJwtToken')
            })
    },

    logout(context) {
        logoutApi().then(() => {
            context.commit('clearJwtToken');
            window.location.reload();
        });
    },

    refresh(context) {

        return refresh()
            .then(response => {
                context.commit('setJwtToken', response.data.access_token);
                context.dispatch('setUser', context.getters.getUserData)
            })
            .catch(() => {
                context.commit('clearJwtToken')
            })
    },

    setToken(context, access_token) {

        context.commit('setJwtToken', access_token);
        context.dispatch('setUser', context.getters.getUserData);
    }
};

const mutations = {

    setJwtToken(state, access_token) {
        localStorage.ACCESS_TOKEN = access_token;
        ApiService.setHeader();
        state.jwt = access_token;
    },

    clearJwtToken(state) {
        localStorage.ACCESS_TOKEN = '';
        state.jwt = ''
    }
};

const getters = {

    getUserData(state) {
        const data = JSON.parse(atob(state.jwt.split('.')[1]));
        return data.user_claims
    },

    getSubjectName(state) {
        const data = JSON.parse(atob(state.jwt.split('.')[1]));
        return data.sub
    },

    getJWT() {
        return state.jwt
    }
};

export const taranis_authenticator = {
    state,
    actions,
    mutations,
    getters
};
