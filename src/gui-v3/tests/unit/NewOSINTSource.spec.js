import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewOSINTSource from '@/components/config/collectors/NewOSINTSource.vue'

/**
 * Regression tests for the OSINT source update/create payload.
 *
 * Background: the backend's NewOSINTSourceSchema (src/core/model/osint_source.py)
 * extends OSINTSourceSchema (src/shared/shared/schema/osint_source.py), which
 * declares loadable fields last_attempted / last_collected / last_error_message.
 * Its @post_load does OSINTSource(**data), but the db Model's __init__ only
 * accepts id, name, description, collector_id, parameter_values, word_lists,
 * osint_source_groups. Sending any extra known field back crashes the server:
 *
 *   TypeError: __init__() got an unexpected keyword argument 'last_attempted'
 *
 * The dialog therefore opens with the full API record (which carries runtime
 * fields like last_attempted, last_collected, state, modified, nested collector),
 * but MUST send only editable fields on PUT/POST. These tests pin that behavior:
 * the leaky fields must never appear in the payload handed to the API module.
 */

const mockCheckPermission = vi.fn(() => true)

const mockConfigStore = {
    wordLists: { items: [{ id: 1, name: 'Wordlist A', description: 'desc' }] },
    osintSourceGroups: { items: [{ id: 2, name: 'Group A', description: 'desc', default: false }] },
    loadWordLists: vi.fn().mockResolvedValue({}),
    loadOSINTSourceGroups: vi.fn().mockResolvedValue({})
}

let configApi
let apiService

// Note: vue-i18n is NOT mocked — mountWithPlugins provides a real i18n
// instance from @/i18n/en.json, and the component's useI18n() uses it.

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: mockCheckPermission })
}))

vi.mock('@/stores/config', () => ({
    useConfigStore: () => mockConfigStore
}))

vi.mock('@/api/config', async () => {
    const actual = await vi.importActual('@/api/config')
    return {
        ...actual,
        createNewOSINTSource: vi.fn().mockResolvedValue({}),
        updateOSINTSource: vi.fn().mockResolvedValue({}),
        getAllCollectorsNodes: vi.fn()
    }
})

vi.mock('@/components/common/buttons/AddNewButton.vue', () => ({
    default: { name: 'AddNewButton', props: ['show'], template: '<div />' }
}))

vi.mock('@/components/common/dialogs/DialogToolbar.vue', () => ({
    default: {
        name: 'DialogToolbar',
        props: ['title', 'saving', 'saveDisabled'],
        emits: ['cancel', 'save'],
        template: '<div class="dialog-toolbar-stub"><button @click="$emit(\'save\')">save</button></div>'
    }
}))

vi.mock('@/components/common/dialogs/UnsavedChangesDialog.vue', () => ({
    default: { name: 'UnsavedChangesDialog', props: ['modelValue'], template: '<div />' }
}))

vi.mock('@/components/common/EntitySelectTable.vue', () => ({
    default: { name: 'EntitySelectTable', props: ['modelValue', 'title', 'items', 'headers', 'loading', 'disabled'], template: '<div />' }
}))

vi.mock('@/components/config/collectors/NewOSINTSourceGroup.vue', () => ({
    default: { name: 'NewOSINTSourceGroup', template: '<div />' }
}))

// Render the dialog inline instead of via teleport/overlay.
const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue', 'maxWidth', 'persistent', 'scrollable'],
    template: '<div class="v-dialog-stub"><slot /><template v-if="false" /><slot name="activator" /></div>',
    emits: ['update:modelValue']
}

// Build a node + collector with one parameter, mirroring the backend shape.
function makeNodeWithCollector() {
    return {
        id: 'node-1',
        name: 'Collector Node',
        collectors: [
            {
                id: 'collector-1',
                name: 'Playwright Collector',
                parameters: [
                    {
                        id: 'param-1',
                        key: 'URL',
                        name: 'URL',
                        description: 'Target URL',
                        default_value: 'https://example.com'
                    }
                ]
            }
        ]
    }
}

// An API record for an existing source, including runtime fields the backend
// populates and that the client must NOT send back on update.
function makeEditSourceRecord() {
    return {
        id: 'f0660dba-e430-4984-90de-ac84d8c2e9f8',
        name: 'VMware Advisories',
        description: 'Security advisories feed',
        collector_id: 'collector-1',
        parameter_values: [{ value: 'https://example.com/adv', parameter: { id: 'param-1', key: 'URL' } }],
        word_lists: [{ id: 1 }],
        osint_source_groups: [{ id: 2 }],
        // ── poisonous runtime fields; must be stripped from the PUT body ──
        last_attempted: '15.07.2026 - 17:51:42',
        last_collected: '15.07.2026 - 17:51:00',
        last_error_message: 'Element not found: css: .ecx-page-title-default',
        state: 2,
        modified: '15.07.2026 - 12:00:00',
        status: 'red',
        collector: { id: 'collector-1', name: 'Playwright Collector', type: 'PLAYWRIGHT_COLLECTOR' }
    }
}

