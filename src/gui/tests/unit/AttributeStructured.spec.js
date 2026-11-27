import { describe, it, expect, beforeEach, vi } from 'vitest'
import { reactive } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'
import AttributeStructured from '@/components/common/attribute/AttributeStructured.vue'
import AuthService from '@/services/auth_service'
import { lockReportItem, unlockReportItem, updateReportItem } from '@/api/analyze'

vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn().mockResolvedValue({ data: { attribute_version: 2 } }),
    holdLockReportItem: vi.fn().mockResolvedValue({}),
    lockReportItem: vi.fn().mockResolvedValue({}),
    unlockReportItem: vi.fn().mockResolvedValue({}),
    updateReportItem: vi.fn().mockResolvedValue({ data: {} })
}))

const group = (type, overrides = {}) => ({
    id: 30,
    attribute: { type, attribute_enums: [] },
    min_occurrence: 0,
    max_occurrence: 10,
    ...overrides
})
const value = (id, raw = '') => ({ id, index: id, value: raw, locked: false, user: null })

function mountStructured(type, values, { edit = false, readOnly = false, enums = [] } = {}) {
    const reactiveValues = reactive(values)
    const wrapper = mountWithPlugins(AttributeStructured, {
        props: {
            attributeGroup: group(type, { attribute: { type, attribute_enums: enums } }),
            values: reactiveValues,
            edit,
            modify: true,
            readOnly,
            reportItemId: edit ? 42 : null
        },
        attachTo: document.body
    })
    return { wrapper, values: reactiveValues }
}

const saves = () =>
    vi
        .mocked(updateReportItem)
        .mock.calls.map(([, data]) => data)
        .filter((data) => data.update)

async function type(wrapper, selector, text) {
    const input = wrapper.find(`[data-test="${selector}"] input`)
    await input.setValue(text)
    return input
}

