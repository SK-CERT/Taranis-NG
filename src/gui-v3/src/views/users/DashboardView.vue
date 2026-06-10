<template>
    <ViewLayout>
        <template #panel>
            <!-- Future: Add dashboard controls/filters here -->
        </template>
        <template #content>
            <v-row no-gutters>
                <!-- Main Content - News Items & Tag Cloud -->
                <v-col cols="12" lg="8">
                    <v-card class="mt-2">
                        <v-card-text>
                            <div class="text-headline-medium mb-2">
                                {{ t('nav_menu.newsitems') }}
                            </div>
                            <div class="text-subtitle-2 text-medium-emphasis">
                                {{ t('dashboard.assess.tagcloud') }}
                            </div>
                            <v-divider class="my-2" />

                            <!-- Word Cloud -->
                            <WordCloud
                                :data="tagCloud"
                                :color-scheme="getColorScheme()"
                                :min-font-size="14"
                                :max-font-size="50"
                                :empty-message="t('common.no_data')"
                            />

                            <v-divider class="my-2" />
                            <v-icon class="me-2" color="primary"> mdi-email-multiple </v-icon>
                            <span class="text-caption text-medium-emphasis">
                                <strong>{{ dashboardData.total_news_items || 0 }}</strong>
                                {{ t('dashboard.assess.total') }}
                            </span>
                        </v-card-text>
                    </v-card>
                </v-col>

                <!-- Sidebar - Stats Cards -->
                <v-col cols="12" lg="4">
                    <!-- Collection Status -->
                    <v-card class="mt-2">
                        <v-card-text>
                            <div class="text-headline-small mb-2">
                                {{ t('dashboard.collect.title') }}
                            </div>
                            <div class="text-subtitle-2 text-medium-emphasis">
                                {{ t('dashboard.collect.status') }}
                            </div>
                            <v-divider class="my-2" />

                            <div class="d-flex align-center mb-2">
                                <v-icon class="me-2" color="green"> mdi-lightbulb-off-outline </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    {{ t('dashboard.collect.pending') }}
                                </span>
                            </div>
                            <v-divider inset class="mb-2 mt-2" />

                            <div class="d-flex align-center">
                                <v-icon class="me-2" color="primary"> mdi-clock-check-outline </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    {{ t('dashboard.collect.last_attempt') }}
                                    <strong>{{ dashboardData.latest_collected || 'N/A' }}</strong>
                                </span>
                            </div>
                        </v-card-text>
                    </v-card>

                    <!-- Report Items Status -->
                    <v-card class="mt-2">
                        <v-card-text>
                            <div class="text-headline-small mb-2">
                                {{ t('nav_menu.report_items') }}
                            </div>
                            <div class="text-subtitle-2 text-medium-emphasis">
                                {{ t('dashboard.analyze.status') }}
                            </div>
                            <v-divider class="my-2" />

                            <!-- Dynamic state display -->
                            <template v-for="(stateData, stateName) in dashboardData.report_item_states" :key="stateName">
                                <div v-if="stateData.count > 0">
                                    <div class="d-flex align-center mb-2">
                                        <v-icon class="me-2" :color="stateData.color" size="small">
                                            {{ stateData.icon }}
                                        </v-icon>
                                        <span class="text-caption text-medium-emphasis">
                                            <strong>{{ stateData.count }}</strong>
                                            {{ getStateDisplayName(stateData.display_name).toLowerCase() }}
                                            {{ t('dashboard.analyze.report_items') }}
                                        </span>
                                    </div>
                                    <v-divider inset class="mb-2" />
                                </div>
                            </template>

                            <!-- Total summary -->
                            <div class="d-flex align-center mt-2">
                                <v-icon class="me-2" color="primary"> mdi-file-document </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    <strong>{{ dashboardData.total_report_items || 0 }}</strong>
                                    {{ t('dashboard.analyze.total') }}
                                </span>
                            </div>
                        </v-card-text>
                    </v-card>

                    <!-- Products Status -->
                    <v-card class="mt-2">
                        <v-card-text>
                            <div class="text-headline-small mb-2">
                                {{ t('nav_menu.products') }}
                            </div>
                            <div class="text-subtitle-2 text-medium-emphasis">
                                {{ t('dashboard.publish.status') }}
                            </div>
                            <v-divider class="my-2" />

                            <!-- Dynamic state display -->
                            <template v-for="(stateData, stateName) in dashboardData.product_states" :key="stateName">
                                <div v-if="stateData.count > 0">
                                    <div class="d-flex align-center mb-2">
                                        <v-icon class="me-2" :color="stateData.color" size="small">
                                            {{ stateData.icon }}
                                        </v-icon>
                                        <span class="text-caption text-medium-emphasis">
                                            <strong>{{ stateData.count }}</strong>
                                            {{ getStateDisplayName(stateData.display_name).toLowerCase() }}
                                            {{ t('dashboard.publish.products') }}
                                        </span>
                                    </div>
                                    <v-divider inset class="mb-2" />
                                </div>
                            </template>

                            <!-- Total summary -->
                            <div class="d-flex align-center mt-2">
                                <v-icon class="me-2" color="primary"> mdi-package-variant </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    <strong>{{ dashboardData.total_products || 0 }}</strong>
                                    {{ t('dashboard.publish.total') }}
                                </span>
                            </div>
                        </v-card-text>
                    </v-card>

                    <!-- About Section -->
                    <v-card class="mt-2">
                        <v-card-text>
                            <div class="text-headline-small mb-2">
                                {{ t('dashboard.about.title') }}
                            </div>
                            <v-divider class="my-2" />

                            <!-- Version Info -->
                            <div class="d-flex align-center mb-2">
                                <v-icon class="me-2" color="blue"> mdi-information-outline </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    {{ t('dashboard.about.version') }}
                                    <strong>{{ appVersion }}</strong>
                                    {{ built }}
                                </span>
                            </div>

                            <!-- Commit Info -->
                            <v-divider inset class="my-2" />
                            <div class="d-flex align-center mb-2">
                                <v-icon class="me-2" color="blue"> mdi-source-branch </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    {{ t('dashboard.about.commit') }}
                                    <strong>{{ commit }}</strong>
                                    {{ commited }} {{ branchDisplay }}
                                </span>
                            </div>

                            <!-- Database Records -->
                            <v-divider inset class="my-2" />
                            <div class="d-flex align-center">
                                <v-icon class="me-2" color="blue"> mdi-database </v-icon>
                                <span class="text-caption text-medium-emphasis">
                                    <strong>{{ dashboardData.total_database_items || 0 }}</strong>
                                    {{ t('dashboard.about.total') }}
                                </span>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </template>
    </ViewLayout>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useDashboardStore } from '@/stores/dashboard'
    import { useSettingsStore } from '@/stores/settings'
    import ViewLayout from '@/components/layouts/ViewLayout.vue'
    import WordCloud from '@/components/dashboard/WordCloud.vue'
    import Settings from '@/services/settings'
    import { format } from 'date-fns'
    import gitMeta from '../../../git-info.json'
    import packageJson from '../../../package.json'

    const { t, te } = useI18n()
    const dashboardStore = useDashboardStore()
    const settingsStore = useSettingsStore()

    type DashboardStateInfo = {
        count: number
        color: string
        icon: string
        display_name: string
    }

    type DashboardData = {
        total_news_items: number
        total_products: number
        total_report_items: number
        total_database_items: number
        latest_collected: string
        tag_cloud: Array<{ word: string; word_quantity: number }>
        report_item_states: Record<string, DashboardStateInfo>
        product_states: Record<string, DashboardStateInfo>
    }

    const emptyDashboardData = (): DashboardData => ({
        total_news_items: 0,
        total_products: 0,
        total_report_items: 0,
        total_database_items: 0,
        latest_collected: '',
        tag_cloud: [],
        report_item_states: {},
        product_states: {}
    })

    // Version and build info (from git-info.json generated by prebuild script)
    const appVersion = ref(gitMeta.version || packageJson.version || 'unknown')
    const buildDate = ref(gitMeta.buildDate || null)
    const commitHash = ref(gitMeta.commit || null)
    const commitDate = ref(gitMeta.commitDate || null)
    const branchName = ref(gitMeta.branchName || null)

    const dashboardData = computed<DashboardData>(() => {
        return (dashboardStore.dashboard_data as DashboardData) || emptyDashboardData()
    })
    const tagCloud = computed(() => (Array.isArray(dashboardData.value.tag_cloud) ? dashboardData.value.tag_cloud : []))

    const formatToLocal = (dateString: string): string => {
        return format(new Date(dateString), 'yyyy-MM-dd HH:mm')
    }

    const built = computed(() => {
        return buildDate.value ? `(${formatToLocal(buildDate.value)})` : ''
    })

    const commit = computed(() => {
        return commitHash.value ? commitHash.value : ''
    })

    const commited = computed(() => {
        return commitDate.value ? `(${formatToLocal(commitDate.value)})` : ''
    })

    const branchDisplay = computed(() => {
        return branchName.value ? `[${branchName.value}]` : ''
    })

    let refreshInterval: ReturnType<typeof setInterval> | null = null

    /**
     * Get translated state display name
     */
    const getStateDisplayName = (displayName: string): string => {
        const key = `workflow.states.${displayName}`
        return te(key) ? t(key) : displayName
    }

    /**
     * Get color scheme based on settings
     */
    const getColorScheme = (): string[] => {
        try {
            const useCategory = settingsStore.getSetting(Settings.TAG_COLOR)
            if (useCategory) {
                return ['#ff7200', '#d9534f', '#5cb85c', '#0275d8', '#5bc0de', '#5a5a5a', '#ff9100', '#df691a', '#e67e22', '#27ae60']
            }
        } catch (e) {
            console.warn('[Dashboard] Could not load TAG_COLOR setting:', e)
        }
        return ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef']
    }

    /**
     * Refresh dashboard data
     */
    const refreshDashboard = async (): Promise<void> => {
        try {
            await dashboardStore.loadDashboardData()
        } catch (error) {
            console.error('[Dashboard] Error refreshing data:', error)
        }
    }

    /**
     * Component mount
     */
    onMounted(async () => {
        // Initial data load
        await refreshDashboard()

        // console.log('[DashboardView] Dashboard data loaded:', {tagCloudLength: tagCloud.value?.length, tagCloud: tagCloud.value, dashboardData: dashboardData.value})

        // Auto-refresh every 10 minutes (600000ms)
        refreshInterval = setInterval(() => {
            refreshDashboard()
        }, 600000)
    })

    /**
     * Component unmount
     */
    onUnmounted(() => {
        if (refreshInterval) {
            clearInterval(refreshInterval)
            refreshInterval = null
        }
    })
</script>
