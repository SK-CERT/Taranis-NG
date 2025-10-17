<template>
    <ViewLayout>
        <template v-slot:panel>

        </template>
        <template v-slot:content>
            <v-row no-gutters>

                <v-col cols="8" class="pa-2 mb-8">
                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">Assess</div>
                                <div class="subheading grey--text">Tagcloud for latest collected news items.</div>
                                <v-divider class="my-2"></v-divider>

                                <v-sheet class="mx-auto"
                                         elevation="4"
                                         max-width="calc(100% - 32px)">
                                    <wordcloud :data="tag_cloud"
                                               nameKey="word"
                                               valueKey="word_quantity"
                                               :color="myColors"
                                               :showTooltip="false"
                                               :rotate="myRotate"
                                               :fontSize="fontSize"
                                               :wordClick="wordClickHandler">
                                    </wordcloud>
                                </v-sheet>

                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2">
                                    mdi-email-multiple
                                </v-icon>
                                <span class="caption grey--text">There are <strong>{{ getData.total_news_items }}</strong> total Assess items.</span>
                            </v-card-text>
                        </v-card>
                    </template>
                </v-col>

                <v-col cols="4" class="pa-2 mb-8">
                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">Collect</div>
                                <div class="subheading grey--text">Collectors activity status</div>
                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2" color="green">
                                    mdi-lightbulb-off-outline
                                </v-icon>
                                <span class="caption grey--text ">Collectors are pending at the moment.</span>
                                <v-divider inset></v-divider>

                                <v-icon class="mr-2">
                                    mdi-clock-check-outline
                                </v-icon>
                                <span class="caption grey--text ">
                                    Last successful run ended at <b>{{ getData.latest_collected }}</b>
                                </span>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">Analyze</div>
                                <div class="subheading grey--text">Report items status</div>
                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2">
                                    mdi-account
                                </v-icon>
                                <span class="caption grey--text">There are <b>{{ getData.report_items_completed }}</b> completed analyses.</span>
                                <v-divider inset></v-divider>
                                <v-icon class="mr-2" color="grey">
                                    mdi-account-question-outline
                                </v-icon>
                                <span class="caption grey--text">There are <b>{{ getData.report_items_in_progress }}</b> pending analyses.</span>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">Publish</div>
                                <div class="subheading grey--text">Products items status</div>
                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2" color="orange">
                                    mdi-email-check-outline
                                </v-icon>
                                <span class="caption grey--text">There are <b>{{ getData.total_products }}</b> products ready for publications.</span>
                                <v-divider inset></v-divider>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">Database</div>
                                <div class="subheading grey--text">Data summary</div>
                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2" color="blue">
                                    mdi-database
                                </v-icon>
                                <span class="caption grey--text">There are <b>{{ getData.total_database_items }}</b> total records.</span>
                            </v-card-text>
                        </v-card>
                    </template>
                </v-col>

            </v-row>
        </template>
    </ViewLayout>
</template>

<script>
    import wordcloud from 'vue-wordcloud'
    import ViewLayout from "../../components/layouts/ViewLayout";
    import Settings, { getSettingBoolean, isInitializedSetting } from "@/services/settings";

    export default {
        name: "DashboardView",
        components: {
            wordcloud,
            ViewLayout,
        },
        computed: {
            getData() {
                return this.$store.getters.getDashboardData
            }
        },
        data: () => ({
            myColors: [],
            myRotate: { "from": 0, "to": 0, "numOfOrientation": 0 },
            fontSize: [14, 50],
            tag_cloud: [],
        }),
        methods: {
            wordClickHandler(name, value, vm) {
                console.log('Word:', name, 'Quantity:', value);
            },

            refreshTagCloud() {
                this.$store.dispatch('getAllDashboardData')
                    .then(() => {
                        this.tag_cloud = this.$store.getters.getDashboardData.tag_cloud
                    });
            },

            initSetting() {
                if (getSettingBoolean(Settings.TAG_COLOR)) {
                    this.myColors = 'Category10';
                } else {
                    this.myColors = ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'];
                }
            }
        },
        mounted() {
            if (isInitializedSetting()) {
                this.initSetting();
            } else {
                this.$root.$on('settings-loaded', () => {
                    this.initSetting();
                });
            }

            this.refreshTagCloud()

            setInterval(function () {
                this.refreshTagCloud()
            }.bind(this), 600000);
        }
    }
</script>
