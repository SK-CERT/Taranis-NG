import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { createI18n } from 'vue-i18n'
import { mount } from '@vue/test-utils'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'

const passthroughStub = defineComponent({ template: '<div><slot /></div>' })

const mountFilter = (props: Record<string, unknown>) => {
    const i18n = createI18n({
        legacy: false,
        locale: 'en',
        messages: {
            en: {
                test: {
                    total: 'No records | {count} record | {count} records',
                    selected: 'No records selected | {count} record selected | {count} records selected'
                }
            }
        }
    })

    return mount(ToolbarFilter, {
        props: {
            totalCountTitle: 'test.total',
            selectedCountTitle: 'test.selected',
            ...props
        },
        global: {
            plugins: [i18n],
            stubs: {
                VContainer: passthroughStub,
                VRow: passthroughStub,
                VCol: passthroughStub,
                SearchField: true
            }
        }
    })
}

describe('ToolbarFilter count messages', () => {
    it.each([
        [0, 'No records'],
        [1, '1 record'],
        [2, '2 records'],
        [12000, '12,000 records']
    ])('renders total count %i with plural choice and locale number formatting', (count, expected) => {
        const wrapper = mountFilter({ totalCount: count })

        expect(wrapper.text()).toContain(expected)
    })

    it('renders selected count as a complete plural message', () => {
        const wrapper = mountFilter({ totalCount: 0, showSelectedCount: true, selectedCount: 2 })

        expect(wrapper.text()).toContain('2 records selected')
    })
})
