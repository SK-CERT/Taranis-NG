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
                                <div class="title mb-2">{{ $t('main_menu.assess') }}</div>
                                <div class="subheading grey--text">{{ $t('dashboard.assess.tagcloud') }}</div>
                                <v-divider class="my-2"></v-divider>

                                <v-sheet class="mx-auto" elevation="4" max-width="calc(100% - 32px)">
                                    <wordcloud :data="tag_cloud" nameKey="word" valueKey="word_quantity"
                                        :color="myColors" :showTooltip="false" :rotate="myRotate" :fontSize="fontSize"
                                        :wordClick="wordClickHandler">
                                    </wordcloud>
                                </v-sheet>

                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2" color="primary">
                                    mdi-email-multiple
                                </v-icon>
                                <span class="caption grey--text"><strong>{{ getData.total_news_items }}</strong> {{
                                    $t('dashboard.assess.total') }}</span>
                            </v-card-text>
                        </v-card>
                    </template>
                </v-col>

                <v-col cols="4" class="pa-2 mb-8">
                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">{{ $t('dashboard.collect.title') }}</div>
                                <div class="subheading grey--text">{{ $t('dashboard.collect.status') }}</div>
                                <v-divider class="my-2"></v-divider>

                                <v-icon class="mr-2" color="green">
                                    mdi-lightbulb-off-outline
                                </v-icon>
                                <span class="caption grey--text">Collectors are pending at the moment.</span>
                                <v-divider inset class="mb-2 mt-2"></v-divider>

                                <v-icon class="mr-2" color="primary">
                                    mdi-clock-check-outline
                                </v-icon>
                                <span class="caption grey--text">
                                    Last successful run ended at <b>{{ getData.latest_collected }}</b>
                                </span>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">{{ $t('main_menu.analyze') }}</div>
                                <div class="subheading grey--text">{{ $t('dashboard.analyze.status') }}</div>
                                <v-divider class="my-2"></v-divider>

                                <!-- Dynamic state display from database -->
                                <template v-for="(stateData, stateName) in getData.report_item_states">
                                    <div :key="stateName" v-if="stateData.count > 0">
                                        <div class="d-flex align-center mb-2">
                                            <v-icon class="mr-2" :color="stateData.color" size="small">
                                                {{ stateData.icon }}
                                            </v-icon>
                                            <span class="caption grey--text">
                                                <b>{{ stateData.count }}</b>
                                                {{($te('workflow.states.' + stateData.display_name)
                                                    ? $t('workflow.states.' + stateData.display_name)
                                                    : stateData.display_name
                                                  ).toLowerCase()}}
                                                {{ $t('dashboard.analyze.report_items') }}.
                                            </span>
                                        </div>
                                        <v-divider inset class="mb-2"></v-divider>
                                    </div>
                                </template>

                                <!-- Total summary -->
                                <div class="d-flex align-center mt-2">
                                    <v-icon class="mr-2" color="primary">
                                        mdi-file-document
                                    </v-icon>
                                    <span class="caption grey--text">
                                        <b>{{ getData.total_report_items || 0 }}</b> {{ $t('dashboard.analyze.total') }}.
                                    </span>
                                </div>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">{{ $t('main_menu.publish') }}</div>
                                <div class="subheading grey--text">{{ $t('dashboard.publish.status') }}</div>
                                <v-divider class="my-2"></v-divider>

                                <!-- Dynamic state display from database -->
                                <template v-for="(stateData, stateName) in getData.product_states">
                                    <div v-if="stateData.count > 0" :key="stateName">
                                        <div class="d-flex align-center mb-2">
                                            <v-icon class="mr-2" :color="stateData.color" size="small">
                                                {{ stateData.icon }}
                                            </v-icon>
                                            <span class="caption grey--text">
                                                <b>{{ stateData.count }}</b>
                                                {{($te('workflow.states.' + stateData.display_name)
                                                    ? $t('workflow.states.' + stateData.display_name)
                                                    : stateData.display_name
                                                  ).toLowerCase()}}
                                                {{ $t('dashboard.publish.products') }}.
                                            </span>
                                        </div>
                                        <v-divider inset class="mb-2"></v-divider>
                                    </div>
                                </template>

                                <!-- Total summary -->
                                <div class="d-flex align-center mt-2">
                                    <v-icon class="mr-2" color="primary">
                                        mdi-package-variant
                                    </v-icon>
                                    <span class="caption grey--text">
                                        <b>{{ getData.total_products || 0 }}</b> {{ $t('dashboard.publish.total') }}.
                                    </span>
                                </div>
                            </v-card-text>
                        </v-card>
                    </template>

                    <template>
                        <v-card class="mt-4 mx-auto" max-width="100%">
                            <v-card-text class="pt-0">
                                <div class="title mb-2">{{ $t('dashboard.database.title') }}</div>
                                <div class="subheading grey--text">{{ $t('dashboard.database.status') }}</div>
                                <v-divider class="my-2"></v-divider>
                                <v-icon class="mr-2" color="blue">
                                    mdi-database
                                </v-icon>
                                <span class="caption grey--text"><b>{{ getData.total_database_items }}</b> {{
                                    $t('dashboard.database.total') }}.</span>
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
