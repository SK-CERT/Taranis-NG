import {getAllAttributes} from "@/api/config";
import {getAllReportItemTypes} from "@/api/config";
import {getAllProductTypes} from "@/api/config";
import {getAllPermissions} from "@/api/config";
import {getAllRoles} from "@/api/config";
import {getAllOrganizations} from "@/api/config";
import {getAllUsers} from "@/api/config";
import {getAllWordLists} from "@/api/config";
import {getAllExternalPermissions} from "@/api/config";
import {getAllExternalUsers} from "@/api/config";
import {getAllACLEntries} from "@/api/config";
import {getAllUserWordLists} from "@/api/user";
import {getAllUserProductTypes} from "@/api/user";


const state = {
    attributes: {total_count: 0, items: []},
    report_item_types_config: {total_count: 0, items: []},
    product_types: {total_count: 0, items: []},
    all_permissions: {total_count: 0, items: []},
    roles: {total_count: 0, items: []},
    acls: {total_count: 0, items: []},
    organizations: {total_count: 0, items: []},
    users: {total_count: 0, items: []},
    word_lists: {total_count: 0, items: []}
};

const actions = {

    getAllAttributes(context, data) {

        return getAllAttributes(data)
            .then(response => {
                context.commit('setAttributes', response.data);
            })
    },

    getAllReportItemTypesConfig(context, data) {

        return getAllReportItemTypes(data)
            .then(response => {
                context.commit('setReportItemTypesConfig', response.data);
            })
    },

    getAllProductTypes(context, data) {

        return getAllProductTypes(data)
            .then(response => {
                context.commit('setProductTypes', response.data);
            })
    },

    getAllUserProductTypes(context, data) {

        return getAllUserProductTypes(data)
            .then(response => {
                context.commit('setProductTypes', response.data);
            })
    },

    getAllPermissions(context, data) {

        return getAllPermissions(data)
            .then(response => {
                context.commit('setPermissions', response.data);
            })
    },

    getAllExternalPermissions(context, data) {

        return getAllExternalPermissions(data)
            .then(response => {
                context.commit('setPermissions', response.data);
            })
    },

    getAllRoles(context, data) {

        return getAllRoles(data)
            .then(response => {
                context.commit('setRoles', response.data);
            })
    },

    getAllACLEntries(context, data) {

        return getAllACLEntries(data)
            .then(response => {
                context.commit('setACLEntries', response.data);
            })
    },

    getAllOrganizations(context, data) {

        return getAllOrganizations(data)
            .then(response => {
                context.commit('setOrganizations', response.data);
            })
    },

    getAllUsers(context, data) {

        return getAllUsers(data)
            .then(response => {
                context.commit('setUsers', response.data);
            })
    },

    getAllExternalUsers(context, data) {

        return getAllExternalUsers(data)
            .then(response => {
                context.commit('setUsers', response.data);
            })
    },

    getAllWordLists(context, data) {

        return getAllWordLists(data)
            .then(response => {
                context.commit('setWordLists', response.data);
            })
    },

    getAllUserWordLists(context, data) {

        return getAllUserWordLists(data)
            .then(response => {
                context.commit('setWordLists', response.data);
            })
    },
};

const mutations = {

    setAttributes(state, new_attributes) {
        state.attributes = new_attributes
    },

    setReportItemTypesConfig(state, new_report_item_types_config) {
        state.report_item_types_config = new_report_item_types_config
    },

    setProductTypes(state, new_product_types) {
        state.product_types = new_product_types
    },

    setPermissions(state, new_permissions) {
        state.all_permissions = new_permissions
    },

    setRoles(state, new_roles) {
        state.roles = new_roles
    },

    setACLEntries(state, new_acls) {
        state.acls = new_acls
    },

    setOrganizations(state, new_organizations) {
        state.organizations = new_organizations
    },

    setUsers(state, new_users) {
        state.users = new_users
    },

    setWordLists(state, new_word_lists) {
        state.word_lists = new_word_lists
    },
};

const getters = {

    getAttributes(state) {
        return state.attributes
    },

    getReportItemTypesConfig(state) {
        return state.report_item_types_config
    },

    getProductTypes(state) {
        return state.product_types
    },

    getAllPermissions(state) {
        return state.all_permissions
    },

    getRoles(state) {
        return state.roles
    },

    getACLEntries(state) {
        return state.acls
    },

    getOrganizations(state) {
        return state.organizations
    },

    getUsers(state) {
        return state.users
    },

    getWordLists(state) {
        return state.word_lists
    },
};

export const config = {
    state,
    actions,
    mutations,
    getters
};