<template>
    <Navigation
            :links="links"
            :icon="'mdi-newspaper-variant'"
    />
</template>

<script>
    import Navigation from "../../components/common/Navigation";

    export default {
        name: "AssessNav",
        components: {
            Navigation
        },
        data: () => ({
            groups: [],
            links: []
        }),
        mounted() {
            this.$store.dispatch('getAllOSINTSourceGroupsAssess', {search:''})
                .then(() => {
                    this.groups = this.$store.getters.getOSINTSourceGroupsAssess;
                    this.links = [...this.groups]
                    if (!window.location.pathname.includes("/group/") && this.links.length > 0) {
                        this.$router.push(this.links[0].route)
                    }
                });
        }
    }
</script>
