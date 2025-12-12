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
            // Add permanent "All" category
            this.links.push({
                icon: 'mdi-folder-multiple',
                color: '#81D4FA',
                title: this.$t('osint_source_group.all'),
                route: '/assess/group/all',
                id: 'all'
            });

            this.$store.dispatch('getAllOSINTSourceGroupsAssess', {search:''})
                .then(() => {
                    this.groups = this.$store.getters.getOSINTSourceGroups.items;
                    for (let i = 0; i < this.groups.length; i++) {
                        let title = this.groups[i].name
                        let color = null
                        if (this.groups[i].default === true) {
                            title = this.$t('osint_source_group.default_group')
                            color = '#BDBDBD'
                        }
                        this.links.push({
                            icon: 'mdi-folder-multiple',
                            color: color,
                            title: title,
                            route: '/assess/group/' + this.groups[i].id,
                            id: this.groups[i].id
                        })
                    }

                    if (!window.location.pathname.includes("/group/") && this.links.length > 0) {

                        this.$router.push(this.links[0].route)
                    }
                });
        }
    }
</script>
