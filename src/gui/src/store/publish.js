import {getAllProducts} from "@/api/publish";

const state = {
    products: {total_count: 0, items: []}
};

const actions = {

    getAllProducts(context, data) {

        return getAllProducts(data)
            .then(response => {
                context.commit('setProducts', response.data);
            })
    }
};

const mutations = {

    setProducts(state, new_product) {
       state.products = new_product
    }
};

const getters = {

    getProducts(state) {
        return state.products
    }
};

export const publish = {
    state,
    actions,
    mutations,
    getters
};