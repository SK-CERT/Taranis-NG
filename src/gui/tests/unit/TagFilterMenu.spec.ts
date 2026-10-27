import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import TagFilterMenu from '@/components/common/tags/TagFilterMenu.vue'

// The list filter: tags people put on items, and needs translation / AI not reviewed / no language.

vi.mock('@/api/tags', () => ({
    getEntityTypeTags: vi.fn(() => Promise.resolve({ data: { tags: [{ id: 1, display_name: 'Urgent', system_key: null, sort_order: 0 }] } }))
}))

describe('TagFilterMenu', () => {
    it('counts what is applied: tags, and a translation filter once it has a language', async () => {
        const wrapper = mountWithPlugins(TagFilterMenu, {
            props: { entityType: 'report_item', modelValue: { tags: [1], translation: 'needs', translation_language: null } }
        })
        await flushPromises()
        expect(wrapper.get('[data-test="tag-filter"]').text()).toBe('1')

        await wrapper.setProps({ modelValue: { tags: [1], translation: 'needs', translation_language: 'sk' } })
        expect(wrapper.get('[data-test="tag-filter"]').text()).toBe('2')
    })

    it('sends the whole filter when one part changes', async () => {
        const wrapper = mountWithPlugins(TagFilterMenu, {
            props: { entityType: 'product', modelValue: { tags: [], translation: '', translation_language: null } }
        })
        await flushPromises()

        wrapper.vm.$.setupState['update']({ translation: 'not_set' })

        expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([{ tags: [], translation: 'not_set', translation_language: null }])
    })
})
