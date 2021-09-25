<template>
    <div class="user-menu cx-user-menu">
        <!--NOTIFICATION--> <!-- TODO: Temporary commented -->
        <!--<v-badge overlap color="red" class="">
            <span class="" slot="badge">3</span>
            <v-icon color="white" small class="pa-2">mdi-bell</v-icon>
        </v-badge>-->
        <QuickChat/>


        <!-- NOTiFiCATiON -->
        <v-menu offset-y >
            <template v-slot:activator="{on}">
                <v-btn icon v-on="on">
                    <v-icon color="white" medium>mdi-bell</v-icon>
                </v-btn>
            </template>
            <v-card
                    class="mt-0 mx-auto user-settings-notifications"
                    max-width="100%"
            >

                <v-card-text class="pt-0">
                    <div class="title mb-2">Notifications</div>
                    <!--<div class="subheading grey&#45;&#45;text">Number of pending analyses per hour</div>-->
                    <v-divider class="my-2"></v-divider>
                    <v-icon class="mr-2" color="green">
                        mdi-coffee-outline
                    </v-icon>
                    <span class="caption grey--text">Planned Server shutdown for 2 hours on <b>1.7.2020</b></span>
                    <v-divider inset ></v-divider>

                    <v-icon class="mr-2" color="blue">
                        mdi-update
                    </v-icon>
                    <span class="caption grey--text">Collectors restart every <b>24 hours</b> on midnight</span>
                    <v-divider inset ></v-divider>

                    <v-icon class="mr-2">
                        mdi-crosshairs-question
                    </v-icon>
                    <span class="caption grey--text">New QA section added to internal <b>Slack</b> channel</span>
                </v-card-text>
            </v-card>
        </v-menu>

        <!--USERMENU-->
        <v-menu close-on-click close-on-content-click offset-y st>
            <template v-slot:activator="{ on }">
                <div class="user-menu-button pl-0 pr-2">
                    <v-btn icon v-on="on">
                        <v-icon color="white" medium>mdi-shield-account</v-icon>
                    </v-btn>
                </div>
            </template>
            <v-list>
                <v-list-item>
                    <v-list-item-avatar class="">
                        <v-icon>mdi-shield-account</v-icon>
                    </v-list-item-avatar>
                    <v-list-item-content>
                        <v-list-item-title>{{username}}</v-list-item-title>
                        <v-list-item-subtitle>{{organizationName}}</v-list-item-subtitle>
                    </v-list-item-content>
                </v-list-item>
                <v-divider></v-divider>

                <v-list-item @click="settings">
                    <v-list-item-icon>
                        <v-icon>mdi-cog-outline</v-icon>
                    </v-list-item-icon>
                    <v-list-item-content>
                        <v-list-item-title > {{$t('user_menu.settings')}}</v-list-item-title>
                    </v-list-item-content>
                </v-list-item>

                <v-list-item @click="logout">
                    <v-list-item-icon>
                        <v-icon>mdi-logout</v-icon>
                    </v-list-item-icon>
                    <v-list-item-content>
                        <v-list-item-title> {{$t('user_menu.logout')}}</v-list-item-title>
                    </v-list-item-content>
                </v-list-item>
            </v-list>
        </v-menu>

        <UserSettings />

    </div>
</template>

<style>
    .user-menu {
        display: inherit;
    }

    .user-menu-button {
        margin-right: 0;
        margin-left: 0;
        /*height: 46px !important;*/
    }

    .user-menu .v-badge__badge {
        height: 18px;
        min-width: 18px;
        top: 2px;
        right: 2px;
    }

    .dark-mode-switch .v-list-item__icon {
        margin-right: 8px !important;
        margin-bottom: 8px;
        margin-top: 0;
        height: 54px;
    }
</style>

<script>
    import QuickChat from "./common/QuickChat";
    import UserSettings from "./UserSettings";

    export default {
        name: "UserMenu",
        components: {
            QuickChat,
            UserSettings
        },
        data: () => ({
            darkTheme: false
        }),
        computed: {
            username() {
                return this.$store.getters.getUserName
            },
            organizationName() {
                return this.$store.getters.getOrganizationName
            }
        },
        methods: {
            logout() {
                this.$store.dispatch('logout')
                    .then(() => {
                        window.location.reload()
                    })
            },
            settings() {
                this.$root.$emit('show-user-settings');
                //this.$root.$emit('settings-press-key');
            },
            darkToggle() {
                this.$vuetify.theme.dark = this.darkTheme
            }
        }
    }
</script>
