import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import EnumSelector from '@/components/common/EnumSelector.vue'

const { getAttributeEnumsMock, getCPEAttributeEnumsMock } = vi.hoisted(() => ({
    getAttributeEnumsMock: vi.fn(),
    getCPEAttributeEnumsMock: vi.fn()
}))

vi.mock('@/api/analyze', () => ({ getAttributeEnums: getAttributeEnumsMock }))
vi.mock('@/api/assets', () => ({ getCPEAttributeEnums: getCPEAttributeEnumsMock }))

const mountSelector = (props = {}) =>
    mountWithPlugins(EnumSelector, {
        props: { attributeId: 17, valueIndex: 1, ...props },
        global: {
            stubs: {
                VDialog: {
                    props: ['modelValue'],
                    template: '<div><slot /></div>'
                }
            }
        }
    })

describe('EnumSelector', () => {
    beforeEach(() => {
        vi.useRealTimers()
        vi.clearAllMocks()
        getAttributeEnumsMock.mockResolvedValue({
            data: { items: [{ value: 'CVE-2026-12345', description: 'Example CVE' }], total_count: 1 }
        })
        getCPEAttributeEnumsMock.mockResolvedValue({
            data: { items: [{ value: 'cpe:2.3:a:vendor:product:%' }], total_count: 1 }
        })
    })

    it('loads the selected attribute enum page when opened', async () => {
        const wrapper = mountSelector()

        wrapper.vm.open()
        await flushPromises()

        expect(getAttributeEnumsMock).toHaveBeenCalledWith({
            attribute_id: 17,
            search: '',
            offset: 0,
            limit: 25
        })
    })

    it('searches with debounce and requests server-side pages', async () => {
        vi.useFakeTimers()
        const wrapper = mountSelector()
        wrapper.vm.open()
        await flushPromises()
        getAttributeEnumsMock.mockClear()

        wrapper.vm.search = 'CVE-2026'
        await vi.advanceTimersByTimeAsync(300)
        await flushPromises()

        expect(getAttributeEnumsMock).toHaveBeenLastCalledWith({
            attribute_id: 17,
            search: 'CVE-2026',
            offset: 0,
            limit: 25
        })

        wrapper.vm.updateOptions({ page: 2, itemsPerPage: 50 })
        await flushPromises()
        expect(getAttributeEnumsMock).toHaveBeenLastCalledWith({
            attribute_id: 17,
            search: 'CVE-2026',
            offset: 50,
            limit: 50
        })
    })

    it('emits the correct occurrence, value, and description', () => {
        const wrapper = mountSelector()

        wrapper.vm.select({ value: 'CWE-79', description: 'Cross-site scripting' })

        expect(wrapper.emitted('enum-selected')).toEqual([[{ index: 1, value: 'CWE-79', value_description: 'Cross-site scripting' }]])
    })

    it('uses the CPE-only endpoint and converts its wildcard notation', async () => {
        const wrapper = mountSelector({ cpeOnly: true })
        wrapper.vm.open()
        await flushPromises()

        expect(getCPEAttributeEnumsMock).toHaveBeenCalledWith({ search: '', offset: 0, limit: 25 })
        wrapper.vm.select({ value: 'cpe:2.3:a:vendor:product:%' })
        expect(wrapper.emitted('enum-selected')).toEqual([[{ index: 1, value: 'cpe:2.3:a:vendor:product:*' }]])
    })

    it('does not open or request data while disabled', async () => {
        const wrapper = mountSelector({ disabled: true })

        wrapper.vm.open()
        await flushPromises()

        expect(getAttributeEnumsMock).not.toHaveBeenCalled()
    })
})
