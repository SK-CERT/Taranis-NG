import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readFileSync } from 'node:fs'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewDataProvider from '@/components/config/data-providers/NewDataProvider.vue'
import NewAiProvider from '@/components/config/data-providers/NewAiProvider.vue'
import StatesTab from '@/components/config/workflow/StatesTab.vue'
import StateWorkflowTab from '@/components/config/workflow/StateWorkflowTab.vue'

const { allowedPermissions, api, configStore } = vi.hoisted(() => ({
    allowedPermissions: new Set(),
    api: {
        createNewDataProvider: vi.fn(),
        updateDataProvider: vi.fn(),
        createNewAiProvider: vi.fn(),
        updateAiProvider: vi.fn(),
        createNewStateDefinition: vi.fn(),
        updateStateDefinition: vi.fn(),
        deleteStateDefinition: vi.fn(),
        createNewStateEntityType: vi.fn(),
        updateStateEntityType: vi.fn(),
        deleteStateEntityType: vi.fn()
    },
    configStore: {
        stateDefinitions: { items: [] },
        stateEntityTypes: { items: [] },
        loadStateDefinitions: vi.fn().mockResolvedValue(undefined),
        loadStateEntityTypes: vi.fn().mockResolvedValue(undefined)
    }
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => allowedPermissions.has(permission) })
}))

vi.mock('@/api/config', () => api)
vi.mock('@/stores/config', () => ({ useConfigStore: () => configStore }))

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div><slot /><slot name="activator" :props="{}" /></div>'
}

const VFormStub = {
    name: 'VForm',
    props: ['disabled'],
    methods: { validate: vi.fn().mockResolvedValue({ valid: true }), reset: vi.fn() },
    template: '<form><slot /></form>'
}

const DialogToolbarStub = {
    name: 'DialogToolbar',
    props: ['showSave'],
    emits: ['save', 'cancel'],
    template: '<div class="dialog-toolbar" />'
}

const AddNewButtonStub = {
    name: 'AddNewButton',
    props: { show: { type: Boolean, default: true } },
    emits: ['click'],
    template: '<button v-if="show" class="add-new" @click="$emit(\'click\')" />'
}

const commonStubs = {
    VDialog: VDialogStub,
    VForm: VFormStub,
    DialogToolbar: DialogToolbarStub,
    AddNewButton: AddNewButtonStub,
    UnsavedChangesDialog: true,
    ConfirmationDialog: true,
    SearchField: true
}

const dataProvider = {
    id: 7,
    name: 'EUVD',
    api_type: 'EUVD',
    api_url: 'https://example.test',
    api_key: '',
    user_agent: '',
    web_url: ''
}

const aiProvider = {
    id: 8,
    name: 'AI',
    api_type: 'openai',
    api_url: 'https://example.test',
    api_key: 'secret',
    model: 'example'
}

const mountProvider = (component, editItem = null) =>
    mountWithPlugins(component, {
        props: { editItem },
        global: { stubs: commonStubs }
    })

describe('data and AI provider permission roles', () => {
    beforeEach(() => {
        allowedPermissions.clear()
        vi.clearAllMocks()
    })

    it.each([
        [NewDataProvider, dataProvider, 'CONFIG_DATA_PROVIDER_CREATE'],
        [NewAiProvider, aiProvider, 'CONFIG_AI_CREATE']
    ])('keeps create-only users out of existing %s editing', async (component, item, createPermission) => {
        allowedPermissions.add(createPermission)
        expect(mountProvider(component).find('.add-new').exists()).toBe(true)

        const detail = mountProvider(component, item)
        await flushPromises()
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(false)
        expect(detail.findComponent(VFormStub).props('disabled')).toBe(true)
    })

    it.each([
        [NewDataProvider, dataProvider, 'CONFIG_DATA_PROVIDER_UPDATE'],
        [NewAiProvider, aiProvider, 'CONFIG_AI_UPDATE']
    ])('allows update independently for %s', async (component, item, updatePermission) => {
        allowedPermissions.add(updatePermission)
        const detail = mountProvider(component, item)
        await flushPromises()

        expect(detail.find('.add-new').exists()).toBe(false)
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(true)
        expect(detail.findComponent(VFormStub).props('disabled')).toBe(false)
    })

    it('rejects a direct provider save without update permission', async () => {
        const detail = mountProvider(NewDataProvider, dataProvider)
        await flushPromises()

        expect(await detail.vm.persist()).toBe(false)
        expect(api.updateDataProvider).not.toHaveBeenCalled()
    })
})

