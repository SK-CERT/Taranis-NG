import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import TagsTab from '@/components/config/workflow/TagsTab.vue'
import TagWorkflowTab from '@/components/config/workflow/TagWorkflowTab.vue'
import { createTag, createTagEntityType, deleteTag } from '@/api/config'

// Configuration › Workflow: admins define tags and link them to reports and products. Built-in
// tags (translation status, language not set) can be renamed and restyled, not deleted, and
// their links can be switched off, not removed.

const urgent = { id: 1, display_name: 'Urgent', description: '', color: '#FF0000', icon: 'mdi-fire', system_key: null }
const outdated = {
    id: 11,
    display_name: 'translation_outdated',
    description: null,
    color: '#FB8C00',
    icon: 'mdi-alert',
    system_key: 'translation_outdated'
}

vi.mock('@/api/config', () => ({
    getAllTags: vi.fn(() => Promise.resolve({ data: { items: [urgent, outdated] } })),
    createTag: vi.fn(() => Promise.resolve({})),
    updateTag: vi.fn(() => Promise.resolve({})),
    deleteTag: vi.fn(() => Promise.resolve({})),
    getAllTagEntityTypes: vi.fn(() =>
        Promise.resolve({
            data: {
                items: [
                    { id: 21, tag_id: 1, entity_type: 'report_item', is_active: true, sort_order: 0, tag: urgent },
                    { id: 22, tag_id: 11, entity_type: 'report_item', is_active: true, sort_order: 102, tag: outdated }
                ]
            }
        })
    ),
    createTagEntityType: vi.fn(() => Promise.resolve({})),
    updateTagEntityType: vi.fn(() => Promise.resolve({})),
    deleteTagEntityType: vi.fn(() => Promise.resolve({}))
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }

const rows = (wrapper: ReturnType<typeof mountWithPlugins>, table: string) => wrapper.get(`[data-test="${table}"]`).findAll('tbody tr')

describe('Tags configuration', () => {
    beforeEach(() => vi.clearAllMocks())

    it('lists the tags by their shown name, built-in ones locked against deletion', async () => {
        const wrapper = mountWithPlugins(TagsTab)
        await flushPromises()

        const headers = wrapper
            .get('[data-test="tags-table"]')
            .findAll('thead th')
            .map((cell) => cell.text())
        // Laid out like States: the name, then its colour and icon in columns of their own.
        expect(headers).toEqual(['Name', 'Description', 'Color', 'Icon', 'Actions'])
        // "Translation outdated" sorts before "Urgent", though it is stored as translation_outdated.
        const [builtIn, admin] = rows(wrapper, 'tags-table')
        expect(admin!.text()).toContain('Urgent')
        expect(admin!.text()).toContain('#FF0000')
        expect(admin!.find('.mdi-fire').exists()).toBe(true)
        expect(admin!.find('button[title="Delete"]').exists()).toBe(true)
        expect(builtIn!.text()).toContain('Translation outdated')
        expect(builtIn!.find('button[title="Delete"]').exists()).toBe(false)

        // Search finds a built-in tag by the name shown, not by its stored key.
        wrapper.vm.$.setupState['search'] = 'Translation outdated'
        await flushPromises()
        expect(rows(wrapper, 'tags-table').map((row) => row.text())).toEqual([expect.stringContaining('Translation outdated')])
    })

    it('creates an admin tag without sending an id or a key', async () => {
        const wrapper = mountWithPlugins(TagsTab, { global: { stubs: { VDialog: VDialogStub } } })
        await flushPromises()

        wrapper.vm.$.setupState['addItem']()
        await flushPromises()
        await wrapper.get('[data-test="tag-name"] input').setValue('Needs review')
        await wrapper.vm.$.setupState['saveAndClose']()
        await flushPromises()

        expect(createTag).toHaveBeenCalledWith({ display_name: 'Needs review', description: '', color: '#607D8B', icon: 'mdi-tag' })
    })

    it('says how many items still carry a tag it cannot delete', async () => {
        vi.mocked(deleteTag).mockRejectedValueOnce({ response: { status: 409, data: { usage_count: 4 } } })
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        const wrapper = mountWithPlugins(TagsTab)
        await flushPromises()

        wrapper.vm.$.setupState['deleteItem'](urgent)
        await wrapper.vm.$.setupState['deleteRecord']()
        await flushPromises()

        expect(notifications.at(-1)?.detail).toEqual({ type: 'error', loc: 'tags.in_use', params: { count: 4 } })
    })

    it('links a tag to an entity type and keeps built-in links', async () => {
        const wrapper = mountWithPlugins(TagWorkflowTab)
        await flushPromises()

        const [admin, builtIn] = rows(wrapper, 'tag-workflow-table')
        // What a link applies to shows as in State Workflow: a coloured chip with an icon.
        const entityType = admin!.findComponent({ name: 'EntityTypeChip' })
        expect(entityType.text()).toContain('Report Item')
        expect(entityType.find('.mdi-file-document').exists()).toBe(true)
        expect(admin!.find('button[title="Delete"]').exists()).toBe(true)
        expect(builtIn!.find('button[title="Delete"]').exists()).toBe(false)

        wrapper.vm.editedItem = { id: -1, tag_id: 1, entity_type: 'product', is_active: true, sort_order: 3 }
        await wrapper.vm.save()

        expect(createTagEntityType).toHaveBeenCalledWith({ tag_id: 1, entity_type: 'product', is_active: true, sort_order: 3 })
    })
})
