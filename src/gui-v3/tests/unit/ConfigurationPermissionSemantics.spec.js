import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NodeDialog from '@/components/common/nodes/NodeDialog.vue'
import CardCompact from '@/components/common/CardCompact.vue'
import EditableEntityTable from '@/components/common/EditableEntityTable.vue'

const sourceRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../../src')

const { allowedPermissions } = vi.hoisted(() => ({ allowedPermissions: new Set() }))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: (permission) => allowedPermissions.has(permission) })
}))

vi.mock('@/api/config', () => ({
    createNewCollectorsNode: vi.fn(),
    updateCollectorsNode: vi.fn(),
    deleteCollectorsNode: vi.fn(),
    createNewPresentersNode: vi.fn(),
    updatePresentersNode: vi.fn(),
    deletePresentersNode: vi.fn(),
    createNewPublishersNode: vi.fn(),
    updatePublishersNode: vi.fn(),
    deletePublishersNode: vi.fn(),
    createNewBotsNode: vi.fn(),
    updateBotsNode: vi.fn(),
    deleteBotsNode: vi.fn()
}))

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div><slot /><slot name="activator" :props="{}" /></div>'
}

const VFormStub = {
    name: 'VForm',
    props: ['disabled'],
    methods: { validate: vi.fn().mockResolvedValue({ valid: true }), resetValidation: vi.fn() },
    template: '<form><slot /></form>'
}

const DialogToolbarStub = {
    name: 'DialogToolbar',
    props: ['showSave'],
    emits: ['cancel', 'save'],
    template: '<div class="dialog-toolbar" />'
}

const AddNewButtonStub = {
    name: 'AddNewButton',
    props: { show: { type: Boolean, default: true } },
    template: '<button v-if="show" class="add-new" />'
}

const ActionButtonStub = {
    name: 'ActionButton',
    props: ['action'],
    emits: ['click'],
    template: '<button :data-action="action" @click="$emit(\'click\')" />'
}

const commonStubs = {
    VDialog: VDialogStub,
    VForm: VFormStub,
    DialogToolbar: DialogToolbarStub,
    AddNewButton: AddNewButtonStub,
    UnsavedChangesDialog: true,
    ActionButton: ActionButtonStub,
    ConfirmationDialog: true,
    HighlightedText: true
}

const mountNodeDialog = (editItem = null) =>
    mountWithPlugins(NodeDialog, {
        props: { type: 'collectors', editItem },
        global: { stubs: commonStubs }
    })

describe('configuration create/update/delete roles', () => {
    beforeEach(() => allowedPermissions.clear())

    it('keeps create-only users out of existing-record editing', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_CREATE')
        const createDialog = mountNodeDialog()
        expect(createDialog.find('.add-new').exists()).toBe(true)

        const detail = mountNodeDialog({ id: 'node-1', name: 'Node 1' })
        await flushPromises()
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(false)
        expect(detail.findComponent(VFormStub).props('disabled')).toBe(true)
    })

    it('gives access-only users a genuine read-only detail view', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_ACCESS')
        const detail = mountNodeDialog({ id: 'node-1', name: 'Node 1' })
        await flushPromises()

        expect(detail.find('.add-new').exists()).toBe(false)
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(false)
        expect(detail.findComponent(VFormStub).props('disabled')).toBe(true)
    })

    it('allows update without implying delete', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_UPDATE')
        const detail = mountNodeDialog({ id: 'node-1', name: 'Node 1' })
        await flushPromises()
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(true)
        expect(detail.findComponent(VFormStub).props('disabled')).toBe(false)

        const card = mountWithPlugins(CardCompact, {
            props: { card: { id: 'node-1', name: 'Node 1' }, deletePermission: 'CONFIG_COLLECTORS_NODE_DELETE' },
            global: { stubs: commonStubs }
        })
        expect(card.find('[data-action="delete"]').exists()).toBe(false)
    })

    it('enables create, update, and delete for a full-access role', async () => {
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_CREATE')
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_UPDATE')
        allowedPermissions.add('CONFIG_COLLECTORS_NODE_DELETE')
        expect(mountNodeDialog().find('.add-new').exists()).toBe(true)

        const detail = mountNodeDialog({ id: 'node-1', name: 'Node 1' })
        await flushPromises()
        expect(detail.findComponent(DialogToolbarStub).props('showSave')).toBe(true)

        const card = mountWithPlugins(CardCompact, {
            props: { card: { id: 'node-1', name: 'Node 1' }, deletePermission: 'CONFIG_COLLECTORS_NODE_DELETE' },
            global: { stubs: commonStubs }
        })
        expect(card.find('[data-action="delete"]').exists()).toBe(true)
    })
})

