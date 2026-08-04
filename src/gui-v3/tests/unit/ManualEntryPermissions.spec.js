import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AssessView from '@/views/users/AssessView.vue'
import AddNewsItemDialog from '@/components/assess/AddNewsItemDialog.vue'

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
        getManualOSINTSources: vi.fn().mockResolvedValue({ data: [{ id: 'manual-1', name: 'Manual source' }] }),
        addNewsItem: vi.fn().mockResolvedValue({})
    }
})

const ToolbarFilterAssessStub = {
    name: 'ToolbarFilterAssess',
    template: '<div><slot name="addbutton" /></div>'
}

const AddNewsItemDialogStub = {
    name: 'AddNewsItemDialog',
    props: ['modelValue', 'manualSources'],
    template: '<div class="add-news-item-dialog"><slot name="activator" :props="{}" /></div>'
}

const AddNewButtonStub = {
    name: 'AddNewButton',
    props: ['show'],
    template: '<button v-if="show" class="add-news-item-button" />'
}

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<div class="manual-entry-dialog"><slot /><slot name="activator" :props="{}" /></div>'
}

const VFormStub = {
    name: 'VForm',
    methods: {
        validate: vi.fn().mockResolvedValue({ valid: true }),
        reset: vi.fn()
    },
    template: '<form><slot /></form>'
}

const DialogToolbarStub = {
    name: 'DialogToolbar',
    emits: ['cancel', 'save'],
    template: '<button class="save-manual-entry" @click="$emit(\'save\')">save</button>'
}

async function mountAssessView() {
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: '/assess', component: AssessView }]
    })
    await router.push('/assess')
    await router.isReady()

    const wrapper = mountWithPlugins(AssessView, {
        global: {
            plugins: [router],
            stubs: {
                ViewLayout: { template: '<div><slot name="panel" /><slot name="content" /></div>' },
                ToolbarFilterAssess: ToolbarFilterAssessStub,
                ContentDataAssess: true,
                AddNewsItemDialog: AddNewsItemDialogStub,
                AddNewButton: AddNewButtonStub,
                NewReportItem: true
            }
        }
    })
    await flushPromises()
    return wrapper
}

function mountManualEntryDialog() {
    return mountWithPlugins(AddNewsItemDialog, {
        props: {
            modelValue: true,
            manualSources: [{ id: 'manual-1', name: 'Manual source' }]
        },
        global: {
            stubs: {
                VDialog: VDialogStub,
                VForm: VFormStub,
                DialogToolbar: DialogToolbarStub,
                Editor: true
            }
        }
    })
}

describe('manual news entry permissions', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        authState.allowed = true
        authState.checkPermission.mockImplementation(() => authState.allowed)
    })

    it('does not expose manual entry or load its sources without ASSESS_CREATE', async () => {
        authState.allowed = false
        const assessApi = await import('@/api/assess')
        const wrapper = await mountAssessView()

        expect(wrapper.findComponent({ name: 'AddNewsItemDialog' }).exists()).toBe(false)
        expect(wrapper.find('.add-news-item-button').exists()).toBe(false)
        expect(assessApi.getManualOSINTSources).not.toHaveBeenCalled()
    })

    it('shows manual entry when ASSESS_CREATE and a manual source are available', async () => {
        const assessApi = await import('@/api/assess')
        const wrapper = await mountAssessView()

        expect(assessApi.getManualOSINTSources).toHaveBeenCalledOnce()
        expect(wrapper.findComponent({ name: 'AddNewsItemDialog' }).exists()).toBe(true)
        expect(wrapper.find('.add-news-item-button').exists()).toBe(true)
    })

    it('does not render the dialog without ASSESS_CREATE', () => {
        authState.allowed = false
        const wrapper = mountManualEntryDialog()

        expect(wrapper.findComponent({ name: 'VDialog' }).exists()).toBe(false)
    })

    it('blocks submission if ASSESS_CREATE is lost after the dialog opens', async () => {
        const assessApi = await import('@/api/assess')
        const wrapper = mountManualEntryDialog()
        const toolbar = wrapper.findComponent({ name: 'DialogToolbar' })

        authState.allowed = false
        toolbar.vm.$emit('save')
        await flushPromises()

        expect(assessApi.addNewsItem).not.toHaveBeenCalled()
        expect(wrapper.emitted('update:modelValue')).toContainEqual([false])
    })
})
