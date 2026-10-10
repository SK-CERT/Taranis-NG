import { describe, it, expect, beforeEach, vi } from 'vitest'
import { computed, defineComponent, h, reactive } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeLink from '@/components/common/attribute/AttributeLink.vue'
import AttributeText from '@/components/common/attribute/AttributeText.vue'
import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'
import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
import { createLinkReferences, provideLinkReferences } from '@/composables/useLinkReferences'
import { CITING_TYPES, numberLinks } from '@/utils/linkReferences'
import AuthService from '@/services/auth_service'
import { getReportItemData, updateReportItem } from '@/api/analyze'

vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn().mockResolvedValue({ data: {} }),
    holdLockReportItem: vi.fn().mockResolvedValue({}),
    lockReportItem: vi.fn().mockResolvedValue({}),
    unlockReportItem: vi.fn().mockResolvedValue({}),
    updateReportItem: vi.fn().mockResolvedValue({ data: {} })
}))

// Menus render inline, so their items can be clicked without an overlay.
const VMenuStub = {
    name: 'VMenu',
    props: ['disabled'],
    template: '<div class="menu-stub"><slot name="activator" :props="{}" /><slot /></div>'
}

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div class="dialog-stub"><slot v-if="modelValue" /></div>'
}

const VENDOR = 'https://vendor.example/advisory'
const NVD = 'https://nvd.nist.gov/vuln/detail/CVE-2026-0001'
const NEWS = 'https://news.example/story'

const linkGroup = (overrides = {}) => ({ id: 12, attribute: { type: 'LINK' }, min_occurrence: 0, max_occurrence: 10, ...overrides })
const textGroup = () => ({ id: 10, attribute: { type: 'TEXT' }, min_occurrence: 0, max_occurrence: 1 })

const linkValue = (id, url, key) => ({ id, index: id, value: url, value_description: key, locked: false, user: null })

/**
 * Mounts a report form in miniature: a link attribute and a text attribute sharing one
 * link-references context, as NewReportItem provides it.
 */
function mountForm({ links, text = '', edit = false, newsItemLinks = [] }) {
    const linkValues = reactive(links)
    const textValues = reactive([{ id: 50, index: 0, value: text, locked: false, user: null }])

    const Form = defineComponent({
        setup() {
            const references = createLinkReferences(
                computed(() => numberLinks(linkValues)),
                computed(() => textValues.map((value) => value.value)),
                computed(() => newsItemLinks)
            )
            provideLinkReferences(references)
            const common = { edit, modify: true, reportItemId: edit ? 42 : null }
            return () =>
                h('div', [
                    h(AttributeLink, { ...common, attributeGroup: linkGroup(), values: linkValues }),
                    h(AttributeText, { ...common, attributeGroup: textGroup(), values: textValues })
                ])
        }
    })

    const wrapper = mountWithPlugins(Form, { global: { stubs: { VMenu: VMenuStub, VDialog: VDialogStub } } })
    return { wrapper, linkValues, textValues }
}

const pairs = (values) => values.map((value) => [value.value, value.value_description])

