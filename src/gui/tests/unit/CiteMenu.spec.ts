import { describe, it, expect } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CiteMenu from '@/components/common/links/CiteMenu.vue'
import type { CitableLink, ExternalLink } from '@/utils/linkReferences'

// The menu renders inline, so its items can be clicked; the activator opens it.
const VMenuStub = {
    name: 'VMenu',
    props: ['modelValue', 'disabled'],
    emits: ['update:modelValue'],
    template:
        '<div class="menu-stub" :data-open="String(!!modelValue)">' +
        '<slot name="activator" :props="{ onClick: () => $emit(\'update:modelValue\', true) }" /><slot /></div>'
}

const ownLinks = (count: number): CitableLink[] =>
    Array.from({ length: count }, (_, index) => ({
        key: `key${String(index + 1).padStart(3, '0')}`,
        url: `https://site${index + 1}.example/advisory`,
        number: index + 1
    }))

const VENDOR: CitableLink = { key: 'vendor', url: 'https://vendor.example/advisory', number: 1 }
const NVD: CitableLink = { key: 'nvdkey', url: 'https://nvd.nist.gov/vuln/detail/CVE-2026-0001', number: 2 }

function mountMenu(links: CitableLink[], groups: Array<{ title: string; links: ExternalLink[] }> = []) {
    return mountWithPlugins(CiteMenu, {
        props: { links, groups },
        global: { stubs: { VMenu: VMenuStub } }
    }) as VueWrapper
}

const offered = (wrapper: VueWrapper) => wrapper.findAll('[data-test="cite-link"]').map((item) => item.text())
const offeredExternal = (wrapper: VueWrapper) => wrapper.findAll('[data-test="cite-external-link"]').map((item) => item.text())
const search = (wrapper: VueWrapper, text: string) => wrapper.find('[data-test="cite-search"] input').setValue(text)

describe('CiteMenu', () => {
    it('labels each link with the token it inserts', () => {
        const wrapper = mountMenu([VENDOR, NVD])

        expect(offered(wrapper)).toEqual(['[#vendor]vendor.example/advisory', '[#nvdkey]nvd.nist.gov/vuln/detail/CVE-2026-0001'])
    })

    it('offers a search only for more than eight links', () => {
        expect(mountMenu(ownLinks(8)).find('[data-test="cite-search"]').exists()).toBe(false)
        expect(mountMenu(ownLinks(9)).find('[data-test="cite-search"]').exists()).toBe(true)
        // The links of reports count as well.
        const groups = [{ title: 'Report', links: [{ key: 'rep001', url: 'https://report.example/a' }] }]
        expect(mountMenu(ownLinks(8), groups).find('[data-test="cite-search"]').exists()).toBe(true)
    })

    it('finds links by URL and by token', async () => {
        const wrapper = mountMenu([...ownLinks(8), NVD])

        await search(wrapper, 'NVD.nist')
        expect(offered(wrapper)).toEqual(['[#nvdkey]nvd.nist.gov/vuln/detail/CVE-2026-0001'])

        await search(wrapper, '[#key00')
        expect(offered(wrapper)).toHaveLength(8)

        await search(wrapper, 'key009')
        expect(offered(wrapper)).toEqual([])
        expect(wrapper.find('[data-test="cite-no-match"]').exists()).toBe(true)
    })

    it("finds a report's links by the report's title or by their URL", async () => {
        const groups = [
            {
                title: 'Vendor advisory',
                links: [
                    { key: 'rep001', url: 'https://a.example/one' },
                    { key: 'rep002', url: 'https://b.example/two' }
                ]
            },
            { title: 'Other report', links: [{ key: null, url: 'https://c.example/three' }] }
        ]
        const wrapper = mountMenu(ownLinks(8), groups)

        await search(wrapper, 'vendor adv')
        expect(offered(wrapper)).toEqual([])
        expect(offeredExternal(wrapper)).toEqual(['a.example/one', 'b.example/two'])

        await search(wrapper, 'c.example')
        expect(offeredExternal(wrapper)).toEqual(['c.example/three'])
        expect(wrapper.text()).not.toContain('Vendor advisory')
    })

    it('cites the first link found on Enter, and closes', async () => {
        const wrapper = mountMenu([...ownLinks(8), NVD])
        await wrapper.find('[data-test="cite-menu"]').trigger('click')
        expect(wrapper.find('.menu-stub').attributes('data-open')).toBe('true')

        await search(wrapper, 'nvd')
        await wrapper.find('[data-test="cite-search"] input').trigger('keydown', { key: 'Enter' })

        expect(wrapper.emitted('pick')).toEqual([[NVD]])
        expect(wrapper.find('.menu-stub').attributes('data-open')).toBe('false')
    })

    it('cites a clicked link and closes; a new opening starts with an empty search', async () => {
        const groups = [{ title: 'Report', links: [{ key: 'rep001', url: 'https://report.example/a' }] }]
        const wrapper = mountMenu(ownLinks(8), groups)
        await wrapper.find('[data-test="cite-menu"]').trigger('click')
        await search(wrapper, 'report.example')

        await wrapper.find('[data-test="cite-external-link"]').trigger('click')

        expect(wrapper.emitted('pick-external')).toEqual([[groups[0]!.links[0]]])
        expect(wrapper.find('.menu-stub').attributes('data-open')).toBe('false')

        await wrapper.find('[data-test="cite-menu"]').trigger('click')
        expect(offered(wrapper)).toHaveLength(8)
    })
})
