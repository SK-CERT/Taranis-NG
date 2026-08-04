import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AssessView from '@/views/users/AssessView.vue'

const authState = vi.hoisted(() => ({
    allowed: true,
    checkPermission: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: authState.checkPermission })
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

vi.mock('@/api/assess', async () => {
    const actual = await vi.importActual('@/api/assess')
    return {
        ...actual,
        getManualOSINTSources: vi.fn().mockResolvedValue({
            data: [
                { id: 'manual-1', name: 'First source' },
                { id: 'manual-42', name: 'Bookmarked source' }
            ]
        })
    }
})

const AddNewsItemDialogStub = {
    name: 'AddNewsItemDialog',
    props: ['modelValue', 'manualSources', 'initialSourceId'],
    template: '<div class="add-news-item-dialog" />'
}

const ContentDataAssessStub = {
    name: 'ContentDataAssess',
    methods: { updateData: vi.fn() },
    template: '<div />'
}

async function mountLegacyEntry() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: '/assess/group/:groupId', name: 'assess', component: AssessView }]
    })
    await router.push('/assess/group/all?manualSource=manual-42')
    await router.isReady()

    const wrapper = mountWithPlugins(AssessView, {
        global: {
            plugins: [router],
            stubs: {
                ViewLayout: { template: '<div><slot name="panel" /><slot name="content" /></div>' },
                ToolbarFilterAssess: { template: '<div><slot name="addbutton" /></div>' },
                ContentDataAssess: ContentDataAssessStub,
                AddNewsItemDialog: AddNewsItemDialogStub,
                AddNewButton: true,
                NewReportItem: true
            }
        }
    })
    await flushPromises()

    return { router, wrapper }
}

describe('legacy manual-entry route', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        authState.allowed = true
        authState.checkPermission.mockImplementation(() => authState.allowed)
    })

    it('opens manual entry with the requested source and canonicalizes the URL', async () => {
        const { router, wrapper } = await mountLegacyEntry()
        const dialog = wrapper.findComponent({ name: 'AddNewsItemDialog' })

        expect(dialog.props('modelValue')).toBe(true)
        expect(dialog.props('initialSourceId')).toBe('manual-42')
        expect(router.currentRoute.value.fullPath).toBe('/assess/group/all')
    })

    it('does not load sources or open manual entry without ASSESS_CREATE', async () => {
        authState.allowed = false
        const assessApi = await import('@/api/assess')
        const { router, wrapper } = await mountLegacyEntry()

        expect(assessApi.getManualOSINTSources).not.toHaveBeenCalled()
        expect(wrapper.findComponent({ name: 'AddNewsItemDialog' }).exists()).toBe(false)
        expect(router.currentRoute.value.fullPath).toBe('/assess/group/all')
    })
})
