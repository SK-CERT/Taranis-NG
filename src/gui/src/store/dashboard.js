import {getDashboardData} from "@/api/dashboard";

const state = {
    dashboard_data: {
        'total_news_items': 0,
        'total_products': 0,
        'total_report_items': 0,
        'report_item_states': {},
        'total_database_items': 0,
        'latest_collected': "",
        'tag_cloud': {}
    }
};

const actions = {

    getAllDashboardData(context) {

        return getDashboardData()
            .then(response => {
                if (response)
                    context.commit('setDashboardData', response.data);
            })
    }
};

const mutations = {

    setDashboardData(state, data) {
        state.dashboard_data = data
    }
};

const getters = {

    getDashboardData(state) {
        return state.dashboard_data;
    },

};

export const dashboard = {
    state,
    actions,
    mutations,
    getters
}
