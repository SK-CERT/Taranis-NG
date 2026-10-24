import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import GlossaryTable from '@/components/config/reports/GlossaryTable.vue'
import { createGlossaryEntry, deleteGlossaryEntry, getGlossary, updateGlossaryEntry } from '@/api/config'

// The AI translation glossary, of the instance or of a report type: a column per language in use,
// entries saved one by one, and the server's rule (two languages, or one term to keep) mirrored
// before anything is sent.

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

const table = (wrapper: ReturnType<typeof mountWithPlugins>) => wrapper.findComponent({ name: 'EditableEntityTable' })

describe('GlossaryTable', () => {
    beforeEach(() => vi.clearAllMocks())

    it('lists the instance glossary with a column per language in use', async () => {
        const wrapper = mountWithPlugins(GlossaryTable)
        await flushPromises()

        expect(getGlossary).toHaveBeenCalledWith(null)
        // Padded like the other Reports tabs, with no introduction above the table.
        expect(wrapper.get('[data-test="glossary"]').classes()).toContain('px-4')
        expect(wrapper.find('.v-alert').exists()).toBe(false)
        const headers = wrapper.findAll('thead th').map((cell) => cell.text())
        expect(headers.slice(0, 2)).toEqual(['Czech', 'English'])
        const [first, second] = wrapper.findAll('tbody tr')
        expect(first!.text()).toContain('zranitelnost')
        expect(first!.text()).toContain('vulnerability')
        expect(second!.text()).toContain('our product')
    })

    it("offers a type's own languages besides those in use, and loads only its entries", async () => {
        const wrapper = mountWithPlugins(GlossaryTable, { props: { reportItemTypeId: 9, languages: ['sk', 'en', null] } })
        await flushPromises()

        expect(getGlossary).toHaveBeenCalledWith(9)
        expect(wrapper.vm.allLanguages).toEqual(['cs', 'en', 'sk'])
        expect(wrapper.get('.v-alert').text()).toContain('instance-wide glossary')
        expect(wrapper.get('[data-test="glossary"]').classes()).not.toContain('px-4')
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
