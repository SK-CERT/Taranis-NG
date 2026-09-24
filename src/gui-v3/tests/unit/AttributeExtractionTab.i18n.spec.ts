import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import cs from '@/i18n/cs.json'
import en from '@/i18n/en.json'
import { pluralRules } from '@/i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeExtractionTab from '@/components/config/attribute-extraction/AttributeExtractionTab.vue'

const apiMocks = vi.hoisted(() => ({ createNewAttributeExtractionRule: vi.fn() }))

vi.mock('@/api/config', async (importOriginal) => {
    const original = await importOriginal<typeof import('@/api/config')>()
    return {
        ...original,
        getAllAttributeExtractionRules: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
        getAllOSINTSourceGroups: vi.fn().mockResolvedValue({ data: { total_count: 0, items: [] } }),
        createNewAttributeExtractionRule: apiMocks.createNewAttributeExtractionRule
    }
})

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

// Renders the dialog's form slot, where the save error is shown, and lets the spec emit a save.
const EditableEntityTableStub = {
    name: 'EditableEntityTable',
    props: ['defaultItem'],
    emits: ['save', 'delete'],
    template: '<div><slot name="form" :item="defaultItem()" :is-new="true" /></div>'
}

const rejectWith = (data: Record<string, string>) =>
    apiMocks.createNewAttributeExtractionRule.mockRejectedValueOnce({ response: { status: 400, data } })

async function saveInCzech() {
    const i18n = createI18n({ legacy: false, locale: 'cs', fallbackLocale: 'en', messages: { cs, en }, pluralRules })
    const wrapper = mountWithPlugins(AttributeExtractionTab, {
        global: { plugins: [i18n], stubs: { EditableEntityTable: EditableEntityTableStub } }
    })
    await flushPromises()
    wrapper.findComponent({ name: 'EditableEntityTable' }).vm.$emit('save', { name: 'Ticket', pattern: '(unclosed' }, { isNew: true })
    await flushPromises()
    return wrapper
}

describe('AttributeExtractionTab save errors', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('shows an invalid pattern in a translated sentence around the engine message', async () => {
        rejectWith({ error: 'Invalid regular expression: missing ) at position 9', pattern_error: 'missing ) at position 9' })

        const wrapper = await saveInCzech()

        expect(wrapper.text()).toContain('Neplatný regulární výraz: missing ) at position 9')
        expect(wrapper.text()).not.toContain('Invalid regular expression')
    })

    it("falls back to the server's message for any other rejection", async () => {
        rejectWith({ error: "An attribute extraction rule named 'Ticket' already exists" })

        const wrapper = await saveInCzech()

        expect(wrapper.text()).toContain("An attribute extraction rule named 'Ticket' already exists")
    })
})