async function mountForEdit(sourceRecord = makeEditSourceRecord()) {
    const wrapper = mountWithPlugins(NewOSINTSource, {
        props: { editItem: sourceRecord },
        global: { stubs: { VDialog: VDialogStub } }
    })
    await flushPromises()
    return wrapper
}

describe('NewOSINTSource — payload sanitization on save', () => {
    beforeEach(async () => {
        vi.clearAllMocks()
        mockCheckPermission.mockReturnValue(true)

        configApi = await import('@/api/config')
        apiService = (await import('@/services/api_service')).default

        vi.mocked(configApi.getAllCollectorsNodes).mockResolvedValue({
            items: [makeNodeWithCollector()]
        })

        // Pure module — mock the transport so updateOrCreate calls reach it.
        vi.spyOn(apiService, 'put').mockResolvedValue({})
        vi.spyOn(apiService, 'post').mockResolvedValue({})
    })

    it('does not leak server-managed fields into the update (PUT) payload', async () => {
        const wrapper = await mountForEdit()

        // Trigger save via the dialog toolbar's save event (saveAndClose).
        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(configApi.updateOSINTSource).toHaveBeenCalledTimes(1)
        const payload = configApi.updateOSINTSource.mock.calls[0][0]

        // The editable whitelist the backend OSINTSource.__init__ accepts.
        expect(Object.keys(payload).sort()).toEqual(
            ['collector_id', 'description', 'id', 'name', 'osint_source_groups', 'parameter_values', 'word_lists'].sort()
        )

        // Explicitly assert the crash-causing fields are absent.
        for (const forbidden of ['last_attempted', 'last_collected', 'last_error_message', 'state', 'modified', 'status', 'collector']) {
            expect(payload).not.toHaveProperty(forbidden)
        }

        // And the editable values are preserved.
        expect(payload.id).toBe('f0660dba-e430-4984-90de-ac84d8c2e9f8')
        expect(payload.name).toBe('VMware Advisories')
        expect(payload.collector_id).toBe('collector-1')
        expect(payload.word_lists).toEqual([{ id: 1 }])
        expect(payload.osint_source_groups).toEqual([{ id: 2 }])
    })

    it('does not leak server-managed fields into the create (POST) payload', async () => {
        // New record: no id → isEdit false → POST path.
        const newRecord = {
            ...makeEditSourceRecord(),
            id: ''
        }
        delete newRecord.collector_id
        const wrapper = await mountForEdit(newRecord)

        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(configApi.createNewOSINTSource).toHaveBeenCalledTimes(1)
        const payload = configApi.createNewOSINTSource.mock.calls[0][0]

        for (const forbidden of ['last_attempted', 'last_collected', 'last_error_message', 'state', 'modified', 'status', 'collector']) {
            expect(payload).not.toHaveProperty(forbidden)
        }

        expect(Object.keys(payload).sort()).toEqual(
            ['collector_id', 'description', 'id', 'name', 'osint_source_groups', 'parameter_values', 'word_lists'].sort()
        )
    })

    it('passes parameter_values through as {value, parameter} pairs', async () => {
        const wrapper = await mountForEdit()

        await wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(configApi.updateOSINTSource).toHaveBeenCalledTimes(1)
        const payload = configApi.updateOSINTSource.mock.calls[0][0]

        expect(payload.parameter_values).toHaveLength(1)
        expect(payload.parameter_values[0]).toMatchObject({
            value: expect.any(String),
            parameter: { id: 'param-1' }
        })
    })
})

describe('NewOSINTSource — edit-mode collector sync', () => {
    beforeEach(async () => {
        vi.clearAllMocks()
        mockCheckPermission.mockReturnValue(true)
        configApi = await import('@/api/config')
        vi.mocked(configApi.getAllCollectorsNodes).mockResolvedValue({
            items: [makeNodeWithCollector()]
        })
    })

    it('loads the node list on mount and resolves the saved collector', async () => {
        await mountForEdit()
        await flushPromises()
        expect(configApi.getAllCollectorsNodes).toHaveBeenCalledWith({ search: '' })
    })
})
