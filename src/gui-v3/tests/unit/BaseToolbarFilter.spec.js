import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'

// Stub the AddNewButton to keep tests focused
const stubs = {
    AddNewButton: {
        name: 'AddNewButton',
        template: '<button class="add-new-stub" @click="$emit(\'click\')"><slot /></button>',
        props: ['label']
    }
}

const createCountMessages = () =>
    createI18n({
        legacy: false,
        locale: 'en',
        messages: {
            en: {
                test: { total: 'No records | {count} record | {count} records' },
                toolbar_filter: {
                    currently_showing: 'Showing no records | Showing {count} record | Showing {count} records',
                    selected_count: 'No records selected | {count} record selected | {count} records selected'
                }
            }
        }
    })

describe('BaseToolbarFilter', () => {
    const defaultProps = {
        title: 'toolbar_filter.search',
        totalCount: 42
    }

    // ── Rendering ─────────────────────────────────
    describe('rendering', () => {
        it('should render the title', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: defaultProps,
                global: { stubs }
            })

            expect(wrapper.text()).toContain('Search')
        })

        it('should display a complete plural total with a locale-formatted count', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, totalCountTitle: 'test.total', totalCount: 12000 },
                global: { stubs, plugins: [createCountMessages()] }
            })

            expect(wrapper.text()).toContain('12,000 records')
        })

        it('should display currently showing as a complete plural message', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, currentlyShowingCount: 1 },
                global: { stubs, plugins: [createCountMessages()] }
            })

            expect(wrapper.text()).toContain('Showing 1 record')
        })

        it('should show day range chips when showDayRanges is true', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showDayRanges: true },
                global: { stubs }
            })

            const chips = wrapper.findAllComponents({ name: 'VChip' })
            expect(chips.length).toBeGreaterThan(0)
        })

        it('should hide day range chips when showDayRanges is false', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showDayRanges: false, showSort: false },
                global: { stubs }
            })

            const chips = wrapper.findAllComponents({ name: 'VChip' })
            expect(chips.length).toBe(0)
        })
    })

    // ── Add Button ────────────────────────────────
    describe('add button', () => {
        it('should show AddNewButton when showAddButton is true', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showAddButton: true },
                global: { stubs }
            })

            expect(wrapper.find('.add-new-stub').exists()).toBe(true)
        })

        it('should not show AddNewButton when showAddButton is false', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showAddButton: false },
                global: { stubs }
            })

            expect(wrapper.find('.add-new-stub').exists()).toBe(false)
        })

        it('should emit add-new when AddNewButton is clicked', async () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showAddButton: true },
                global: { stubs }
            })

            await wrapper.find('.add-new-stub').trigger('click')
            expect(wrapper.emitted('add-new')).toBeDefined()
            expect(wrapper.emitted('add-new').length).toBeGreaterThanOrEqual(1)
        })

        it('passes the label as a translation key (AddNewButton translates it itself, avoiding double translation)', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showAddButton: true },
                global: { stubs }
            })

            const addBtn = wrapper.findComponent({ name: 'AddNewButton' })
            expect(addBtn.props('label')).toBe('common.add_btn')
        })
    })

    // ── Search ────────────────────────────────────
    describe('search', () => {
        it('should have a search text field', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: defaultProps,
                global: { stubs }
            })

            const textField = wrapper.findComponent({ name: 'VTextField' })
            expect(textField.exists()).toBe(true)
        })

        it('should debounce search and emit update-filter', async () => {
            vi.useFakeTimers()
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, searchDebounceMs: 100 },
                global: { stubs }
            })

            // Type into the field rather than emitting at the Vuetify component: VTextField
            // declares `update:modelValue`, so emitting the hyphenated spelling by hand only
            // produced a "not declared in the emits option" warning while bypassing the real
            // v-model path this test is about.
            await wrapper.find('input').setValue('test query')
            vi.advanceTimersByTime(150)
            await wrapper.vm.$nextTick()

            const emitted = wrapper.emitted('update-filter')
            expect(emitted).toBeDefined()
            expect(emitted[emitted.length - 1][0]).toMatchObject({ search: 'test query' })
            vi.useRealTimers()
        })
    })

    // ── Range Filter ──────────────────────────────
    describe('range filter', () => {
        it('should emit update-filter when a range chip is clicked', async () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showDayRanges: true },
                global: { stubs }
            })

            // Find chips - first set of chips are range chips
            const chips = wrapper.findAllComponents({ name: 'VChip' })
            expect(chips.length).toBeGreaterThan(1)

            // Click the second chip (TODAY)
            await chips[1].trigger('click')

            const emitted = wrapper.emitted('update-filter')
            expect(emitted).toBeDefined()
            expect(emitted[0][0].range).toBe('TODAY')
        })
    })

    // ── Sort Toggle ───────────────────────────────
    describe('sort toggle', () => {
        it('should toggle sort between DATE_DESC and DATE_ASC', async () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showSort: true, showDayRanges: false },
                global: { stubs }
            })

            // Default sort is DATE_DESC, click to toggle
            const sortChip = wrapper.findAllComponents({ name: 'VChip' })[0]
            await sortChip.trigger('click')

            const emitted = wrapper.emitted('update-filter')
            expect(emitted).toBeDefined()
            expect(emitted[0][0].sort).toBe('DATE_ASC')
        })
    })

    // ── Selected Count ────────────────────────────
    describe('selected count', () => {
        it('should show selected count when showSelectedCount is true', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showSelectedCount: true, selectedCount: 5 },
                global: { stubs, plugins: [createCountMessages()] }
            })

            expect(wrapper.text()).toContain('5 records selected')
        })

        it('should not show selected count when showSelectedCount is false', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: { ...defaultProps, showSelectedCount: false, selectedCount: 5 },
                global: { stubs }
            })

            // Selected count title should not appear
            expect(wrapper.text()).not.toContain('toolbar_filter.selected_count')
        })
    })

    // ── Expose ────────────────────────────────────
    describe('exposed API', () => {
        it('should expose filter ref and emitFilter method', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: defaultProps,
                global: { stubs }
            })

            expect(wrapper.vm.filter).toBeDefined()
            expect(typeof wrapper.vm.emitFilter).toBe('function')
        })

        it('emitFilter should emit update-filter with current filter state', () => {
            const wrapper = mountWithPlugins(BaseToolbarFilter, {
                props: defaultProps,
                global: { stubs }
            })

            wrapper.vm.emitFilter()
            const emitted = wrapper.emitted('update-filter')
            expect(emitted).toHaveLength(1)
        })
    })
})
