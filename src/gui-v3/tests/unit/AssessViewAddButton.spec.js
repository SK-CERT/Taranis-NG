import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createTestI18n } from '../helpers/mount-helpers'
import AssessView from '@/views/users/AssessView.vue'

/**
 * Assess offers exactly one "Add New", in the toolbar, and it adds a news item. The report-item
 * dialog the view also hosts is opened from the news-item selection, never by a button - but it
 * renders one by default, which put a second, unrelated "Add New" at the foot of the screen.
 */

// vi.mock is hoisted above module-level consts, so the fixture is declared with it.
const { manualSources } = vi.hoisted(() => ({ manualSources: [{ id: 'src-1', name: 'Manual source' }] }))

vi.mock('@/api/assess', () => ({
    getManualOSINTSources: vi.fn().mockResolvedValue({ data: manualSources }),
    getNewsItemsByGroup: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
    voteNewsItemAggregate: vi.fn(),
    readNewsItemAggregate: vi.fn(),
    importantNewsItemAggregate: vi.fn(),
    deleteNewsItemAggregate: vi.fn(),
    saveNewsItemAggregate: vi.fn(),
    deleteNewsItem: vi.fn(),
    groupAction: vi.fn(),
    importantNewsItem: vi.fn(),
    readNewsItem: vi.fn(),
    voteNewsItem: vi.fn(),
    selectAllNewsItems: vi.fn()
}))

// The toolbar button is permission-gated; without this the view renders no button at all and
// the count below would pass for the wrong reason.
vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/composables/useKeyboard', () => ({
    default: () => ({
        onInit: vi.fn(),
        keyAction: vi.fn(),
        reindexCardItems: vi.fn(),
        setDetailDialogCloseCallback: vi.fn(),
        setReloadCallback: vi.fn()
    })
}))

const vuetify = createVuetify({ components, directives })

// Rendered rather than stubbed, so the button each one would actually draw is counted.
const AddNewButtonStub = {
    name: 'AddNewButton',
    props: ['show', 'label'],
    template: '<button v-if="show !== false" class="add-new-button">Add New</button>'
}

// showButton mirrors the real component's default of true - that default is the whole reason a
// second button appeared, so a stub that defaulted to false would hide the defect under test.
const NewReportItemStub = {
    name: 'NewReportItem',
    props: {
        showButton: { type: Boolean, default: true },
        readOnly: { type: Boolean, default: false }
    },
    template: '<div class="new-report-item"><button v-if="showButton" class="add-new-button">Add New</button></div>'
}

// The view calls updateData() on this ref when the route settles; the auto-stub has no such
// method and the rejection would surface as an unhandled error.
const ContentDataAssessStub = {
    name: 'ContentDataAssess',
    methods: { updateData: () => {} },
    template: '<div class="content-data" />'
}

const AddNewsItemDialogStub = {
    name: 'AddNewsItemDialog',
    props: ['modelValue', 'manualSources', 'initialSourceId'],
    template: '<div><slot name="activator" :props="{}" /></div>'
}

const ToolbarFilterAssessStub = {
    name: 'ToolbarFilterAssess',
    template: '<div class="toolbar"><slot name="addbutton" /></div>'
}

const mountAssessView = async () => {
    const pinia = createPinia()
    setActivePinia(pinia)

    const router = createRouter({
        history: createMemoryHistory(),
        routes: [
            { path: '/', component: { template: '<div />' } },
            { path: '/assess/group/:groupId', name: 'assess', component: AssessView }
        ]
    })
    router.push('/assess/group/group-a')
    await router.isReady()

    const wrapper = mount(
        { template: '<router-view />' },
        {
            global: {
                plugins: [vuetify, createTestI18n(), pinia, router],
                stubs: {
                    ViewLayout: { template: '<div><slot name="panel" /><slot name="content" /></div>' },
                    ToolbarFilterAssess: ToolbarFilterAssessStub,
                    ContentDataAssess: ContentDataAssessStub,
                    AddNewsItemDialog: AddNewsItemDialogStub,
                    AddNewButton: AddNewButtonStub,
                    NewReportItem: NewReportItemStub
                }
            }
        }
    )
    await flushPromises()
    return wrapper
}

describe('AssessView add button', () => {
    beforeEach(() => vi.clearAllMocks())

    it('draws exactly one add button, in the toolbar', async () => {
        const wrapper = await mountAssessView()

        expect(wrapper.findAll('.add-new-button')).toHaveLength(1)
        expect(wrapper.find('.toolbar .add-new-button').exists()).toBe(true)
    })

    it('does not let the report-item dialog contribute one of its own', async () => {
        const wrapper = await mountAssessView()

        expect(wrapper.findComponent({ name: 'NewReportItem' }).props('showButton')).toBe(false)
        expect(wrapper.find('.new-report-item .add-new-button').exists()).toBe(false)
    })
})
