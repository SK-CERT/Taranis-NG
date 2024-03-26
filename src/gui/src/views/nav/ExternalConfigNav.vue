<template>
    <Navigation
            :links  = "links"
            :icon   = "'mdi-ballot-outline'"
    />
</template>

<script>
    import Navigation from "../../components/common/Navigation";

    export default {
        name: "ExternalConfigNav",
        components: {
            Navigation
        },
        data: () => ({
            links: [
                { id: 1, icon: 'mdi-account-group', title: 'nav_menu.users', route: '/config/external/users', translate: '1' },
                { id: 2, icon: 'mdi-folder-multiple', title: 'nav_menu.asset_groups', route: '/config/external/groups', translate: '1' },
                { id: 3, icon: 'mdi-email-multiple-outline', title: 'nav_menu.notification_templates', route: '/config/external/templates', translate: '1' },
            ]
        })
    }
</script>