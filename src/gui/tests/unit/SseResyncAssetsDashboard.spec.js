import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ContentDataAssets from '@/components/assets/ContentDataAssets.vue'
import MyAssetsNav from '@/views/nav/MyAssetsNav.vue'
import DashboardView from '@/views/users/DashboardView.vue'
import en from '@/i18n/en.json'
import gitMeta from '../../git-info.json'

const mocks = vi.hoisted(() => ({
    route: { path: '/myassets/group/3', params: { groupId: '3' } },
    router: { push: vi.fn(), replace: vi.fn() },
    assetsStore: {
        assetGroups: { total_count: 1, items: [{ id: 3, name: 'Servers' }] },
        assets: { total_count: 1, items: [{ id: 8, name: 'host.example' }] },
        loadAssetGroups: vi.fn().mockResolvedValue({}),
        loadAssets: vi.fn().mockResolvedValue({}),
        clearAssets: vi.fn()
    },
    dashboardStore: {
        dashboard_data: {
            total_news_items: 1,
            total_products: 2,
            total_report_items: 3,
            total_database_items: 4,
            latest_collected: '',
            news_items_by_day: [],
            tag_cloud: [],
            report_item_states: {},
            product_states: {}
        },
        loadDashboardData: vi.fn().mockResolvedValue(undefined)
    }
}))

vi.mock('vue-router', () => ({
    useRoute: () => mocks.route,
    useRouter: () => mocks.router
}))

vi.mock('@/stores/assets', () => ({ useAssetsStore: () => mocks.assetsStore }))
vi.mock('@/stores/dashboard', () => ({ useDashboardStore: () => mocks.dashboardStore }))
vi.mock('@/api/assets', () => ({ deleteAsset: vi.fn() }))
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ checkPermission: () => true }) }))

const stubs = {
    CardAsset: { template: '<div class="asset-card-stub" />' },
    GroupNavList: { template: '<div class="group-nav-stub" />' },
    WordCloud: { template: '<div class="word-cloud-stub" />' },
    VDialog: {
        props: ['modelValue'],
        template: '<div v-if="modelValue" class="dialog-stub"><slot /></div>'
    }
}

const createDashboardI18n = () =>
    createI18n({
        legacy: false,
        locale: 'de-DE',
        fallbackLocale: 'en',
        // The de-DE catalogue below is deliberately partial — the dashboard's other
        // keys are meant to fall back to `en`, which is what these specs assert. Left
        // on, vue-i18n warns twice for each of those keys on every render.
        missingWarn: false,
        fallbackWarn: false,
        messages: {
            en,
            'de-DE': {
                nav_menu: {
                    newsitems: 'Nachrichten',
                    report_items: 'Berichte',
                    products: 'Produkte'
                },
                toolbar_filter: { last_7_days: 'die letzten 7 Tage' },
                dashboard: {
                    metrics: {
                        news_items_summary: 'Keine Nachrichten | {count} Nachricht | {count} Nachrichten',
                        report_items_summary: 'Keine Berichte | {count} Bericht | {count} Berichte',
                        products_summary: 'Keine Produkte | {count} Produkt | {count} Produkte'
                    },
                    assess: {
                        total: 'insgesamt',
                        ingestion_chart: 'Nachrichteneingang für {period}',
                        ingestion_point: 'Am {date}: {count} Nachricht | Am {date}: {count} Nachrichten'
                    },
                    analyze: { total: 'insgesamt' },
                    publish: { total: 'insgesamt' },
                    about: {
                        built_at: 'Erstellt am {date}',
                        committed_at: 'Commit vom {date}'
                    }
                }
            }
        }
    })

const mountDashboardWithDirection = (rtl) =>
    mount(DashboardView, {
        global: {
            plugins: [
                createVuetify({
                    components,
                    directives,
                    locale: { locale: rtl ? 'ar' : 'en', rtl: { ar: true } }
                }),
                createDashboardI18n()
            ],
            stubs: { ...stubs, 'router-link': true }
        }
    })

