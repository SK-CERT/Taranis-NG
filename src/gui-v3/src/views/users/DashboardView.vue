<template>
    <main class="dashboard-page">
        <header class="dashboard-hero">
            <div class="dashboard-hero__identity">
                <div class="dashboard-hero__mark">
                    <v-icon size="28">mdi-view-dashboard-variant-outline</v-icon>
                </div>
                <div>
                    <h1>{{ t('main_menu.dashboard') }}</h1>
                    <p>{{ t('dashboard.subtitle') }}</p>
                </div>
            </div>

            <div class="dashboard-hero__activity">
                <div class="dashboard-hero__freshness">
                    <span class="activity-dot" />
                    <span>{{ t('dashboard.collect.last_attempt') }}</span>
                    <strong>{{ latestCollection }}</strong>
                </div>
                <v-btn
                    icon="mdi-refresh"
                    size="small"
                    variant="text"
                    :loading="refreshing"
                    :title="t('dashboard.refresh')"
                    @click="refreshDashboard"
                />
            </div>
        </header>

        <section class="dashboard-metrics">
            <v-card
                class="metric-card metric-card--news metric-card--linked"
                to="/assess"
                variant="flat"
            >
                <div class="metric-card__summary">
                    <div class="metric-card__icon metric-card__icon--blue">
                        <v-icon size="25">mdi-newspaper-variant-multiple-outline</v-icon>
                    </div>
                    <div class="metric-card__body">
                        <span>{{ t('nav_menu.newsitems') }}</span>
                        <strong>{{ (dashboardData.total_news_items || 0).toLocaleString() }}</strong>
                        <small>{{ t('dashboard.assess.total') }}</small>
                    </div>
                </div>
                <div class="news-ingestion">
                    <header class="news-ingestion__header">
                        <span>
                            <v-icon size="15">mdi-chart-bar</v-icon>
                            {{ t('toolbar_filter.last_7_days') }}
                        </span>
                    </header>
                    <div
                        class="news-ingestion__chart"
                        role="img"
                        :aria-label="`${t('nav_menu.newsitems')}: ${t('toolbar_filter.last_7_days')}`"
                    >
                        <div
                            v-for="point in ingestionData"
                            :key="point.date"
                            class="news-ingestion__column"
                            :title="`${point.fullDate}: ${point.value}`"
                        >
                            <strong>{{ point.value }}</strong>
                            <span class="news-ingestion__track">
                                <i :style="{ height: `${point.height}%` }" />
                            </span>
                            <small>{{ point.label }}</small>
                        </div>
                    </div>
                </div>
                <v-icon
                    class="metric-card__arrow"
                    size="18"
                >
                    mdi-arrow-top-right
                </v-icon>
            </v-card>

            <v-card
                v-for="metric in dashboardMetrics"
                :key="metric.label"
                class="metric-card"
                :class="{ 'metric-card--linked': metric.to }"
                :to="metric.to"
                variant="flat"
            >
                <div
                    class="metric-card__icon"
                    :class="`metric-card__icon--${metric.tone}`"
                >
                    <v-icon size="25">{{ metric.icon }}</v-icon>
                </div>
                <div class="metric-card__body">
                    <span>{{ metric.label }}</span>
                    <strong>{{ metric.value.toLocaleString() }}</strong>
                    <small>{{ metric.detail }}</small>
                </div>
                <v-icon
                    v-if="metric.to"
                    class="metric-card__arrow"
                    size="18"
                >
                    mdi-arrow-top-right
                </v-icon>
            </v-card>
        </section>

        <section class="dashboard-grid">
            <article class="dashboard-card dashboard-cloud">
                <header class="dashboard-card__header">
                    <div>
                        <span class="dashboard-card__eyebrow">{{ t('main_menu.assess') }}</span>
                        <h2>{{ t('dashboard.assess.trending') }}</h2>
                        <p>{{ t('dashboard.assess.tagcloud') }}</p>
                    </div>
                    <div class="dashboard-cloud__header-actions">
                        <div
                            class="dashboard-cloud__period-control"
                            role="group"
                            :aria-label="t('dashboard.assess.tagcloud')"
                        >
                            <v-btn-toggle
                                class="dashboard-cloud__period-toggle"
                                color="primary"
                                density="compact"
                                mandatory
                                variant="outlined"
                                :model-value="tagCloudPeriod"
                            >
                                <v-btn
                                    v-for="period in tagCloudPeriodOptions"
                                    :key="period.value"
                                    :value="period.value"
                                    size="small"
                                    @click="selectTagCloudPeriod(period.value)"
                                >
                                    {{ period.label }}
                                </v-btn>
                            </v-btn-toggle>
                        </div>

                        <v-btn
                            to="/assess"
                            icon="mdi-arrow-right"
                            size="small"
                            variant="tonal"
                            color="primary"
                            :title="t('main_menu.assess')"
                        />
                    </div>
                </header>

                <v-dialog
                    v-model="customRangeDialog"
                    max-width="460"
                >
                    <v-card>
                        <v-card-title>{{ t('toolbar_filter.custom_filter') }}</v-card-title>
                        <v-card-text class="dashboard-cloud__range-fields">
                            <v-text-field
                                v-model="draftDateFrom"
                                density="comfortable"
                                type="date"
                                variant="outlined"
                                :label="t('analyze.from')"
                                :max="draftDateTo || latestCustomDate"
                            />
                            <v-text-field
                                v-model="draftDateTo"
                                density="comfortable"
                                type="date"
                                variant="outlined"
                                :label="t('analyze.to')"
                                :min="draftDateFrom"
                                :max="latestCustomDate"
                            />
                        </v-card-text>
                        <v-card-actions>
                            <v-spacer />
                            <v-btn
                                variant="text"
                                @click="customRangeDialog = false"
                            >
                                {{ t('common.cancel') }}
                            </v-btn>
                            <v-btn
                                color="primary"
                                variant="flat"
                                :disabled="!customRangeValid"
                                @click="applyCustomRange"
                            >
                                {{ t('common.done') }}
                            </v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>

                <WordCloud
                    :data="tagCloud"
                    :color-scheme="getColorScheme()"
                    :min-font-size="15"
                    :max-font-size="46"
                    :empty-message="t('common.no_data')"
                    :word-action-label="t('toolbar_filter.search')"
                    viewport-fit
                    @select-word="openWordSearch"
                />
            </article>

            <aside class="dashboard-rail">
                <section class="dashboard-card collection-card">
                    <header class="dashboard-card__header dashboard-card__header--compact">
                        <div>
                            <span class="dashboard-card__eyebrow">{{ t('dashboard.collect.status') }}</span>
                            <h2>{{ t('dashboard.collect.title') }}</h2>
                        </div>
                        <div class="collection-card__icon">
                            <v-icon>mdi-radar</v-icon>
                        </div>
                    </header>
                    <div class="collection-card__status">
                        <span class="activity-dot" />
                        <strong>{{ t('dashboard.collect.pending') }}</strong>
                    </div>
                    <div class="collection-card__time">
                        <v-icon size="17">mdi-clock-check-outline</v-icon>
                        <span>{{ latestCollection }}</span>
                    </div>
                </section>

                <section class="dashboard-card workflow-card">
                    <div class="workflow-group">
                        <header>
                            <div class="workflow-heading">
                                <span class="workflow-heading__icon workflow-heading__icon--analyze">
                                    <v-icon size="19">mdi-file-document-multiple-outline</v-icon>
                                </span>
                                <div>
                                    <span>{{ t('main_menu.analyze') }}</span>
                                    <strong>{{ t('nav_menu.report_items') }}</strong>
                                </div>
                            </div>
                            <v-btn
                                to="/analyze/local"
                                icon="mdi-arrow-right"
                                size="x-small"
                                variant="text"
                                :title="t('main_menu.analyze')"
                            />
                        </header>
                        <div class="state-list">
                            <div
                                v-for="state in reportStates"
                                :key="state.name"
                                class="state-row"
                            >
                                <v-icon
                                    :color="state.color"
                                    size="16"
                                >
                                    {{ state.icon }}
                                </v-icon>
                                <span>{{ getStateDisplayName(state.display_name) }}</span>
                                <strong>{{ state.count }}</strong>
                            </div>
                        </div>
                    </div>

                    <div class="workflow-divider" />

                    <div class="workflow-group">
                        <header>
                            <div class="workflow-heading">
                                <span class="workflow-heading__icon workflow-heading__icon--publish">
                                    <v-icon size="19">mdi-send-outline</v-icon>
                                </span>
                                <div>
                                    <span>{{ t('main_menu.publish') }}</span>
                                    <strong>{{ t('nav_menu.products') }}</strong>
                                </div>
                            </div>
                            <v-btn
                                to="/publish"
                                icon="mdi-arrow-right"
                                size="x-small"
                                variant="text"
                                :title="t('main_menu.publish')"
                            />
                        </header>
                        <div class="state-list">
                            <div
                                v-for="state in productStates"
                                :key="state.name"
                                class="state-row"
                            >
                                <v-icon
                                    :color="state.color"
                                    size="16"
                                >
                                    {{ state.icon }}
                                </v-icon>
                                <span>{{ getStateDisplayName(state.display_name) }}</span>
                                <strong>{{ state.count }}</strong>
                            </div>
                        </div>
                    </div>
                </section>
            </aside>
        </section>

        <footer class="dashboard-system">
            <div class="dashboard-system__title">
                <v-icon size="19">mdi-information-outline</v-icon>
                <strong>{{ t('dashboard.about.system') }}</strong>
            </div>
            <div class="dashboard-system__item">
                <span>{{ t('dashboard.about.version') }}</span>
                <strong>{{ appVersion }}</strong>
                <small>{{ built }}</small>
            </div>
            <div class="dashboard-system__item">
                <span>{{ t('dashboard.about.commit') }}</span>
                <strong>{{ commit }}</strong>
                <small>{{ commited }} {{ branchDisplay }}</small>
            </div>
        </footer>
    </main>