describe('workflow permission roles', () => {
    const state = {
        id: 1,
        display_name: 'Draft',
        description: '',
        color: '#2196F3',
        icon: 'mdi-circle',
        editable: true
    }
    const association = {
        id: 2,
        entity_type: 'report_item',
        state_id: 1,
        state_type: 'normal',
        is_active: true,
        editable: true,
        sort_order: 0,
        state
    }

    beforeEach(() => {
        allowedPermissions.clear()
        vi.clearAllMocks()
        configStore.stateDefinitions.items = [state]
        configStore.stateEntityTypes.items = [association]
    })

    it.each([
        [StatesTab, state],
        [StateWorkflowTab, association]
    ])('opens existing %s records read-only without update', async (component, item) => {
        allowedPermissions.add('CONFIG_WORKFLOW_ACCESS')
        const wrapper = mountWithPlugins(component, { global: { stubs: commonStubs } })
        wrapper.vm.editItem(item)
        await flushPromises()

        expect(wrapper.vm.canSave).toBe(false)
        expect(wrapper.findComponent(DialogToolbarStub).props('showSave')).toBe(false)
        expect(wrapper.findComponent(VFormStub).props('disabled')).toBe(true)
    })

    it.each([
        [StatesTab, state],
        [StateWorkflowTab, association]
    ])('allows workflow update without implying delete for %s', async (component, item) => {
        allowedPermissions.add('CONFIG_WORKFLOW_UPDATE')
        const wrapper = mountWithPlugins(component, { global: { stubs: commonStubs } })
        wrapper.vm.editItem(item)
        await flushPromises()

        expect(wrapper.vm.canSave).toBe(true)
        expect(wrapper.vm.canDelete).toBe(false)
        wrapper.vm.deleteItem(item)
        expect(wrapper.vm.dialogDelete).toBe(false)
    })

    it('enables workflow create, update, and delete for full access', async () => {
        for (const permission of ['CONFIG_WORKFLOW_CREATE', 'CONFIG_WORKFLOW_UPDATE', 'CONFIG_WORKFLOW_DELETE']) {
            allowedPermissions.add(permission)
        }
        const wrapper = mountWithPlugins(StatesTab, { global: { stubs: commonStubs } })

        expect(wrapper.find('.add-new').exists()).toBe(true)
        wrapper.vm.editItem(state)
        await flushPromises()
        expect(wrapper.vm.canSave).toBe(true)
        wrapper.vm.deleteItem(state)
        expect(wrapper.vm.dialogDelete).toBe(true)
    })
})

describe('inherited configuration permission coverage', () => {
    const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../src')
    const matrix = [
        ['components/config/data-providers/NewDataProvider.vue', 'CONFIG_DATA_PROVIDER_CREATE', 'CONFIG_DATA_PROVIDER_UPDATE'],
        ['components/config/data-providers/NewAiProvider.vue', 'CONFIG_AI_CREATE', 'CONFIG_AI_UPDATE'],
        ['components/config/workflow/StatesTab.vue', 'CONFIG_WORKFLOW_CREATE', 'CONFIG_WORKFLOW_UPDATE'],
        ['components/config/workflow/StateWorkflowTab.vue', 'CONFIG_WORKFLOW_CREATE', 'CONFIG_WORKFLOW_UPDATE']
    ]

    it.each(matrix)('%s has independent create/update persistence gates', (relativePath, createPermission, updatePermission) => {
        const source = readFileSync(resolve(sourceRoot, relativePath), 'utf8')
        expect(source).toContain(createPermission)
        expect(source).toContain(updatePermission)
        expect(source).toContain(':show-save="canSave"')
        expect(source).toContain('if (!canSave.value) return false')
    })

    const deletionMatrix = [
        ['components/config/data-providers/DataProvidersTab.vue', 'CONFIG_DATA_PROVIDER_DELETE'],
        ['components/config/data-providers/AiProvidersTab.vue', 'CONFIG_AI_DELETE'],
        ['components/config/workflow/StatesTab.vue', 'CONFIG_WORKFLOW_DELETE'],
        ['components/config/workflow/StateWorkflowTab.vue', 'CONFIG_WORKFLOW_DELETE']
    ]

    it.each(deletionMatrix)('%s gates row deletion', (relativePath, deletePermission) => {
        const source = readFileSync(resolve(sourceRoot, relativePath), 'utf8')
        expect(source).toContain(deletePermission)
        expect(source).toContain('v-if="canDelete"')
        expect(source).toContain('if (!canDelete.value')
    })
})