describe('AttributeLink', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(AuthService, 'hasPermission').mockReturnValue(true)
    })

    it('is what AttributeContainer renders for LINK attributes', () => {
        const wrapper = mountWithPlugins(AttributeContainer, {
            props: { attributeItem: { attribute_group_item: linkGroup(), values: [] }, reportItemId: null, readOnly: true }
        })
        expect(wrapper.findComponent(AttributeLink).exists()).toBe(true)
    })

    it('numbers the links as their citations will be numbered', () => {
        const { wrapper } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, '', 'bbbbbb'), linkValue(3, NVD, 'cccccc')] })

        const numbers = wrapper.findAll('[data-test="link-row"] .link-list__number').map((number) => number.text())
        expect(numbers).toEqual(['[1]', '–', '[2]'])
    })

    it('inserts a new link between two links, and every link keeps its key', async () => {
        const { wrapper, linkValues } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, NVD, 'bbbbbb')] })

        await wrapper.findAll('[data-test="link-insert"]')[1].trigger('click')
        await flushPromises()

        expect(linkValues).toHaveLength(3)
        expect(pairs(linkValues)[0]).toEqual([VENDOR, 'aaaaaa'])
        expect(linkValues[1].value).toBe('')
        expect(linkValues[1].value_description).toMatch(/^[a-z0-9]{6}$/)
        expect(pairs(linkValues)[2]).toEqual([NVD, 'bbbbbb'])
    })

    it('saves an insertion in edit mode with the key the server gave the new link', async () => {
        vi.mocked(getReportItemData).mockResolvedValueOnce({
            data: { attribute_id: 3, attribute_value: '', attribute_value_description: 'srvkey', attribute_version: 1 }
        })
        const { wrapper, linkValues } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, NVD, 'bbbbbb')], edit: true })

        await wrapper.findAll('[data-test="link-insert"]')[1].trigger('click')
        await flushPromises()

        expect(pairs(linkValues)).toEqual([
            [VENDOR, 'aaaaaa'],
            ['', 'srvkey'],
            [NVD, 'bbbbbb']
        ])
        const saved = vi
            .mocked(updateReportItem)
            .mock.calls.map(([, data]) => data)
            .filter((data) => data.update)
        expect(saved.map((data) => [data.attribute_id, data.attribute_value, data.value_description])).toEqual([
            [2, '', 'srvkey'],
            [3, NVD, 'bbbbbb']
        ])
    })

    it('moves a link together with its key', async () => {
        const { wrapper, linkValues } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, NVD, 'bbbbbb')] })

        await wrapper.find('[data-test="link-row"] [title="Move down"]').trigger('click')
        await flushPromises()

        expect(pairs(linkValues)).toEqual([
            [NVD, 'bbbbbb'],
            [VENDOR, 'aaaaaa']
        ])
    })

    it('asks before deleting a cited link, and deletes an uncited one right away', async () => {
        const { wrapper, linkValues } = mountForm({
            links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, NVD, 'bbbbbb')],
            text: 'Fixed upstream [#bbbbbb].'
        })
        expect(wrapper.find('[data-test="link-citations"]').text()).toBe('Cited 1×')

        const deleteButtons = () => wrapper.findAll('[data-test="link-row"] [title="Delete value from this attribute"]')
        await deleteButtons()[1].trigger('click')
        expect(wrapper.findComponent(ConfirmationDialog).props('modelValue')).toBe(true)
        expect(linkValues).toHaveLength(2)

        await deleteButtons()[0].trigger('click')
        await flushPromises()
        expect(pairs(linkValues)).toEqual([[NVD, 'bbbbbb']])
    })

    it('adds the links of attached news items, filling an empty row first', async () => {
        const { wrapper, linkValues } = mountForm({
            links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, '', 'bbbbbb')],
            newsItemLinks: [VENDOR, NEWS]
        })

        const offered = wrapper.findAll('[data-test="link-from-news-item"]')
        expect(offered.map((item) => item.text())).toEqual([NEWS])

        await offered[0].trigger('click')
        await flushPromises()
        expect(pairs(linkValues)).toEqual([
            [VENDOR, 'aaaaaa'],
            [NEWS, 'bbbbbb']
        ])
    })
})

describe('citing links from text attributes', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(AuthService, 'hasPermission').mockReturnValue(true)
    })

    it('treats exactly the text types as citing', () => {
        expect([...CITING_TYPES]).toEqual(['STRING', 'TEXT', 'RICH_TEXT'])
    })

    it('inserts a citation token and shows what it resolves to', async () => {
        const { wrapper, textValues } = mountForm({
            links: [linkValue(1, VENDOR, 'aaaaaa'), linkValue(2, NVD, 'bbbbbb')],
            text: 'Fixed upstream'
        })

        const offered = wrapper.findAll('[data-test="cite-link"]')
        expect(offered.map((item) => item.text())).toEqual(['[1]vendor.example/advisory', '[2]nvd.nist.gov/vuln/detail/CVE-2026-0001'])

        await offered[1].trigger('click')
        await flushPromises()

        expect(textValues[0].value).toBe('Fixed upstream [#bbbbbb]')
        expect(wrapper.find('[data-test="reference-chip"]').text()).toBe('[2]nvd.nist.gov/vuln/detail/CVE-2026-0001')
    })

    it('saves an inserted citation in edit mode', async () => {
        const { wrapper } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa')], text: 'See', edit: true })

        await wrapper.find('[data-test="cite-link"]').trigger('click')
        await flushPromises()

        const saved = vi.mocked(updateReportItem).mock.calls.map(([, data]) => data)
        expect(saved).toContainEqual(expect.objectContaining({ update: true, attribute_id: 50, attribute_value: 'See [#aaaaaa]' }))
    })

    it('flags a citation whose link was deleted', () => {
        const { wrapper } = mountForm({ links: [linkValue(1, VENDOR, 'aaaaaa')], text: 'See [#gone00] and [#aaaaaa]' })

        expect(wrapper.find('[data-test="reference-missing"]').exists()).toBe(true)
        expect(wrapper.findAll('[data-test="reference-chip"]')).toHaveLength(1)
    })
})
