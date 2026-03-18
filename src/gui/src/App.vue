<template>
    <v-app class="taranis">

        <MainMenu v-if="isAuthenticated()" />

        <v-navigation-drawer v-model="visible" width="96px" app clipped color="cx-drawer-bg" v-if="isAuthenticated()">
            <router-view name="nav"></router-view>
        </v-navigation-drawer>

        <v-main>
            <router-view />
        </v-main>

        <Notification v-if="isAuthenticated()" />
    </v-app>
</template>

<script>
    import MainMenu from "./components/MainMenu";
    import AuthMixin from "./services/auth/auth_mixin";
    import Notification from "./components/common/Notification";
    import Settings, { getSettingBoolean } from "@/services/settings";
    import { initSSE } from "@/api/auth";

    export default {
        name: 'App',
        components: {
            MainMenu,
            Notification,
        },
        data: () => ({
            visible: null,
            sseConnection: null,
        }),
        mixins: [AuthMixin],
        methods: {
            connectSSE() {
                this.$sse(((typeof (process.env.VUE_APP_TARANIS_NG_CORE_SSE) == "undefined") ? "$VUE_APP_TARANIS_NG_CORE_SSE" : process.env.VUE_APP_TARANIS_NG_CORE_SSE), { format: 'json', withCredentials: true })
                    .then(sse => {
                        this.sseConnection = sse
                        sse.onError(() => {
                            if (this.$store.getters.getJWT != '') {
                                this.reconnectSSE()
                            } else {
                                this.closeSSE()
                            }
                        });
                        sse.subscribe('news-items-updated', (data) => {
                            this.$root.$emit('news-items-updated', data)
                        });
                        sse.subscribe('report-items-updated', (data) => {
                            this.$root.$emit('report-items-updated', data)
                        });
                        sse.subscribe('report-item-updated', (data) => {
                            this.$root.$emit('report-item-updated', data)
                        });
                        sse.subscribe('report-item-locked', (data) => {
                            this.$root.$emit('report-item-locked', data)
                        });
                        sse.subscribe('report-item-unlocked', (data) => {
                            this.$root.$emit('report-item-unlocked', data)
                        });
                    }).catch(() => {
                        // eslint-disable-next-line no-console
                        // console.error("SSE connection failed", err)
                        this.sseConnection = null;
                    })
            },

            reconnectSSE() {
                this.closeSSE();
                this.connectSSE()
            },

            closeSSE() {
                if (this.sseConnection !== null) {
                    this.sseConnection.close()
                    this.sseConnection = null
                }
            },

            initUserSettings() {
                this.$store.dispatch('getAllSettings', { search: '' }).then(() => {
                    this.$vuetify.theme.dark = getSettingBoolean(Settings.DARK_THEME);
                    this.$store.state.settings.spellcheck = getSettingBoolean(Settings.SPELLCHECK);
                    this.$i18n.locale = this.$store.getters.getProfileLanguage;
                    this.$root.$emit('settings-loaded');
                });
                this.$store.dispatch('getUserWordLists');
                this.$store.dispatch('getUserHotkeys');
            }
        },
        updated() {
            this.$root.$emit('app-updated');
        },
        mounted() {
            if (this.$cookies.isKey('jwt')) {
                this.$store.dispatch('setToken', this.$cookies.get('jwt')).then(() => {
                    this.$cookies.remove("jwt")
                    this.connectSSE()
                });
            }

            if (localStorage.ACCESS_TOKEN) {
                if (this.isAuthenticated()) {
                    this.initUserSettings();
                    this.connectSSE()
                } else {
                    if (this.$store.getters.getJWT) {
                        this.logout()
                    }
                }
            }

            setInterval(function () {
                if (this.isAuthenticated()) {
                    if (this.needTokenRefresh() === true) {
                        this.$store.dispatch("refresh").then(() => {
                            this.reconnectSSE()
                        })
                    }
                } else {
                    if (this.$store.getters.getJWT) {
                        this.logout()
                    }
                }
            }.bind(this), 5000);

            this.$root.$on('nav-clicked', () => {
                this.visible = !this.visible
            });

            this.$root.$on('logged-in', () => {
                initSSE().then(() => {
                    this.connectSSE();
                })
                this.initUserSettings();
            });

        },
        beforeDestroy() {
            this.closeSSE();
        }
    };
</script>

<style src="./assets/common.css"></style>
<style src="./assets/centralize.css"></style>
