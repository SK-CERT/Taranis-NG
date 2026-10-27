import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import TagChips from '@/components/common/tags/TagChips.vue'

// A card shows the tags people put on the item, then its translation status per language as a
// chip per language code styled with that status's built-in tag; switched-off tags are not shown.

vi.mock('@/api/tags', () => ({
    getEntityTypeTags: vi.fn(() =>
        Promise.resolve({
            data: {
                tags: [
                    { id: 1, display_name: 'Urgent', color: '#FF0000', icon: 'mdi-fire', system_key: null, sort_order: 0 },
                    { id: 2, display_name: 'Reviewed', color: null, icon: null, system_key: null, sort_order: 1 },
                    {
                        id: 11,
                        display_name: 'translation_outdated',
                        color: '#FB8C00',
                        icon: 'mdi-alert',
                        system_key: 'translation_outdated',
                        sort_order: 102
                    },
                    {
                        id: 12,
                        display_name: 'translation_done',
                        color: '#2E7D32',
                        icon: 'mdi-check',
                        system_key: 'translation_done',
                        sort_order: 104
                    },
                    {
                        id: 13,
                        display_name: 'Bez jazyka',
                        color: '#757575',
                        icon: 'mdi-help',
                        system_key: 'language_not_set',
                        sort_order: 105
                    }
                ]
            }
        })
    )
}))

async function mountChips(props: Record<string, unknown>) {
    const wrapper = mountWithPlugins(TagChips, { props: { entityType: 'report_item', ...props } })
    await flushPromises()
    return wrapper
}

describe('TagChips', () => {
    it('shows the tags people put on it, then a chip per language with its status', async () => {
        const wrapper = await mountChips({ tagIds: [1], translationStatus: { sk: 'translation_outdated', cs: 'translation_done' } })

        expect(wrapper.findAll('[data-test="tag-chip"]').map((chip) => chip.text())).toEqual(['Urgent'])
        const slovak = wrapper.get('[data-test="translation-status-sk"]')
        expect(slovak.text()).toBe('SK')
        expect(slovak.attributes('title')).toBe('Slovak: Translation outdated')
        expect(wrapper.get('[data-test="translation-status-cs"]').attributes('title')).toBe('Czech: Translated')
    })

    it('leaves out a status whose tag is switched off', async () => {
        const wrapper = await mountChips({ translationStatus: { de: 'translation_missing', sk: 'translation_done' } })

        expect(wrapper.find('[data-test="translation-status-de"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="translation-status-sk"]').exists()).toBe(true)
    })

    it('names an item without a language with the tag as an admin renamed it', async () => {
        const wrapper = await mountChips({ translationStatus: { '': 'language_not_set' } })

        expect(wrapper.get('[data-test="translation-status-none"]').text()).toBe('Bez jazyka')
    })

    it('shows nothing for an item with neither tags nor status', async () => {
        const wrapper = await mountChips({})

        expect(wrapper.find('[data-test="tag-chips"]').exists()).toBe(false)
    })
})