describe('AttributeStructured', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(AuthService, 'hasPermission').mockReturnValue(true)
        document.body.innerHTML = ''
    })

    it('is what AttributeContainer renders for each structured type', () => {
        for (const type of ['AFFECTED', 'CREDIT', 'TIMELINE', 'RELATIONSHIP', 'REFERENCE', 'JSON']) {
            const wrapper = mountWithPlugins(AttributeContainer, {
                props: { attributeItem: { attribute_group_item: group(type), values: [] }, reportItemId: null, readOnly: true }
            })
            expect(wrapper.findComponent(AttributeStructured).exists(), type).toBe(true)
        }
    })

    it('stores an affected product as JSON with sorted keys while a report is created', async () => {
        const { wrapper, values } = mountStructured('AFFECTED', [value(1)])

        await type(wrapper, 'affected-vendor', 'ExampleVendor')
        await type(wrapper, 'affected-product', 'ExampleProduct')

        expect(values[0].value).toBe('{"product":"ExampleProduct","vendor":"ExampleVendor"}')
        // Nothing is saved before the report exists.
        expect(updateReportItem).not.toHaveBeenCalled()
    })

    it('locks a value once while the focus moves between its fields, and saves it when the focus leaves', async () => {
        const { wrapper, values } = mountStructured('CREDIT', [value(7, '{"value":"Researcher"}')], { edit: true })
        const form = wrapper.find('.structured-form')
        const name = wrapper.find('[data-test="credit-name"] input')
        const user = wrapper.findAll('.structured-form input').at(-1)

        await form.trigger('focusin')
        await name.setValue('Example Researcher')
        // Moving to another field of the same value is not leaving it.
        await form.trigger('focusout', { relatedTarget: user.element })
        await form.trigger('focusin')
        await flushPromises()

        expect(lockReportItem).toHaveBeenCalledTimes(1)
        expect(saves()).toHaveLength(0)

        await form.trigger('focusout', { relatedTarget: null })
        await flushPromises()

        expect(saves()).toEqual([expect.objectContaining({ attribute_id: 7, attribute_value: '{"value":"Example Researcher"}' })])
        expect(unlockReportItem).toHaveBeenCalledTimes(1)
        expect(values[0].value).toBe('{"value":"Example Researcher"}')
    })

    it('leaves an untouched value alone when the focus leaves it', async () => {
        const { wrapper } = mountStructured('RELATIONSHIP', [value(8, '{"destId":"CVE-2026-0001","type":"equal"}')], { edit: true })
        const form = wrapper.find('.structured-form')

        await form.trigger('focusin')
        await form.trigger('focusout', { relatedTarget: null })
        await flushPromises()

        expect(saves()).toHaveLength(0)
    })

    it('saves a picked choice at once', async () => {
        const { wrapper } = mountStructured('CREDIT', [value(9, '{"value":"Researcher"}')], {
            edit: true,
            enums: [{ value: 'finder' }, { value: 'reporter' }]
        })

        wrapper.findComponent('[data-test="credit-role"]').vm.$emit('update:modelValue', 'finder')
        await flushPromises()

        expect(saves()).toEqual([expect.objectContaining({ attribute_id: 9, attribute_value: '{"type":"finder","value":"Researcher"}' })])
    })

    it('gives a version range a numbering scheme, as the CVE Record Format requires', async () => {
        const { wrapper, values } = mountStructured('AFFECTED', [value(1, '{"product":"ExampleProduct","vendor":"ExampleVendor"}')])

        await wrapper.find('[data-test="affected-add-version"]').trigger('click')
        const limit = wrapper.findAllComponents({ name: 'VSelect' }).find((select) => select.props('label') === 'Range')
        limit.vm.$emit('update:modelValue', 'lessThan')
        await flushPromises()

        // The bound is still empty, so it is not stored yet; the scheme is.
        expect(JSON.parse(values[0].value).versions).toEqual([{ status: 'affected', versionType: 'semver' }])
    })

    it('lets a range change status within it, and drops the changes once it is a single version', async () => {
        const range = { version: '1.0', lessThan: '2.0', status: 'affected', versionType: 'semver' }
        const { wrapper, values } = mountStructured('AFFECTED', [value(1, JSON.stringify({ product: 'ExampleProduct', versions: [range] }))])

        await wrapper.find('[data-test="affected-add-change"]').trigger('click')
        await type(wrapper, 'affected-change-at', '1.4.2')

        expect(JSON.parse(values[0].value).versions).toEqual([{ ...range, changes: [{ at: '1.4.2', status: 'unaffected' }] }])

        const limit = wrapper.findAllComponents({ name: 'VSelect' }).find((select) => select.props('label') === 'Range')
        limit.vm.$emit('update:modelValue', '')
        await flushPromises()

        // A single version has no status changes (CVE Record Format), and offers none.
        expect(JSON.parse(values[0].value).versions).toEqual([{ version: '1.0', status: 'affected', versionType: 'semver' }])
        expect(wrapper.find('[data-test="affected-version-changes"]').exists()).toBe(false)
    })

    it('keeps JSON as typed until it is a valid object, and says what is wrong', async () => {
        const { wrapper, values } = mountStructured('JSON', [value(1)])
        const textarea = wrapper.find('[data-test="structured-json"] textarea')

        await textarea.setValue('{"other": ')
        expect(values[0].value).toBe('')
        expect(wrapper.text()).toContain('This is not valid JSON.')

        await textarea.setValue('[1]')
        expect(values[0].value).toBe('')
        expect(wrapper.text()).toContain('This must be a JSON object.')

        await textarea.setValue('{"other": {"type": "ssvc", "content": {}}}')
        expect(values[0].value).toBe('{"other":{"type":"ssvc"}}')
        expect(wrapper.text()).not.toContain('This must be a JSON object.')
    })

    it('shows one line per value where it is only read, a reference as a link', () => {
        const { wrapper } = mountStructured(
            'REFERENCE',
            [value(1, '{"name":"Advisory","url":"https://vendor.example/a"}'), value(2, '{"url":"javascript:alert(1)"}')],
            {
                readOnly: true
            }
        )
        const lines = wrapper.findAll('[data-test="structured-summary"]')

        expect(lines).toHaveLength(2)
        expect(lines[0].find('a').attributes('href')).toBe('https://vendor.example/a')
        expect(lines[0].text()).toBe('Advisory <https://vendor.example/a>')
        // Only http(s) addresses become links.
        expect(lines[1].find('a').exists()).toBe(false)
        expect(wrapper.find('.structured-form').exists()).toBe(false)
    })
})