describe('fine-grained nested row actions', () => {
    const mountTable = (props = {}) =>
        mountWithPlugins(EditableEntityTable, {
            props: {
                title: 'Constants',
                headers: [
                    { title: 'Value', key: 'value' },
                    { title: 'Actions', key: 'actions' }
                ],
                defaultItem: () => ({ value: '' }),
                addTitle: 'Add',
                editTitle: 'Edit',
                items: [{ value: 'CVE-1' }],
                server: true,
                ...props
            },
            global: { stubs: commonStubs }
        })

    it('does not infer delete from update permission', () => {
        const wrapper = mountTable({ allowAdd: true, allowEdit: true, allowDelete: false })

        expect(wrapper.vm.canAdd).toBe(true)
        expect(wrapper.vm.canEdit).toBe(true)
        expect(wrapper.vm.canDelete).toBe(false)
    })

    it('suppresses every mutation when the parent detail is read-only', () => {
        const wrapper = mountTable({ disabled: true })

        expect(wrapper.vm.canAdd).toBe(false)
        expect(wrapper.vm.canEdit).toBe(false)
        expect(wrapper.vm.canDelete).toBe(false)
    })
})

describe('configuration permission coverage matrix', () => {
    const editorMatrix = [
        ['components/config/access-management/NewOrganization.vue', 'CONFIG_ORGANIZATION_CREATE', 'CONFIG_ORGANIZATION_UPDATE'],
        ['components/config/access-management/NewUser.vue', 'CONFIG_USER_CREATE', 'CONFIG_USER_UPDATE'],
        ['components/config/access-management/NewRole.vue', 'CONFIG_ROLE_CREATE', 'CONFIG_ROLE_UPDATE'],
        ['components/config/access-management/NewACL.vue', 'CONFIG_ACL_CREATE', 'CONFIG_ACL_UPDATE'],
        ['components/config/remote/NewRemoteAccess.vue', 'CONFIG_REMOTE_ACCESS_CREATE', 'CONFIG_REMOTE_ACCESS_UPDATE'],
        ['components/config/remote/NewRemoteNode.vue', 'CONFIG_REMOTE_NODE_CREATE', 'CONFIG_REMOTE_NODE_UPDATE'],
        ['components/config/reports/NewAttribute.vue', 'CONFIG_ATTRIBUTE_CREATE', 'CONFIG_ATTRIBUTE_UPDATE'],
        ['components/config/reports/NewReportType.vue', 'CONFIG_REPORT_TYPE_CREATE', 'CONFIG_REPORT_TYPE_UPDATE'],
        ['components/config/word-lists/NewWordList.vue', 'CONFIG_WORD_LIST_CREATE', 'CONFIG_WORD_LIST_UPDATE'],
        ['components/config/collectors/NewOSINTSourceGroup.vue', 'CONFIG_OSINT_SOURCE_GROUP_CREATE', 'CONFIG_OSINT_SOURCE_GROUP_UPDATE'],
        ['components/config/collectors/NewOSINTSource.vue', 'CONFIG_OSINT_SOURCE_CREATE', 'CONFIG_OSINT_SOURCE_UPDATE'],
        ['components/config/publishers/NewPublisherPreset.vue', 'CONFIG_PUBLISHER_PRESET_CREATE', 'CONFIG_PUBLISHER_PRESET_UPDATE'],
        ['components/config/bots/NewBotPreset.vue', 'CONFIG_BOT_PRESET_CREATE', 'CONFIG_BOT_PRESET_UPDATE'],
        ['components/config/presenters/NewProductType.vue', 'CONFIG_PRODUCT_TYPE_CREATE', 'CONFIG_PRODUCT_TYPE_UPDATE']
    ]

    it.each(editorMatrix)('%s explicitly gates create and update', (relativePath, createPermission, updatePermission) => {
        const source = readFileSync(resolve(sourceRoot, relativePath), 'utf8')
        expect(source).toContain(createPermission)
        expect(source).toContain(updatePermission)
        expect(source).toContain(':show-save="canSave"')
        expect(source).toContain('if (!canSave.value) return false')
    })

    const tabDeleteMatrix = [
        ['components/config/access-management/OrganizationsTab.vue', 'CONFIG_ORGANIZATION_DELETE'],
        ['components/config/access-management/UsersTab.vue', 'CONFIG_USER_DELETE'],
        ['components/config/access-management/RolesTab.vue', 'CONFIG_ROLE_DELETE'],
        ['components/config/access-management/ACLTab.vue', 'CONFIG_ACL_DELETE'],
        ['components/config/reports/AttributesTab.vue', 'CONFIG_ATTRIBUTE_DELETE']
    ]

    it.each(tabDeleteMatrix)('%s explicitly gates row deletion', (relativePath, deletePermission) => {
        const source = readFileSync(resolve(sourceRoot, relativePath), 'utf8')
        expect(source).toContain(deletePermission)
        expect(source).toContain('v-if="canDelete"')
        expect(source).toContain('if (!canDelete.value) return')
    })

    const compactDeleteMatrix = [
        ['views/admin/RemoteNodesView.vue', 'CONFIG_REMOTE_NODE_DELETE'],
        ['views/admin/RemoteAccessesView.vue', 'CONFIG_REMOTE_ACCESS_DELETE'],
        ['views/admin/ReportTypesView.vue', 'CONFIG_REPORT_TYPE_DELETE'],
        ['views/admin/WordListsView.vue', 'CONFIG_WORD_LIST_DELETE'],
        ['views/admin/OSINTSourceGroupsView.vue', 'CONFIG_OSINT_SOURCE_GROUP_DELETE'],
        ['views/admin/PublisherPresetsView.vue', 'CONFIG_PUBLISHER_PRESET_DELETE'],
        ['views/admin/BotPresetsView.vue', 'CONFIG_BOT_PRESET_DELETE'],
        ['views/admin/ProductTypesView.vue', 'CONFIG_PRODUCT_TYPE_DELETE'],
        ['components/config/collectors/OSINTSourceBulkList.vue', 'CONFIG_OSINT_SOURCE_DELETE']
    ]

    it.each(compactDeleteMatrix)('%s supplies its delete permission to compact rows', (relativePath, deletePermission) => {
        const source = readFileSync(resolve(sourceRoot, relativePath), 'utf8')
        expect(source).toContain(deletePermission)
    })

    it('keeps global settings read-only without CONFIG_SETTINGS_UPDATE', () => {
        const source = readFileSync(resolve(sourceRoot, 'components/config/SettingsTable.vue'), 'utf8')
        expect(source).toContain('CONFIG_SETTINGS_UPDATE')
        expect(source).toContain(':disabled="!canEditSettings"')
        expect(source).toContain('if (!canEditSettings.value) return')
    })

    it('uses the registered remote-node permissions on every backend operation', () => {
        const source = readFileSync(resolve(sourceRoot, '../../core/api/config.py'), 'utf8')
        const remoteNodeSection = source.slice(source.indexOf('class RemoteNodesResource'), source.indexOf('class PresentersNodesResource'))

        expect(remoteNodeSection).toContain('@auth_required("CONFIG_REMOTE_NODE_ACCESS")')
        expect(remoteNodeSection).toContain('@auth_required("CONFIG_REMOTE_NODE_CREATE")')
        expect(remoteNodeSection).toContain('@auth_required("CONFIG_REMOTE_NODE_UPDATE")')
        expect(remoteNodeSection).toContain('@auth_required("CONFIG_REMOTE_NODE_DELETE")')
        expect(remoteNodeSection).not.toContain('CONFIG_REMOTE_ACCESS_')
    })
})
