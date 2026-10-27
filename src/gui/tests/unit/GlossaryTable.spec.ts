import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import GlossaryTable from '@/components/config/reports/GlossaryTable.vue'
import { createGlossaryEntry, deleteGlossaryEntry, getGlossary, updateGlossaryEntry } from '@/api/config'

// The AI translation glossary, of the instance or of a report type: an entry's terms in one column,
// each marked with its language; an entry starts with a field per report language, and adds or
// removes its own; entries saved one by one, and the server's rule (two languages, or one term to
// keep) mirrored before anything is sent.

const vulnerability = { id: 1, terms: { cs: 'zranitelnost', en: 'vulnerability' }, keep: false, note: '' }
const product = { id: 2, terms: { en: 'Taranis NG' }, keep: true, note: 'our product' }

vi.mock('@/api/config', () => ({
    getGlossary: vi.fn(() => Promise.resolve({ data: { items: [vulnerability, product], languages: ['cs', 'en'] } })),
    createGlossaryEntry: vi.fn(() => Promise.resolve({})),
    updateGlossaryEntry: vi.fn(() => Promise.resolve({})),
    deleteGlossaryEntry: vi.fn(() => Promise.resolve({}))
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const VDialogStub = { name: 'VDialog', template: '<div><slot /></div>' }

const table = (wrapper: ReturnType<typeof mountWithPlugins>) => wrapper.findComponent({ name: 'EditableEntityTable' })

async function editFirstEntry() {
    const wrapper = mountWithPlugins(GlossaryTable, { global: { stubs: { VDialog: VDialogStub } } })
    await flushPromises()
    await wrapper
        .findAllComponents({ name: 'ActionButton' })
        .find((button) => button.props('action') === 'edit')!
        .trigger('click')
    await flushPromises()
    return wrapper
}

const termFields = (wrapper: ReturnType<typeof mountWithPlugins>) =>
    wrapper.findAll('[data-test^="glossary-term-"]').map((field) => field.attributes('data-test')!.slice('glossary-term-'.length))

describe('GlossaryTable', () => {
    beforeEach(() => vi.clearAllMocks())

    it("lists the instance glossary with each entry's terms in one column", async () => {
        const wrapper = mountWithPlugins(GlossaryTable)
        await flushPromises()

        expect(getGlossary).toHaveBeenCalledWith(null)
        // Padded like the other Reports tabs, with no introduction above the table.
        expect(wrapper.get('[data-test="glossary"]').classes()).toContain('px-4')
        expect(wrapper.find('.v-alert').exists()).toBe(false)
        const headers = wrapper.findAll('thead th').map((cell) => cell.text())
        expect(headers.slice(0, 2)).toEqual(['Terms', 'Keep as written'])
        const [first, second] = wrapper.findAll('tbody tr')
        expect(first!.get('[data-test="glossary-cell-cs"]').text()).toMatch(/^CS\s*zranitelnost$/)
        expect(first!.get('[data-test="glossary-cell-en"]').text()).toMatch(/^EN\s*vulnerability$/)
        // No empty marker for a language the entry has no term in.
        expect(second!.find('[data-test="glossary-cell-cs"]').exists()).toBe(false)
        expect(second!.text()).toContain('our product')
    })

    it("offers a type's own languages besides those in use, and loads only its entries", async () => {
        const wrapper = mountWithPlugins(GlossaryTable, { props: { reportItemTypeId: 9, languages: ['sk', 'en', null] } })
        await flushPromises()

        expect(getGlossary).toHaveBeenCalledWith(9)
        expect(wrapper.vm.suggestedLanguages).toEqual(['cs', 'en', 'sk'])
        expect(wrapper.get('.v-alert').text()).toContain('instance-wide glossary')
        expect(wrapper.get('[data-test="glossary"]').classes()).not.toContain('px-4')
    })

    it("removes and adds an entry's languages, for that entry only", async () => {
        const wrapper = await editFirstEntry()
        expect(termFields(wrapper)).toEqual(['cs', 'en'])

        await wrapper.get('[data-test="glossary-remove-cs"]').trigger('click')
        await flushPromises()
        expect(termFields(wrapper)).toEqual(['en'])

        const dialog = wrapper.findAllComponents({ name: 'EditableEntityTable' })[0]!
        wrapper.vm.addLanguage(dialog.vm.$.setupState['editedItem'], 'sk')
        await flushPromises()
        expect(termFields(wrapper)).toEqual(['en', 'sk'])
        await wrapper.get('[data-test="glossary-term-sk"] input').setValue('zraniteľnosť')

        wrapper.findComponent({ name: 'DialogToolbar' }).vm.$emit('save')
        await flushPromises()

        expect(updateGlossaryEntry).toHaveBeenCalledWith(1, { terms: { en: 'vulnerability', sk: 'zraniteľnosť' }, keep: false, note: '' })
        // The table kept the entry as it was until the save reloaded it.
        expect(wrapper.vm.entries[0]!.terms).toEqual({ cs: 'zranitelnost', en: 'vulnerability' })
    })

    it('starts a new entry with a field per report language', async () => {
        const wrapper = mountWithPlugins(GlossaryTable, { global: { stubs: { VDialog: VDialogStub } } })
        await flushPromises()
        await wrapper.findComponent({ name: 'AddNewButton' }).trigger('click')
        await flushPromises()

        expect(termFields(wrapper)).toEqual(['cs', 'en'])
    })

    it('needs two languages, or one term to keep as written', async () => {
        const wrapper = mountWithPlugins(GlossaryTable)
        await flushPromises()

        expect(wrapper.vm.isComplete({ id: -1, keep: false, note: '', term_en: 'patch', term_cs: ' ' })).toBe(false)
        expect(wrapper.vm.isComplete({ id: -1, keep: false, note: '', term_en: 'patch', term_cs: 'záplata' })).toBe(true)
        expect(wrapper.vm.isComplete({ id: -1, keep: true, note: '', term_en: 'CESNET' })).toBe(true)
    })

    it('saves a new entry to the glossary it shows, trimmed and without empty terms', async () => {
        const wrapper = mountWithPlugins(GlossaryTable, { props: { reportItemTypeId: 9 } })
        await flushPromises()

        table(wrapper).vm.$emit(
            'save',
            { id: -1, keep: false, note: ' ', term_cs: ' záplata ', term_en: 'patch', term_sk: '' },
            { isNew: true }
        )
        await flushPromises()

        expect(createGlossaryEntry).toHaveBeenCalledWith({
            terms: { cs: 'záplata', en: 'patch' },
            keep: false,
            note: ' ',
            report_item_type_id: 9
        })
        expect(getGlossary).toHaveBeenCalledTimes(2)
    })

    it('updates an entry in place and shows why the server refused one', async () => {
        vi.mocked(updateGlossaryEntry).mockRejectedValueOnce({ response: { data: { error: 'A term has at most 200 characters' } } })
        const notifications: CustomEvent[] = []
        window.addEventListener('notification', (event) => notifications.push(event as CustomEvent))
        const wrapper = mountWithPlugins(GlossaryTable)
        await flushPromises()

        table(wrapper).vm.$emit('save', { id: 2, keep: true, note: 'our product', term_en: 'Taranis NG' }, { isNew: false })
        await flushPromises()

        expect(updateGlossaryEntry).toHaveBeenCalledWith(2, { terms: { en: 'Taranis NG' }, keep: true, note: 'our product' })
        expect(notifications.at(-1)?.detail).toEqual({ type: 'error', message: 'A term has at most 200 characters' })
    })

    it('deletes an entry once confirmed', async () => {
        const wrapper = mountWithPlugins(GlossaryTable)
        await flushPromises()

        table(wrapper).vm.$emit('delete', { id: 1, keep: false, note: '' }, 0)
        await wrapper.vm.$.setupState['deleteRecord']()
        await flushPromises()

        expect(deleteGlossaryEntry).toHaveBeenCalledWith(1)
    })
})
