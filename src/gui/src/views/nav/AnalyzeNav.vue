<template>
     <Navigation
        :links = "links"
        :icon   = "'mdi-file-table'"
    />
</template>

<script>
    import Navigation from "../../components/common/Navigation";

    export default {
        name: "AnalyzeNav",
        components: {
            Navigation
        },
        data: () => ({
            groups: [],
            links: []
        }),
        mounted() {
            this.$store.dispatch('getAllReportItemGroups', {search:''})
                .then(() => {
                    this.groups = this.$store.getters.getReportItemGroups;

                    this.links.push({
                        icon: 'mdi-home-circle-outline',
                        title: 'nav_menu.local',
                        translate: '1',
                        route: '/analyze/local',
                    })

                    for (let i = 0; i < this.groups.length; i++) {
                        this.links.push({
                            icon: 'mdi-arrow-down-bold-circle-outline',
                            title: this.groups[i],
                            route: '/analyze/group/' + this.groups[i].replaceAll(" ", "-"),
                        })
                    }

                    if (!window.location.pathname.includes("/group/")) {

                        this.$router.push("/analyze/local").catch(()=>{});
                    }
                });

        }
    }
</script>
