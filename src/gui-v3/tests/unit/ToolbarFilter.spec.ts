import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { createI18n } from 'vue-i18n'
import { mount } from '@vue/test-utils'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'

const passthroughStub = defineComponent({ template: '<div><slot /></div>' })

const mountFilter = (props: Record<string, unknown>, slots: Record<string, string> = {}) => {
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
        slots,
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

describe('ToolbarFilter prepend slot', () => {
    /**
     * The OSINT sources view puts its selection, import, export and delete controls on the search
     * bar's line. Every other view passes no such slot, so an absent one has to render nothing
     * rather than reserve space or break the row.
     */
    it('renders prepended controls ahead of the search field', () => {
        const wrapper = mountFilter({ totalCount: 0 }, { prepend: '<button class="probe">probe</button>' })

        const probe = wrapper.find('button.probe').element
        const search = wrapper.findComponent({ name: 'SearchField' }).element

        // Ahead of, not merely present: DOCUMENT_POSITION_FOLLOWING means search comes after.
        expect(probe.compareDocumentPosition(search) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    })

    it('renders nothing extra for the views that pass no slot', () => {
        const wrapper = mountFilter({ totalCount: 0 })

        expect(wrapper.find('button.probe').exists()).toBe(false)
        expect(wrapper.findComponent({ name: 'SearchField' }).exists()).toBe(true)
    })
})