</template>

<script setup lang="ts">
    import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRouter } from 'vue-router'
    import { useDashboardStore } from '@/stores/dashboard'
    import type { TagCloudQuery } from '@/api/dashboard'
    import WordCloud from '@/components/dashboard/WordCloud.vue'
    import { format } from 'date-fns'
    import gitMeta from '../../../git-info.json'
    import packageJson from '../../../package.json'
    import { useSseResync } from '@/composables/useSseResync'

    const dashboardStore = useDashboardStore()
    const { t, te, locale } = useI18n()
    const router = useRouter()

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
        news_items_by_day: Array<{ date: string; count: number }>
        tag_cloud: Array<{ word: string; word_quantity: number }>
        report_item_states: Record<string, DashboardStateInfo>
        product_states: Record<string, DashboardStateInfo>
    }

    type DashboardMetric = {
        label: string
        value: number
        detail: string
        icon: string
        tone: 'blue' | 'cyan' | 'amber' | 'slate'
        to?: string
    }

    type DisplayState = DashboardStateInfo & {
        name: string
    }

    type TagCloudPeriod = 'lastSevenDays' | 'today' | 'yesterday' | 'custom'

    const emptyDashboardData = (): DashboardData => ({
        total_news_items: 0,
        total_products: 0,
        total_report_items: 0,
        total_database_items: 0,
        latest_collected: '',
        news_items_by_day: [],
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
    const refreshing = ref(false)

    const previousDay = (): string => {
        const date = new Date()
        date.setDate(date.getDate() - 1)
        return format(date, 'yyyy-MM-dd')
    }

    const latestCustomDate = ref(previousDay())
    const customDateFrom = ref(latestCustomDate.value)
    const customDateTo = ref(latestCustomDate.value)
    const draftDateFrom = ref(latestCustomDate.value)
    const draftDateTo = ref(latestCustomDate.value)
    const customRangeDialog = ref(false)
    const tagCloudPeriod = ref<TagCloudPeriod>('lastSevenDays')
    const yesterdayLabel = computed(() => new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' }).format(-1, 'day'))
    const tagCloudPeriodOptions = computed<Array<{ value: TagCloudPeriod; label: string }>>(() => [
        { value: 'lastSevenDays', label: t('toolbar_filter.last_7_days') },
        { value: 'today', label: t('toolbar_filter.today') },
        { value: 'yesterday', label: yesterdayLabel.value },
        { value: 'custom', label: t('toolbar_filter.custom_filter') }
    ])
    const tagCloudQuery = computed<TagCloudQuery>(() => {
        if (tagCloudPeriod.value === 'lastSevenDays') return { range: 'LAST_7_DAYS' }
        if (tagCloudPeriod.value === 'today') return { range: 'TODAY' }
        if (tagCloudPeriod.value === 'yesterday') {
            return { dateFrom: latestCustomDate.value, dateTo: latestCustomDate.value }
        }
        return { dateFrom: customDateFrom.value, dateTo: customDateTo.value }
    })
    const customRangeValid = computed(
        () =>
            Boolean(draftDateFrom.value && draftDateTo.value) &&
            draftDateFrom.value <= draftDateTo.value &&
            draftDateTo.value <= latestCustomDate.value
    )

    const ingestionData = computed(() => {
        const dailyCounts = dashboardData.value.news_items_by_day || []
        const maximum = Math.max(1, ...dailyCounts.map((item) => item.count))
        const weekdayFormatter = new Intl.DateTimeFormat(locale.value, { weekday: 'short' })
        const dateFormatter = new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short' })

        return dailyCounts.map((item) => {
            const date = new Date(`${item.date}T12:00:00`)

            return {
                date: item.date,
                fullDate: dateFormatter.format(date),
                label: weekdayFormatter.format(date),
                value: item.count,
                height: item.count === 0 ? 0 : Math.max(10, Math.round((item.count / maximum) * 100))
            }
        })
    })

    const openWordSearch = (word: string): void => {
        router.push({ name: 'assess', params: { groupId: 'all' }, query: { search: word } })
    }

    const dashboardMetrics = computed<DashboardMetric[]>(() => [
        {
            label: t('nav_menu.report_items'),
            value: dashboardData.value.total_report_items || 0,
            detail: t('dashboard.analyze.total'),
            icon: 'mdi-file-document-multiple-outline',
            tone: 'cyan',
            to: '/analyze/local'
        },
        {
            label: t('nav_menu.products'),
            value: dashboardData.value.total_products || 0,
            detail: t('dashboard.publish.total'),
            icon: 'mdi-package-variant-closed',
            tone: 'amber',
            to: '/publish'
        }
    ])

    const toDisplayStates = (states: Record<string, DashboardStateInfo>): DisplayState[] =>
        Object.entries(states || {})
            .map(([name, state]) => ({ name, ...state }))
            .filter((state) => Number(state.count) > 0)

    const reportStates = computed(() => toDisplayStates(dashboardData.value.report_item_states))
    const productStates = computed(() => toDisplayStates(dashboardData.value.product_states))

    const formatToLocal = (dateString: string): string => {
        const date = new Date(dateString)
        return Number.isNaN(date.getTime()) ? dateString : format(date, 'yyyy-MM-dd HH:mm')
    }

    const latestCollection = computed(() =>
        dashboardData.value.latest_collected ? formatToLocal(dashboardData.value.latest_collected) : '—'
    )

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
    let refreshPromise: Promise<void> | null = null

    /**
     * Get translated state display name
     */
    const getStateDisplayName = (displayName: string): string => {
        const stateKey = `workflow.states.${displayName.toLowerCase().replaceAll(' ', '_')}`
        return te(stateKey) ? t(stateKey) : displayName.replaceAll('_', ' ')
    }

    /**
     * Get color scheme based on settings
     */
    const getColorScheme = (): string[] => {
        return ['#2f86c1', '#1e9f9a', '#6b9f3a', '#dc8b21', '#d1606b', '#8a6bb8', '#238f70', '#5577b9']
    }

    /**
     * Refresh dashboard data
     */
    const refreshDashboard = (): Promise<void> => {
        if (refreshPromise) return refreshPromise

        refreshPromise = (async () => {
            refreshing.value = true
            try {
                await dashboardStore.loadDashboardData(tagCloudQuery.value)
            } catch (error) {
                console.error('[Dashboard] Error refreshing data:', error)
            } finally {
                refreshing.value = false
                refreshPromise = null
            }
        })()
        return refreshPromise
    }

    const resyncDashboard = async (): Promise<void> => {
        if (refreshPromise) await refreshPromise
        await refreshDashboard()
    }

    const refreshSelectedPeriod = async (): Promise<void> => {
        if (refreshPromise) await refreshPromise
        await refreshDashboard()
    }

    const selectTagCloudPeriod = (period: TagCloudPeriod | null): void => {
        if (!period) return
        if (period !== 'custom') {
            tagCloudPeriod.value = period
            return
        }

        latestCustomDate.value = previousDay()
        draftDateFrom.value = customDateFrom.value
        draftDateTo.value = customDateTo.value
        customRangeDialog.value = true
    }

    const applyCustomRange = (): void => {
        if (!customRangeValid.value) return

        const refreshExistingCustomRange = tagCloudPeriod.value === 'custom'
        customDateFrom.value = draftDateFrom.value
        customDateTo.value = draftDateTo.value
        tagCloudPeriod.value = 'custom'
        customRangeDialog.value = false

        if (refreshExistingCustomRange) void refreshSelectedPeriod()
    }

    watch(tagCloudPeriod, () => {
        void refreshSelectedPeriod()
    })

    useSseResync(resyncDashboard)

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

<style scoped>
    .dashboard-page {
        width: 100%;
        height: 100%;
        padding: clamp(0.65rem, 1.2vw, 1rem);
        overflow-y: auto;
        background: var(--review-workspace);
        color: rgb(var(--v-theme-on-surface));
    }

    .dashboard-hero,
    .dashboard-card,
    .metric-card,
    .dashboard-system {
        border: 1px solid var(--review-panel-border);
        background: rgb(var(--v-theme-surface));
        box-shadow: 0 3px 12px rgba(18, 44, 70, 0.11);
    }

    .dashboard-hero {
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 86px;
        padding: 0.85rem 1rem;
        border-left: 5px solid rgb(var(--v-theme-primary));
        border-radius: 5px;
    }

    .dashboard-hero__identity,
    .dashboard-hero__activity,
    .dashboard-hero__freshness,
    .dashboard-system__title,
    .dashboard-system__item,
    .collection-card__status,
    .collection-card__time {
        display: flex;
        align-items: center;
    }

    .dashboard-hero__identity {
        min-width: 0;
        gap: 0.85rem;
    }

    .dashboard-hero__mark {
        display: grid;
        width: 48px;
        height: 48px;
        flex: 0 0 auto;
        place-items: center;
        border: 1px solid rgba(var(--v-theme-primary), 0.28);
        border-radius: 4px;
        background: rgba(var(--v-theme-primary), 0.1);
        color: rgb(var(--v-theme-primary));
    }

    .dashboard-hero h1 {
        margin: 0;
        font-size: clamp(1.45rem, 2.2vw, 2rem);
        font-weight: 750;
        letter-spacing: -0.035em;
        line-height: 1.1;
    }

    .dashboard-hero p,
    .dashboard-card__header p {
        margin: 0.25rem 0 0;
        color: rgba(var(--v-theme-on-surface), 0.62);
        font-size: 0.8rem;
    }

    .dashboard-hero__activity {
        gap: 0.45rem;
    }

    .dashboard-hero__freshness {
        gap: 0.42rem;
        color: rgba(var(--v-theme-on-surface), 0.65);
        font-size: 0.75rem;
        white-space: nowrap;
    }

    .dashboard-hero__freshness strong {
        color: rgb(var(--v-theme-on-surface));
    }

    .activity-dot {
        width: 8px;
        height: 8px;
        flex: 0 0 auto;
        border-radius: 50%;
        background: rgb(var(--v-theme-success));
        box-shadow: 0 0 0 3px rgba(var(--v-theme-success), 0.14);
    }

    .dashboard-metrics {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.7rem;
        margin-top: 0.7rem;
    }

    .metric-card {
        position: relative;
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        min-height: 104px;
        padding: 0.8rem;
        gap: 0.75rem;
        border-radius: 4px;
        transition:
            border-color 140ms ease,
            transform 140ms ease;
    }

    .metric-card--linked:hover {
        border-color: rgb(var(--v-theme-primary));
        transform: translateY(-1px);
    }

    .metric-card--news {
        grid-column: span 2;
        grid-template-columns: minmax(150px, 0.72fr) minmax(260px, 1.28fr);
        align-items: stretch;
    }

    .metric-card__summary {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr);
        align-items: start;
        gap: 0.75rem;
    }

    .metric-card__icon {
        display: grid;
        width: 42px;
        height: 42px;
        place-items: center;
        border-radius: 4px;
    }

    .metric-card__icon--blue {
        background: rgba(30, 117, 190, 0.13);
        color: #287bb9;
    }

    .metric-card__icon--cyan {
        background: rgba(23, 150, 165, 0.13);
        color: #158393;
    }

    .metric-card__icon--amber {
        background: rgba(220, 140, 25, 0.14);
        color: #c47a12;
    }

    .metric-card__icon--slate {
        background: rgba(var(--v-theme-on-surface), 0.09);
        color: rgba(var(--v-theme-on-surface), 0.68);
    }

    .metric-card__body {
        display: flex;
        min-width: 0;
        flex-direction: column;
    }

    .metric-card__body > span {
        overflow: hidden;
        color: rgba(var(--v-theme-on-surface), 0.66);
        font-size: 0.75rem;
        font-weight: 650;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .metric-card__body > strong {
        margin-top: 0.05rem;
        font-size: clamp(1.5rem, 2.2vw, 2rem);
        font-weight: 750;
        letter-spacing: -0.04em;
        line-height: 1.15;
    }

    .metric-card__body > small {
        overflow: hidden;
        color: rgba(var(--v-theme-on-surface), 0.48);
        font-size: 0.68rem;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .metric-card__arrow {
        position: absolute;
        top: 0.65rem;
        right: 0.65rem;
        color: rgba(var(--v-theme-on-surface), 0.38);
    }

    .dashboard-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.8fr) minmax(300px, 0.8fr);
        align-items: start;
        margin-top: 0.7rem;
        gap: 0.7rem;
    }

    .dashboard-card {
        overflow: hidden;
        border-radius: 5px;
    }

    .dashboard-card__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.85rem 0.95rem;
        gap: 1rem;
        border-bottom: 1px solid var(--review-list-border);
    }

    .dashboard-card__header--compact {
        border-bottom: 0;
    }

    .dashboard-card__eyebrow {
        display: block;
        margin-bottom: 0.12rem;
        color: rgb(var(--v-theme-primary));
        font-size: 0.66rem;
        font-weight: 750;
        letter-spacing: 0.09em;
        text-transform: uppercase;
    }

    .dashboard-card__header h2 {
        margin: 0;
        font-size: 1.08rem;
        font-weight: 720;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .dashboard-cloud__header-actions,
    .dashboard-cloud__period-control {
        display: flex;
        min-width: 0;
        align-items: center;
    }

    .dashboard-cloud__header-actions {
        flex: 1 1 auto;
        justify-content: flex-end;
        gap: 0.8rem;
    }

    .dashboard-cloud__period-control {
        justify-content: flex-end;
        gap: 0.45rem;
    }

    .dashboard-cloud__period-toggle {
        height: 30px;
        border-color: rgba(var(--v-theme-outline), 0.2);
        background: rgba(var(--v-theme-surface-variant), 0.12);
    }

    .dashboard-cloud__period-toggle :deep(.v-btn) {
        min-width: 0;
        height: 30px;
        padding-inline: 0.55rem;
        font-size: 0.66rem;
        letter-spacing: 0;
        text-transform: none;
    }

    .dashboard-cloud__range-fields {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.8rem;
        padding-top: 0.65rem;
    }

    .dashboard-cloud :deep(.word-cloud-container) {
        border-radius: 0;
        background:
            radial-gradient(circle at 45% 48%, rgba(var(--v-theme-primary), 0.1), transparent 64%), rgba(var(--v-theme-surface-variant), 0.1);
    }

    .dashboard-rail {
        position: sticky;
        top: 0.65rem;
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 0.7rem;
    }

    .collection-card {
        flex: 0 0 auto;
    }

    .collection-card__icon {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        border-radius: 4px;
        background: rgba(var(--v-theme-primary), 0.1);
        color: rgb(var(--v-theme-primary));
    }

    .collection-card__status,
    .collection-card__time {
        margin-inline: 0.95rem;
        gap: 0.5rem;
    }

    .collection-card__status {
        min-height: 42px;
        padding-block: 0.5rem;
        border-top: 1px solid var(--review-list-border);
        color: rgba(var(--v-theme-on-surface), 0.74);
        font-size: 0.76rem;
    }

    .collection-card__time {
        min-height: 36px;
        border-top: 1px solid rgba(var(--v-theme-outline), 0.14);
        color: rgba(var(--v-theme-on-surface), 0.58);
        font-size: 0.72rem;
    }

    .news-ingestion {
        min-width: 0;
        padding-left: 0.8rem;
        border-left: 1px solid var(--review-list-border);
    }

    .news-ingestion__header,
    .news-ingestion__header > span {
        display: flex;
        align-items: center;
    }

    .news-ingestion__header {
        justify-content: space-between;
        margin-bottom: 0.2rem;
        gap: 0.5rem;
        color: rgba(var(--v-theme-on-surface), 0.68);
        font-size: 0.62rem;
        font-weight: 650;
    }

    .news-ingestion__header > span {
        gap: 0.35rem;
    }

    .news-ingestion__chart {
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        height: 69px;
        gap: 0.28rem;
    }

    .news-ingestion__column {
        display: grid;
        min-width: 0;
        grid-template-rows: 13px 1fr 13px;
        align-items: end;
        justify-items: center;
        color: rgba(var(--v-theme-on-surface), 0.55);
    }

    .news-ingestion__column > strong {
        font-size: 0.54rem;
        font-weight: 700;
    }

    .news-ingestion__column > small {
        overflow: hidden;
        width: 100%;
        font-size: 0.54rem;
        text-align: center;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
    }

    .news-ingestion__track {
        position: relative;
        width: min(62%, 22px);
        height: 100%;
        overflow: hidden;
        border-radius: 2px 2px 0 0;
        background: rgba(var(--v-theme-primary), 0.08);
    }

    .news-ingestion__track > i {
        position: absolute;
        right: 0;
        bottom: 0;
        left: 0;
        border-radius: 2px 2px 0 0;
        background: linear-gradient(180deg, rgb(var(--v-theme-primary)), rgba(var(--v-theme-primary), 0.58));
        transition: height 180ms ease;
    }

    .news-ingestion__column:hover .news-ingestion__track > i {
        background: rgb(var(--v-theme-secondary));
    }

    .workflow-card {
        display: grid;
        flex: 0 0 auto;
        grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    }

    .workflow-group {
        padding: 0.8rem 0.9rem;
    }

    .workflow-group header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
    }

    .workflow-heading {
        display: flex;
        min-width: 0;
        align-items: center;
        gap: 0.5rem;
    }

    .workflow-heading > div {
        display: flex;
        min-width: 0;
        flex-direction: column;
    }

    .workflow-heading > div > span {
        color: rgb(var(--v-theme-primary));
        font-size: 0.65rem;
        font-weight: 750;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .workflow-heading > div > strong {
        overflow: hidden;
        font-size: 0.78rem;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .workflow-heading__icon {
        display: grid;
        width: 32px;
        height: 32px;
        flex: 0 0 32px;
        place-items: center;
        border: 1px solid currentColor;
        border-radius: 4px;
    }

    .workflow-heading__icon--analyze {
        background: rgba(23, 150, 165, 0.1);
        color: #158393;
    }

    .workflow-heading__icon--publish {
        background: rgba(220, 140, 25, 0.11);
        color: #c47a12;
    }

    .state-list {
        display: grid;
        margin-top: 0.65rem;
        gap: 0.3rem;
    }

    .state-row {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        align-items: center;
        min-height: 30px;
        padding: 0.25rem 0.45rem;
        gap: 0.45rem;
        border: 1px solid rgba(var(--v-theme-outline), 0.14);
        border-radius: 3px;
        background: rgba(var(--v-theme-surface-variant), 0.16);
        color: rgba(var(--v-theme-on-surface), 0.68);
        font-size: 0.7rem;
    }

    .state-row:hover {
        border-color: rgba(var(--v-theme-primary), 0.3);
        background: rgba(var(--v-theme-primary), 0.06);
    }

    .state-row span {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .state-row strong {
        min-width: 1.4rem;
        padding-left: 0.4rem;
        border-left: 1px solid rgba(var(--v-theme-outline), 0.16);
        color: rgb(var(--v-theme-on-surface));
        text-align: right;
    }

    .workflow-divider {
        width: 1px;
        height: auto;
        margin-block: 0.8rem;
        margin-inline: 0;
        background: var(--review-list-border);
    }

    .dashboard-system {
        display: grid;
        grid-template-columns: auto repeat(2, minmax(0, 1fr));
        align-items: center;
        min-height: 48px;
        margin-top: 0.7rem;
        padding: 0.5rem 0.75rem;
        border-radius: 4px;
    }

    .dashboard-system__title,
    .dashboard-system__item {
        min-width: 0;
        min-height: 30px;
        padding-inline: 0.7rem;
        gap: 0.35rem;
        border-right: 1px solid var(--review-list-border);
        font-size: 0.7rem;
    }

    .dashboard-system__title {
        padding-left: 0;
        color: rgb(var(--v-theme-primary));
    }

    .dashboard-system__item:last-child {
        border-right: 0;
    }

    .dashboard-system__item span,
    .dashboard-system__item small {
        overflow: hidden;
        color: rgba(var(--v-theme-on-surface), 0.55);
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .dashboard-system__item strong {
        flex: 0 0 auto;
    }

    @media (max-width: 1100px) {
        .dashboard-metrics {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .metric-card--news {
            grid-column: 1 / -1;
        }

        .dashboard-grid {
            grid-template-columns: 1fr;
        }

        .dashboard-rail {
            display: grid;
            grid-template-columns: minmax(260px, 0.7fr) minmax(0, 1.3fr);
            position: static;
        }

        .workflow-card {
            grid-template-columns: 1fr auto 1fr;
        }

        .workflow-divider {
            width: 1px;
            height: auto;
            margin-block: 0.8rem;
            margin-inline: 0;
        }
    }

    @media (max-width: 760px) {
        .dashboard-page {
            padding: 0.45rem;
        }

        .dashboard-hero {
            align-items: flex-start;
            flex-direction: column;
            gap: 0.65rem;
        }

        .dashboard-hero__activity {
            width: 100%;
            justify-content: space-between;
        }

        .dashboard-hero__freshness {
            white-space: normal;
        }

        .dashboard-cloud .dashboard-card__header {
            align-items: flex-start;
            flex-direction: column;
        }

        .dashboard-cloud__header-actions {
            width: 100%;
        }

        .dashboard-cloud__period-control {
            flex: 1 1 auto;
            justify-content: flex-start;
            flex-wrap: wrap;
        }

        .dashboard-cloud__range-fields {
            grid-template-columns: 1fr;
        }

        .dashboard-rail,
        .workflow-card {
            display: grid;
            grid-template-columns: 1fr;
        }

        .workflow-divider {
            width: auto;
            height: 1px;
            margin-block: 0;
            margin-inline: 0.9rem;
        }

        .dashboard-system {
            grid-template-columns: 1fr;
        }

        .dashboard-system__title,
        .dashboard-system__item {
            border-right: 0;
            border-bottom: 1px solid var(--review-list-border);
        }

        .dashboard-system__item:last-child {
            border-bottom: 0;
        }
    }

    @media (max-width: 480px) {
        .dashboard-metrics {
            grid-template-columns: 1fr;
        }

        .metric-card--news {
            grid-column: auto;
            grid-template-columns: 1fr;
        }

        .news-ingestion {
            padding-top: 0.55rem;
            padding-left: 0;
            border-top: 1px solid var(--review-list-border);
            border-left: 0;
        }
    }
</style>