describe('SSE resynchronization for Assets and Dashboard', () => {
    beforeEach(() => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date(2026, 7, 6, 12, 0, 0))
        vi.clearAllMocks()
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('refreshes the active asset group and asset-group navigation once per signal burst', async () => {
        const content = mountWithPlugins(ContentDataAssets, { global: { stubs } })
        const navigation = mountWithPlugins(MyAssetsNav, { global: { stubs } })

        try {
            await flushPromises()
            vi.clearAllMocks()

            for (let i = 0; i < 6; i++) window.dispatchEvent(new CustomEvent('sse-resync'))
            await vi.advanceTimersByTimeAsync(100)
            await flushPromises()

            expect(mocks.assetsStore.loadAssets).toHaveBeenCalledTimes(1)
            expect(mocks.assetsStore.loadAssets).toHaveBeenCalledWith({
                group_id: '3',
                filter: { search: '', vulnerable: false, sort: 'ALPHABETICAL' }
            })
            expect(mocks.assetsStore.loadAssetGroups).toHaveBeenCalledTimes(1)
            expect(mocks.assetsStore.clearAssets).not.toHaveBeenCalled()
        } finally {
            content.unmount()
            navigation.unmount()
        }
    })

    it('refreshes Dashboard after a missed-event signal and coalesces bursts', async () => {
        const wrapper = mountWithPlugins(DashboardView, { global: { stubs } })

        try {
            await flushPromises()
            mocks.dashboardStore.loadDashboardData.mockClear()

            window.dispatchEvent(new CustomEvent('sse-resync'))
            window.dispatchEvent(new CustomEvent('sse-resync'))
            await vi.advanceTimersByTimeAsync(100)
            await flushPromises()

            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenCalledTimes(1)
        } finally {
            wrapper.unmount()
        }
    })

    it('loads the selected tag-cloud interval and excludes today from custom dates', async () => {
        const wrapper = mountWithPlugins(DashboardView, { global: { stubs } })

        try {
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({ range: 'LAST_7_DAYS' })

            const button = (label) => wrapper.findAll('button').find((candidate) => candidate.text().trim() === label)

            await button('Today').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({ range: 'TODAY' })

            await button('yesterday').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({
                dateFrom: '2026-08-05',
                dateTo: '2026-08-05'
            })

            await button('Custom Filter').trigger('click')
            await flushPromises()
            const dateInputs = wrapper.findAll('input[type="date"]')
            expect(dateInputs).toHaveLength(2)
            expect(dateInputs[1].attributes('max')).toBe('2026-08-05')

            await dateInputs[0].setValue('2026-08-02')
            await dateInputs[1].setValue('2026-08-04')
            await button('Done').trigger('click')
            await flushPromises()
            expect(mocks.dashboardStore.loadDashboardData).toHaveBeenLastCalledWith({
                dateFrom: '2026-08-02',
                dateTo: '2026-08-04'
            })

            await button('Custom Filter').trigger('click')
            await flushPromises()
            expect(wrapper.findAll('input[type="date"]')).toHaveLength(2)
        } finally {
            wrapper.unmount()
        }
    })

    it('renders complete plural metric and chart messages with app-locale numbers', async () => {
        const previousData = mocks.dashboardStore.dashboard_data
        mocks.dashboardStore.dashboard_data = {
            ...previousData,
            total_news_items: 1,
            total_report_items: 0,
            total_products: 12000,
            news_items_by_day: [{ date: '2026-08-05', count: 12000 }]
        }
        const wrapper = mountWithPlugins(DashboardView, {
            global: { stubs, plugins: [createDashboardI18n()] }
        })

        try {
            await flushPromises()
            const metrics = wrapper.findAll('.metric-card__body')

            expect(metrics[0].text()).toContain('1 Nachricht')
            expect(metrics[1].text()).toContain('Keine Berichte')
            expect(metrics[2].text()).toContain('12.000 Produkte')
            expect(metrics[2].find('strong').text()).toBe('12.000')

            const chart = wrapper.find('.news-ingestion__chart')
            expect(chart.attributes('aria-label')).toBe('Nachrichteneingang für die letzten 7 Tage')
            expect(wrapper.find('.news-ingestion__column').attributes('title')).toContain('12.000 Nachrichten')
            expect(wrapper.find('.news-ingestion__column strong').text()).toBe('12.000')

            expect(wrapper.findAllComponents({ name: 'VCard' })[0].props('to')).toBe('/assess')
        } finally {
            wrapper.unmount()
            mocks.dashboardStore.dashboard_data = previousData
        }
    })

    it('formats build metadata in the app locale without code-owned parentheses', async () => {
        const wrapper = mountWithPlugins(DashboardView, {
            global: { stubs, plugins: [createDashboardI18n()] }
        })

        try {
            await flushPromises()
            const metadata = wrapper.findAll('.dashboard-system__item')
            const expectedBuildDate = new Intl.DateTimeFormat('de-DE', {
                dateStyle: 'medium',
                timeStyle: 'short'
            }).format(new Date(gitMeta.buildDate))
            const expectedCommitDate = new Intl.DateTimeFormat('de-DE', {
                dateStyle: 'medium',
                timeStyle: 'short'
            }).format(new Date(gitMeta.commitDate))

            expect(metadata[0].find('small').text()).toBe(`Erstellt am ${expectedBuildDate}`)
            expect(metadata[1].find('small').text()).toBe(`Commit vom ${expectedCommitDate} [${gitMeta.branchName}]`)
            expect(metadata[0].find('small').text()).not.toContain('(')
            expect(metadata[1].find('small').text()).not.toContain('(')
            expect(metadata[0].find('strong').text()).toBe(gitMeta.version)
            expect(metadata[1].find('strong').text()).toBe(gitMeta.commit)
            expect(metadata[0].get('bdi').attributes('dir')).toBe('auto')
            expect(metadata[1].findAll('bdi').map((value) => value.attributes('dir'))).toEqual(['auto', 'ltr'])
            expect(metadata[1].findAll('bdi')[1].text()).toBe(`[${gitMeta.branchName}]`)
        } finally {
            wrapper.unmount()
        }
    })

    it('preserves empty, invalid, and valid latest-collection date displays', async () => {
        const previousData = mocks.dashboardStore.dashboard_data
        let wrapper

        try {
            mocks.dashboardStore.dashboard_data = { ...previousData, latest_collected: '' }
            wrapper = mountWithPlugins(DashboardView, { global: { stubs } })
            await flushPromises()
            expect(wrapper.findAll('.dashboard-hero__freshness bdi, .collection-card__time bdi').map((value) => value.text())).toEqual([
                '—',
                '—'
            ])
            expect(
                wrapper.findAll('.dashboard-hero__freshness bdi, .collection-card__time bdi').map((value) => value.attributes('dir'))
            ).toEqual(['auto', 'auto'])
            wrapper.unmount()

            mocks.dashboardStore.dashboard_data = { ...previousData, latest_collected: 'وقت قديم' }
            wrapper = mountWithPlugins(DashboardView, { global: { stubs } })
            await flushPromises()
            expect(wrapper.find('.dashboard-hero__freshness bdi').text()).toBe('وقت قديم')
            expect(wrapper.find('.dashboard-hero__freshness bdi').attributes('dir')).toBe('auto')
            wrapper.unmount()

            const latestCollected = '2026-08-05T10:00:00Z'
            mocks.dashboardStore.dashboard_data = { ...previousData, latest_collected: latestCollected }
            wrapper = mountWithPlugins(DashboardView, { global: { stubs } })
            await flushPromises()
            wrapper.vm.$i18n.locale = 'ar'
            await wrapper.vm.$nextTick()
            const expectedDate = new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(latestCollected))
            expect(wrapper.find('.dashboard-hero__freshness bdi').text()).toBe(expectedDate)
            expect(wrapper.find('.dashboard-hero__freshness bdi').attributes('dir')).toBe('auto')
        } finally {
            wrapper?.unmount()
            mocks.dashboardStore.dashboard_data = previousData
        }
    })

    it('uses semantic forward icons for dashboard navigation in both directions', async () => {
        const rtlWrapper = mountDashboardWithDirection(true)

        try {
            await flushPromises()
            const rtlNavigationButtons = rtlWrapper
                .findAllComponents({ name: 'VBtn' })
                .filter((button) => ['/assess', '/analyze/local', '/publish'].includes(button.props('to')))

            expect(rtlNavigationButtons.map((button) => button.props('to'))).toEqual(['/assess', '/analyze/local', '/publish'])
            expect(rtlNavigationButtons.map((button) => button.props('icon'))).toEqual(['mdi-arrow-left', 'mdi-arrow-left', 'mdi-arrow-left'])
        } finally {
            rtlWrapper.unmount()
        }

        const ltrWrapper = mountDashboardWithDirection(false)
        try {
            await flushPromises()
            const ltrNavigationButtons = ltrWrapper
                .findAllComponents({ name: 'VBtn' })
                .filter((button) => ['/assess', '/analyze/local', '/publish'].includes(button.props('to')))

            expect(ltrNavigationButtons.map((button) => button.props('icon'))).toEqual([
                'mdi-arrow-right',
                'mdi-arrow-right',
                'mdi-arrow-right'
            ])
        } finally {
            ltrWrapper.unmount()
        }
    })
})
