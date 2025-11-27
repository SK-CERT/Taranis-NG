<template>

    <v-container id="selector_publish">
        <CardProduct v-for="collection in collections" :card="collection" :key="collection.id"></CardProduct>
        <v-card v-intersect.quiet="infiniteScrolling"></v-card>
    </v-container>

</template>

<script>
    import CardProduct from "./CardProduct";

    export default {
        name: "ContentDataPublish",

        components: {
            CardProduct,
        },

        data: () => ({
            collections: [],
            data_loaded: false,
            filter: {
                search: "",
                range: "ALL",
                sort: "DATE_DESC"
            }
        }),

        methods: {
            infiniteScrolling(entries, observer, isIntersecting) {

                if (this.data_loaded && isIntersecting) {
                    this.updateData(true, false)
                }
            },

            updateData(append, reload_all) {
                this.data_loaded = false;

                if (append === false) {
                    this.collections = []
                }

                let offset = this.collections.length;
                let limit = 20;
                if (reload_all) {
                    offset = 0;
                    if (this.collections.length > limit) {
                        limit = this.collections.length;
                    }
                    this.collections = []
                }
                this.$store.dispatch("getAllProducts", { filter: this.filter, offset: offset, limit: limit })
                    .then(() => {
                        const product_types = Object.values(this.$store.getters.getProductTypes.items);
                        this.collections = this.collections.concat(this.$store.getters.getProducts.items);
                        for (let i = 0; i < this.collections.length; i++) {
                            let product_type = product_types.filter(x => x.id == this.collections[i].product_type_id);
                            if (product_type.length) {
                                this.collections[i].product_type_name = product_type[0].title;
                            } else {
                                this.collections[i].product_type_name = this.$t('card_item.title');
                            }
                        }
                        setTimeout(() => {
                            this.data_loaded = true
                        }, 1000);
                    });
            }
        },

        watch: {
            $route() {
                this.updateData(false, false);
            }
        },

        mounted() {
            this.updateData();
            this.$root.$on(['notification', 'product-updated'], () => {
                this.updateData(true, true)
            });
            this.$root.$on('update-products-filter', (filter) => {
                this.filter = filter;
                this.updateData(false, false)
            });
        },

        beforeDestroy() {
            this.$root.$off('notification');
            this.$root.$off('product-updated');
            this.$root.$off('update-products-filter');
        }
    }
</script>
