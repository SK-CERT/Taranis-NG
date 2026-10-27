import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, reactive } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { useAttributes } from '@/components/common/attribute/useAttributes'

// In a language tab the values are a report's translations: saved with the language, locked per
// language, and never added, deleted or reordered.

vi.mock('@/services/auth_service', () => ({
    default: { hasPermission: () => true }
}))

vi.mock('@/stores/user', () => ({
    useUserStore: () => ({ userId: 101 })
}))

vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn(),
    holdLockReportItem: vi.fn(),
    lockReportItem: vi.fn(),
    unlockReportItem: vi.fn(),
    updateReportItem: vi.fn()
}))

function setup(overrides = {}) {
    const props = reactive({
        edit: true,
        modify: true,
        readOnly: false,
        reportItemId: 7,
        language: 'en',
        values: [{ id: 21, value: 'An attacker can', version: 2 }],
        attributeGroup: { id: 11, min_occurrence: 1, max_occurrence: 3, attribute: { type: 'TEXT' } },
        ...overrides
    })
    let result
    const wrapper = mount(
        defineComponent({
            setup() {
                result = useAttributes(props)
                return () => null
            }
        })
    )
    return { props, result, wrapper }
}

describe('useAttributes in a language tab', () => {
    let analyzeApi

    beforeEach(async () => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        analyzeApi = await import('@/api/analyze')
    })

    it('locks the field per language', async () => {
        const { result, wrapper } = setup()

        await result.onFocus(0)
        await result.onBlur(0)

        expect(analyzeApi.lockReportItem).toHaveBeenCalledWith(7, { field_id: '21:en' })
        expect(analyzeApi.unlockReportItem).toHaveBeenCalledWith(7, { field_id: '21:en' })
        wrapper.unmount()
    })

    it('saves the translation with its language and the version it is based on', async () => {
        vi.mocked(analyzeApi.updateReportItem).mockResolvedValue({ data: { update: true, language: 'en', attribute_id: 21 } })
        vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
            data: { attribute_version: 3, attribute_user: 'Ann', attribute_last_updated: 'now' }
        })
        const { props, result, wrapper } = setup()

        props.values[0].value = 'An attacker may'
        await result.onEdit(0)

        expect(analyzeApi.updateReportItem).toHaveBeenCalledWith(7, {
            update: true,
            language: 'en',
            attribute_id: 21,
            attribute_value: 'An attacker may',
            base_version: 2
        })
        expect(props.values[0].version).toBe(3)
        wrapper.unmount()
    })

    it('neither adds nor seeds values', async () => {
        const { props, result, wrapper } = setup({ values: [] })

        await result.addInitialValues()

        expect(result.addButtonVisible.value).toBe(false)
        expect(props.values).toHaveLength(0)
        expect(analyzeApi.updateReportItem).not.toHaveBeenCalled()
        wrapper.unmount()
    })

    it('takes updates of its own language only', async () => {
        vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
            data: { attribute_id: 21, attribute_value: 'Updated by Bob', attribute_version: 4 }
        })
        const { props, wrapper } = setup()

        window.dispatchEvent(
            new CustomEvent('report-item-updated', { detail: { report_item_id: 7, user_id: 5, update: true, attribute_id: 21 } })
        )
        window.dispatchEvent(
            new CustomEvent('report-item-updated', {
                detail: { report_item_id: 7, user_id: 5, update: true, attribute_id: 21, language: 'sk' }
            })
        )
        await flushPromises()
        expect(analyzeApi.getReportItemData).not.toHaveBeenCalled()

        window.dispatchEvent(
            new CustomEvent('report-item-updated', {
                detail: { report_item_id: 7, user_id: 5, update: true, attribute_id: 21, language: 'en' }
            })
        )
        await flushPromises()
        expect(props.values[0].value).toBe('Updated by Bob')
        expect(props.values[0].version).toBe(4)
        wrapper.unmount()
    })

    it('shows a lock only for its own language', async () => {
        const { props, wrapper } = setup()

        window.dispatchEvent(new CustomEvent('report-item-locked', { detail: { report_item_id: 7, user_id: 5, field_id: 21 } }))
        expect(props.values[0].locked).toBeUndefined()

        window.dispatchEvent(new CustomEvent('report-item-locked', { detail: { report_item_id: 7, user_id: 5, field_id: '21:en' } }))
        expect(props.values[0].locked).toBe(true)
        wrapper.unmount()
    })

    it('a source field is not touched by a translation update', async () => {
        const { props, wrapper } = setup({ language: null })

        window.dispatchEvent(
            new CustomEvent('report-item-updated', {
                detail: { report_item_id: 7, user_id: 5, update: true, attribute_id: 21, language: 'en' }
            })
        )
        await flushPromises()

        expect(analyzeApi.getReportItemData).not.toHaveBeenCalled()
        expect(props.values[0].value).toBe('An attacker can')
        wrapper.unmount()
    })
})
