import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'

import AttributeString from '@/components/common/attribute/AttributeString.vue'
import AttributeNumber from '@/components/common/attribute/AttributeNumber.vue'
import AttributeText from '@/components/common/attribute/AttributeText.vue'
import AttributeEnum from '@/components/common/attribute/AttributeEnum.vue'
import AttributeRadio from '@/components/common/attribute/AttributeRadio.vue'
import AttributeMultiChoice from '@/components/common/attribute/AttributeMultiChoice.vue'
import AttributeBoolean from '@/components/common/attribute/AttributeBoolean.vue'
import AttributeDate from '@/components/common/attribute/AttributeDate.vue'
import AttributeTime from '@/components/common/attribute/AttributeTime.vue'
import AttributeDateTime from '@/components/common/attribute/AttributeDateTime.vue'
import AttributeTLP from '@/components/common/attribute/AttributeTLP.vue'
import AttributeCVE from '@/components/common/attribute/AttributeCVE.vue'
import AttributeCWE from '@/components/common/attribute/AttributeCWE.vue'
import AttributeCPE from '@/components/common/attribute/AttributeCPE.vue'
import AttributeCVSS from '@/components/common/attribute/AttributeCVSS.vue'
import AttributeRichText from '@/components/common/attribute/AttributeRichText.vue'
import AttributeAttachment from '@/components/common/attribute/AttributeAttachment.vue'
import AuthService from '@/services/auth_service'
import { removeAttachment, updateAttachmentDescription, uploadAttachment, updateReportItem } from '@/api/analyze'

// ── API mocks (prevent network calls from useAttributes) ─────────────────────
vi.mock('@/api/analyze', () => ({
    getReportItemData: vi.fn().mockResolvedValue({ data: {} }),
    holdLockReportItem: vi.fn().mockResolvedValue({}),
    lockReportItem: vi.fn().mockResolvedValue({}),
    unlockReportItem: vi.fn().mockResolvedValue({}),
    updateReportItem: vi.fn().mockResolvedValue({}),
    getAttributeEnums: vi.fn().mockResolvedValue({ data: { items: [], total_count: 0 } }),
    downloadAttachment: vi.fn().mockResolvedValue({}),
    removeAttachment: vi.fn().mockResolvedValue({}),
    updateAttachmentDescription: vi.fn().mockResolvedValue({ data: {} }),
    uploadAttachment: vi.fn().mockResolvedValue({ data: { attribute_id: 99 } })
}))

// Stub layout sub-components so we don't need to wire up their Pinia deps
const AttributeItemLayoutStub = {
    name: 'AttributeItemLayout',
    props: ['addButton', 'values'],
    template: '<div class="item-layout-stub"><slot name="content" /></div>',
    emits: ['add-value']
}

const AttributeValueLayoutStub = {
    name: 'AttributeValueLayout',
    props: ['delButton', 'occurrence', 'values', 'valIndex'],
    template: '<div class="value-layout-stub"><slot name="col_left" /><slot name="col_middle" /><slot name="col_right" /></div>',
    emits: ['del-value']
}

// Stub PrimeVue Editor (used by AttributeRichText only)
const EditorStub = {
    name: 'Editor',
    props: ['modelValue', 'readonly', 'placeholder'],
    template: '<div class="editor-stub"><slot /></div>',
    emits: ['update:modelValue']
}

// Stub CalculatorCVSS (used by AttributeCVSS only)
const CalculatorCVSSStub = {
    name: 'CalculatorCVSS',
    props: ['modelValue', 'disabled'],
    template: '<div class="calculator-stub" />',
    emits: ['update:modelValue']
}

const DialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div class="dialog-stub"><slot /></div>',
    emits: ['update:modelValue']
}

const EnumSelectorStub = {
    name: 'EnumSelector',
    props: ['attributeId', 'valueIndex', 'disabled'],
    template: '<button class="enum-selector-stub" :disabled="disabled" />',
    emits: ['enum-selected']
}

const globalStubs = {
    AttributeItemLayout: AttributeItemLayoutStub,
    AttributeValueLayout: AttributeValueLayoutStub,
    Editor: EditorStub,
    CalculatorCVSS: CalculatorCVSSStub,
    VDialog: DialogStub,
    EnumSelector: EnumSelectorStub
}

// ── Shared prop factories ─────────────────────────────────────────────────────

function makeAttributeGroup(overrides = {}) {
    return {
        id: 'ag-1',
        attribute: { type: 'STRING' },
        min_occurrence: 0,
        max_occurrence: 10,
        ...overrides
    }
}

function makeValue(overrides = {}) {
    return {
        id: 1,
        index: 0,
        value: 'test-value',
        locked: false,
        remote: false,
        user: null,
        last_updated: null,
        ...overrides
    }
}

function baseProps(valueOverrides = {}, groupOverrides = {}) {
    return {
        attributeGroup: makeAttributeGroup(groupOverrides),
        values: [makeValue(valueOverrides)],
        readOnly: false,
        edit: true,
        modify: false,
        reportItemId: 42
    }
}

function readOnlyProps(valueOverrides = {}) {
    return { ...baseProps(valueOverrides), readOnly: true, edit: false }
}

function mountAttr(component, props = {}, extraGlobal = {}) {
    return mountWithPlugins(component, {
        props,
        global: {
            stubs: globalStubs,
            ...extraGlobal
        }
    })
}

// ── AttributeString ───────────────────────────────────────────────────────────

describe('AttributeString', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        const wrapper = mountAttr(AttributeString, baseProps())
        expect(wrapper.exists()).toBe(true)
    })

    it('shows read-only value as text', () => {
        const wrapper = mountAttr(AttributeString, readOnlyProps({ value: 'hello world' }))
        expect(wrapper.text()).toContain('hello world')
        expect(wrapper.find('.numbered-string-value').exists()).toBe(true)
    })

    it('shows editable text field when edit=true', () => {
        const wrapper = mountAttr(AttributeString, baseProps())
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })

    it('hides editable field when readOnly=true', () => {
        const wrapper = mountAttr(AttributeString, readOnlyProps())
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(false)
    })

    it('numbers values when there are multiple', () => {
        const props = {
            ...readOnlyProps(),
            values: [makeValue({ value: 'first' }), makeValue({ id: 2, index: 1, value: 'second' })]
        }
        const wrapper = mountAttr(AttributeString, props)
        expect(wrapper.text()).toContain('1.')
        expect(wrapper.text()).toContain('2.')
    })

    it('shows reorder controls (drag handle + arrows) when there are multiple editable values', () => {
        const props = {
            ...baseProps(),
            values: [makeValue({ value: 'first' }), makeValue({ id: 2, index: 1, value: 'second' })]
        }
        const wrapper = mountAttr(AttributeString, props)
        expect(wrapper.findAll('.reorder-controls').length).toBe(2)
        expect(wrapper.find('.drag-handle').exists()).toBe(true)
        expect(wrapper.findAll('.reorder-arrows').length).toBe(2)
    })

    it('does not show reorder controls for a single value', () => {
        const wrapper = mountAttr(AttributeString, baseProps())
        expect(wrapper.find('.reorder-controls').exists()).toBe(false)
    })

    it('renders a read-only URL value as a link opening in a new tab', () => {
        const wrapper = mountAttr(AttributeString, readOnlyProps({ value: 'https://example.com/path' }))
        const link = wrapper.find('.string-content a')
        expect(link.exists()).toBe(true)
        expect(link.attributes('href')).toBe('https://example.com/path')
        expect(link.attributes('target')).toBe('_blank')
        expect(link.attributes('rel')).toContain('noopener')
    })

    it('renders a non-URL read-only value as plain text (no link)', () => {
        const wrapper = mountAttr(AttributeString, readOnlyProps({ value: 'not a url' }))
        expect(wrapper.find('.string-content a').exists()).toBe(false)
        expect(wrapper.text()).toContain('not a url')
    })

    it('shows an open-link button when an editable value is a URL', () => {
        const wrapper = mountAttr(AttributeString, baseProps({ value: 'https://example.com' }))
        expect(wrapper.find('a[href="https://example.com"][target="_blank"]').exists()).toBe(true)
    })

    it('does not show an open-link button when an editable value is not a URL', () => {
        const wrapper = mountAttr(AttributeString, baseProps({ value: 'plain text' }))
        expect(wrapper.find('a[target="_blank"]').exists()).toBe(false)
    })
})

// ── AttributeNumber ───────────────────────────────────────────────────────────

describe('AttributeNumber', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeNumber, baseProps()).exists()).toBe(true)
    })

    it('shows read-only numeric value', () => {
        const wrapper = mountAttr(AttributeNumber, readOnlyProps({ value: 42 }))
        expect(wrapper.text()).toContain('42')
        expect(wrapper.find('.numbered-value').exists()).toBe(true)
    })

    it('locale-formats zero and large numbers without mutating raw values, while null stays empty', async () => {
        const values = [makeValue({ value: 0 }), makeValue({ id: 2, index: 1, value: 12345.6 }), makeValue({ id: 3, index: 2, value: null })]
        const wrapper = mountAttr(AttributeNumber, { ...readOnlyProps(), values })
        wrapper.vm.$i18n.locale = 'de-DE'
        await wrapper.vm.$nextTick()

        expect(wrapper.findAll('.number-content').map((value) => value.text())).toEqual([
            new Intl.NumberFormat('de-DE').format(0),
            new Intl.NumberFormat('de-DE').format(12345.6),
            ''
        ])
        expect(values.map((value) => value.value)).toEqual([0, 12345.6, null])
    })

    it('shows VTextField in edit mode', () => {
        const wrapper = mountAttr(AttributeNumber, baseProps())
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })
})

// ── AttributeText ─────────────────────────────────────────────────────────────

describe('AttributeText', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeText, baseProps()).exists()).toBe(true)
    })

    it('shows read-only text', () => {
        const wrapper = mountAttr(AttributeText, readOnlyProps({ value: 'long text here' }))
        expect(wrapper.text()).toContain('long text here')
        expect(wrapper.find('.numbered-text-value').exists()).toBe(true)
    })

    it('shows VTextarea in edit mode', () => {
        const wrapper = mountAttr(AttributeText, baseProps())
        expect(wrapper.findComponent({ name: 'VTextarea' }).exists()).toBe(true)
    })

    it('hides editable field when readOnly=true', () => {
        const wrapper = mountAttr(AttributeText, readOnlyProps())
        expect(wrapper.findComponent({ name: 'VTextarea' }).exists()).toBe(false)
    })

    it('numbers values when there are multiple', () => {
        const props = {
            ...readOnlyProps(),
            values: [makeValue({ value: 'first' }), makeValue({ id: 2, index: 1, value: 'second' })]
        }
        const wrapper = mountAttr(AttributeText, props)
        expect(wrapper.text()).toContain('1.')
        expect(wrapper.text()).toContain('2.')
    })

    it('shows reorder controls (drag handle + arrows) when there are multiple editable values', () => {
        const props = {
            ...baseProps(),
            values: [makeValue({ value: 'first' }), makeValue({ id: 2, index: 1, value: 'second' })]
        }
        const wrapper = mountAttr(AttributeText, props)
        expect(wrapper.findAll('.reorder-controls').length).toBe(2)
        expect(wrapper.find('.drag-handle').exists()).toBe(true)
        expect(wrapper.findAll('.reorder-arrows').length).toBe(2)
    })

    it('does not show reorder controls for a single value', () => {
        const wrapper = mountAttr(AttributeText, baseProps())
        expect(wrapper.find('.reorder-controls').exists()).toBe(false)
    })
})

// ── AttributeEnum ─────────────────────────────────────────────────────────────

describe('AttributeEnum', () => {
    beforeEach(() => setActivePinia(createPinia()))

    const enumGroup = makeAttributeGroup({
        attribute: {
            type: 'ENUM',
            enum_items: [
                { id: 1, value: 'option-a' },
                { id: 2, value: 'option-b' }
            ]
        }
    })

    it('renders without error', () => {
        expect(mountAttr(AttributeEnum, baseProps({}, enumGroup)).exists()).toBe(true)
    })

    it('shows read-only enum value', () => {
        const wrapper = mountAttr(AttributeEnum, { ...readOnlyProps({ value: 'option-a' }), attributeGroup: enumGroup })
        expect(wrapper.text()).toContain('option-a')
        expect(wrapper.find('.enum-value').exists()).toBe(true)
    })

    it('shows VSelect in edit mode', () => {
        const wrapper = mountAttr(AttributeEnum, { ...baseProps({}, enumGroup), attributeGroup: enumGroup })
        expect(wrapper.findComponent({ name: 'VSelect' }).exists()).toBe(true)
    })

    it('offers the constants the backend sends as attribute_enums', () => {
        const backendEnumGroup = makeAttributeGroup({
            attribute: {
                type: 'ENUM',
                attribute_enums: [
                    { id: 1, index: 0, value: 'High', description: '' },
                    { id: 2, index: 1, value: 'Medium', description: '' },
                    { id: 3, index: 2, value: 'Low', description: '' }
                ]
            }
        })

        const wrapper = mountAttr(AttributeEnum, { ...baseProps({}, backendEnumGroup), attributeGroup: backendEnumGroup })
        const select = wrapper.findComponent({ name: 'VSelect' })

        expect(select.props('items')).toEqual([
            { title: 'High', value: 'High' },
            { title: 'Medium', value: 'Medium' },
            { title: 'Low', value: 'Low' }
        ])
    })

    it('falls back to the enum_items key', () => {
        const wrapper = mountAttr(AttributeEnum, { ...baseProps({}, enumGroup), attributeGroup: enumGroup })
        expect(wrapper.findComponent({ name: 'VSelect' }).props('items')).toEqual([
            { title: 'option-a', value: 'option-a' },
            { title: 'option-b', value: 'option-b' }
        ])
    })
})

// ── AttributeRadio ────────────────────────────────────────────────────────────

describe('AttributeRadio', () => {
    beforeEach(() => setActivePinia(createPinia()))

    const radioGroup = makeAttributeGroup({
        attribute: {
            type: 'RADIO',
            enum_items: [
                { id: 1, value: 'yes' },
                { id: 2, value: 'no' }
            ]
        }
    })

    it('renders without error', () => {
        expect(mountAttr(AttributeRadio, { ...baseProps(), attributeGroup: radioGroup }).exists()).toBe(true)
    })

    it('shows read-only radio value', () => {
        const wrapper = mountAttr(AttributeRadio, { ...readOnlyProps({ value: 'yes' }), attributeGroup: radioGroup })
        expect(wrapper.text()).toContain('yes')
        expect(wrapper.find('.radio-value').exists()).toBe(true)
    })

    it('shows VRadioGroup in edit mode', () => {
        const wrapper = mountAttr(AttributeRadio, { ...baseProps(), attributeGroup: radioGroup })
        expect(wrapper.findComponent({ name: 'VRadioGroup' }).exists()).toBe(true)
    })

    it('colours the radio buttons so a selected option reads as selected', () => {
        const wrapper = mountAttr(AttributeRadio, { ...baseProps(), attributeGroup: radioGroup })
        expect(wrapper.findComponent({ name: 'VRadio' }).props('color')).toBe('primary')
    })

    it('renders selectable radio options from backend attribute_enums', () => {
        const backendRadioGroup = makeAttributeGroup({
            attribute: {
                type: 'RADIO',
                attribute_enums: [
                    { id: 1, index: 0, value: 'UNRESTRICTED' },
                    { id: 2, index: 1, value: 'CLASSIFIED' }
                ]
            }
        })

        const wrapper = mountAttr(AttributeRadio, { ...baseProps(), attributeGroup: backendRadioGroup })
        const radios = wrapper.findAllComponents({ name: 'VRadio' })

        expect(radios.length).toBe(2)
    })
})

// ── AttributeMultiChoice ──────────────────────────────────────────────────────

describe('AttributeMultiChoice', () => {
    beforeEach(() => setActivePinia(createPinia()))

    const multiChoiceGroup = makeAttributeGroup({
        attribute: {
            type: 'MULTI_CHOICE',
            attribute_enums: [
                { id: 1, index: 0, value: 'Option A' },
                { id: 2, index: 1, value: 'Option B' },
                { id: 3, index: 2, value: 'Option C' }
            ]
        }
    })

    const multiChoiceProps = (valueOverrides = {}) => ({
        ...baseProps(valueOverrides),
        attributeGroup: multiChoiceGroup
    })

    it('renders without error', () => {
        expect(mountAttr(AttributeMultiChoice, multiChoiceProps({ value: '' })).exists()).toBe(true)
    })

    it('colours the checkboxes so a ticked option reads as ticked', () => {
        const wrapper = mountAttr(AttributeMultiChoice, multiChoiceProps({ value: '' }))
        expect(wrapper.findComponent({ name: 'VCheckbox' }).props('color')).toBe('primary')
    })

    it('renders one checkbox per backend attribute_enum', () => {
        const wrapper = mountAttr(AttributeMultiChoice, multiChoiceProps({ value: '' }))
        expect(wrapper.findAllComponents({ name: 'VCheckbox' }).length).toBe(3)
    })

    it('shows the selected values as chips when read-only', () => {
        const wrapper = mountAttr(AttributeMultiChoice, {
            ...readOnlyProps({ value: 'Option A\nOption C' }),
            attributeGroup: multiChoiceGroup
        })

        expect(wrapper.find('.multi-choice-value').exists()).toBe(true)
        expect(wrapper.text()).toContain('Option A')
        expect(wrapper.text()).toContain('Option C')
        expect(wrapper.text()).not.toContain('Option B')
    })

    it('ticks the checkboxes matching the stored value', () => {
        const wrapper = mountAttr(AttributeMultiChoice, multiChoiceProps({ value: 'Option A\nOption C' }))
        const checked = wrapper.findAllComponents({ name: 'VCheckbox' }).map((box) => box.props('modelValue'))

        expect(checked).toEqual([true, false, true])
    })

    it('joins ticked values in constant order, not click order', async () => {
        const props = multiChoiceProps({ value: '' })
        const wrapper = mountAttr(AttributeMultiChoice, props)
        const boxes = wrapper.findAllComponents({ name: 'VCheckbox' })

        await boxes[2].vm.$emit('update:modelValue', true)
        await boxes[0].vm.$emit('update:modelValue', true)
        await flushPromises()

        expect(props.values[0].value).toBe('Option A\nOption C')
    })

    it('removes only the unticked value', async () => {
        const props = multiChoiceProps({ value: 'Option A\nOption B\nOption C' })
        const wrapper = mountAttr(AttributeMultiChoice, props)

        await wrapper.findAllComponents({ name: 'VCheckbox' })[1].vm.$emit('update:modelValue', false)
        await flushPromises()

        expect(props.values[0].value).toBe('Option A\nOption C')
    })

    it('persists an empty value when the last box is unticked', async () => {
        const props = multiChoiceProps({ value: 'Option B' })
        const wrapper = mountAttr(AttributeMultiChoice, props)

        await wrapper.findAllComponents({ name: 'VCheckbox' })[1].vm.$emit('update:modelValue', false)
        await flushPromises()

        expect(props.values[0].value).toBe('')
        expect(updateReportItem).toHaveBeenCalled()
    })
})

// ── AttributeBoolean ──────────────────────────────────────────────────────────

describe('AttributeBoolean', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeBoolean, baseProps({ value: true })).exists()).toBe(true)
    })

    it('shows read-only boolean — true shows check icon', () => {
        const wrapper = mountAttr(AttributeBoolean, readOnlyProps({ value: true }))
        expect(wrapper.find('.boolean-value').exists()).toBe(true)
        expect(wrapper.html()).toContain('mdi-check-circle')
    })

    it('shows read-only boolean — false shows close icon', () => {
        const wrapper = mountAttr(AttributeBoolean, readOnlyProps({ value: false }))
        expect(wrapper.html()).toContain('mdi-close-circle')
    })

    it('shows VSwitch in edit mode', () => {
        const wrapper = mountAttr(AttributeBoolean, baseProps({ value: true }))
        expect(wrapper.findComponent({ name: 'VSwitch' }).exists()).toBe(true)
    })

    it('colours the switch so the on state is visible', () => {
        // Vuetify keeps the track in the default grey unless a colour is given, which made the
        // toggle look identical whether it was on or off.
        const wrapper = mountAttr(AttributeBoolean, baseProps({ value: true }))
        expect(wrapper.findComponent({ name: 'VSwitch' }).props('color')).toBe('primary')
    })
})

// ── AttributeDate ─────────────────────────────────────────────────────────────

describe('AttributeDate', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeDate, baseProps({ value: '2024-01-15' })).exists()).toBe(true)
    })

    it('locale-formats a date without mutating it and uses automatic direction for Arabic output', async () => {
        const props = readOnlyProps({ value: '2024-01-15' })
        const wrapper = mountAttr(AttributeDate, props)
        wrapper.vm.$i18n.locale = 'ar'
        await wrapper.vm.$nextTick()

        expect(wrapper.get('.date-value bdi').attributes('dir')).toBe('auto')
        expect(wrapper.get('.date-value bdi').text()).toBe(
            new Intl.DateTimeFormat('ar', { dateStyle: 'medium' }).format(new Date(2024, 0, 15))
        )
        expect(props.values[0].value).toBe('2024-01-15')
    })

    it.each([
        ['invalid-date', 'invalid-date'],
        [null, '']
    ])('preserves the date display fallback for %s', (rawValue, expected) => {
        const props = readOnlyProps({ value: rawValue })
        const wrapper = mountAttr(AttributeDate, props)

        expect(wrapper.get('.date-value bdi').text()).toBe(expected)
        expect(props.values[0].value).toBe(rawValue)
    })

    it('shows VTextField in edit mode', () => {
        const wrapper = mountAttr(AttributeDate, baseProps({ value: '2024-01-15' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })
})

// ── AttributeTime ─────────────────────────────────────────────────────────────

describe('AttributeTime', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeTime, baseProps({ value: '14:30' })).exists()).toBe(true)
    })

    it('shows read-only time value', () => {
        const wrapper = mountAttr(AttributeTime, readOnlyProps({ value: '14:30' }))
        expect(wrapper.text()).toContain('14:30')
        expect(wrapper.find('.time-value').exists()).toBe(true)
    })

    it('shows VTextField in edit mode', () => {
        const wrapper = mountAttr(AttributeTime, baseProps({ value: '14:30' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })
})

// ── AttributeDateTime ─────────────────────────────────────────────────────────

describe('AttributeDateTime', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeDateTime, baseProps({ value: '2024-01-15T14:30' })).exists()).toBe(true)
    })

    it('locale-formats a datetime instant without mutating it and uses automatic direction for Arabic output', async () => {
        const rawValue = '2024-01-15T14:30:00Z'
        const props = readOnlyProps({ value: rawValue })
        const wrapper = mountAttr(AttributeDateTime, props)
        wrapper.vm.$i18n.locale = 'ar'
        await wrapper.vm.$nextTick()

        expect(wrapper.get('.datetime-value bdi').attributes('dir')).toBe('auto')
        expect(wrapper.get('.datetime-value bdi').text()).toBe(
            new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawValue))
        )
        expect(props.values[0].value).toBe(rawValue)
    })

    it.each([
        ['invalid-datetime', 'invalid-datetime'],
        [null, '–']
    ])('preserves the datetime display fallback for %s', (rawValue, expected) => {
        const props = readOnlyProps({ value: rawValue })
        const wrapper = mountAttr(AttributeDateTime, props)

        expect(wrapper.get('.datetime-value bdi').text()).toBe(expected)
        expect(props.values[0].value).toBe(rawValue)
    })

    it('shows VTextField in edit mode', () => {
        const wrapper = mountAttr(AttributeDateTime, baseProps({ value: '2024-01-15T14:30' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })
})

// ── AttributeTLP ──────────────────────────────────────────────────────────────

describe('AttributeTLP', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeTLP, baseProps({ value: 'GREEN' })).exists()).toBe(true)
    })

    it('shows read-only TLP badge', () => {
        const wrapper = mountAttr(AttributeTLP, readOnlyProps({ value: 'RED' }))
        expect(wrapper.find('.tlp-display').exists()).toBe(true)
        expect(wrapper.find('.tlp-badge').exists()).toBe(true)
        expect(wrapper.text()).toContain('RED')
    })

    it('shows TLP buttons in edit mode', () => {
        const wrapper = mountAttr(AttributeTLP, baseProps({ value: 'CLEAR' }))
        expect(wrapper.find('.tlp-options').exists()).toBe(true)
        const buttons = wrapper.findAll('.tlp-button')
        expect(buttons.length).toBe(5) // CLEAR, GREEN, AMBER, AMBER+STRICT, RED
    })

    it('renders TLP buttons with type="button" so they never submit a parent form', () => {
        const wrapper = mountAttr(AttributeTLP, baseProps({ value: 'CLEAR' }))
        const buttons = wrapper.findAll('.tlp-button')
        expect(buttons.length).toBe(5)
        buttons.forEach((btn) => {
            expect(btn.attributes('type')).toBe('button')
        })
    })

    it('shows TLP description in read-only mode', () => {
        const wrapper = mountAttr(AttributeTLP, readOnlyProps({ value: 'GREEN' }))
        expect(wrapper.find('.tlp-description').exists()).toBe(true)
    })
})

// ── AttributeCVE ──────────────────────────────────────────────────────────────

describe('AttributeCVE', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeCVE, baseProps({ value: 'CVE-2024-1234' })).exists()).toBe(true)
    })

    it('shows read-only CVE value', () => {
        const wrapper = mountAttr(AttributeCVE, readOnlyProps({ value: 'CVE-2024-1234' }))
        expect(wrapper.find('.numbered-cve-value').exists()).toBe(true)
        expect(wrapper.text()).toContain('CVE-2024-1234')
    })

    it('shows editable text field in edit mode', () => {
        const wrapper = mountAttr(AttributeCVE, baseProps({ value: 'CVE-2024-1234' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })

    it('offers enum lookup in editable mode and applies the selected occurrence', async () => {
        const props = baseProps({ value: 'CVE-2024-1234' }, { attribute: { id: 17, type: 'CVE' } })
        const wrapper = mountAttr(AttributeCVE, props)
        const selector = wrapper.findComponent(EnumSelectorStub)

        expect(selector.props()).toMatchObject({ attributeId: 17, valueIndex: 0, disabled: false })
        selector.vm.$emit('enum-selected', { index: 0, value: 'CVE-2026-12345', value_description: 'Example CVE' })
        await flushPromises()

        expect(props.values[0]).toMatchObject({ value: 'CVE-2026-12345', value_description: 'Example CVE' })
    })

    it('does not offer enum lookup for read-only values', () => {
        const wrapper = mountAttr(AttributeCVE, readOnlyProps({ value: 'CVE-2024-1234' }))
        expect(wrapper.findComponent(EnumSelectorStub).exists()).toBe(false)
    })
})

// ── AttributeCWE ──────────────────────────────────────────────────────────────

describe('AttributeCWE', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeCWE, baseProps({ value: 'CWE-79' })).exists()).toBe(true)
    })

    it('shows read-only CWE value', () => {
        const wrapper = mountAttr(AttributeCWE, readOnlyProps({ value: 'CWE-79' }))
        expect(wrapper.find('.numbered-cwe-value').exists()).toBe(true)
        expect(wrapper.text()).toContain('CWE-79')
    })

    it('shows editable text field in edit mode', () => {
        const wrapper = mountAttr(AttributeCWE, baseProps({ value: 'CWE-79' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })

    it('offers enum lookup and disables it while the occurrence is locked', () => {
        const props = baseProps({ value: 'CWE-79', locked: true }, { attribute: { id: 18, type: 'CWE' } })
        const wrapper = mountAttr(AttributeCWE, props)
        const selector = wrapper.findComponent(EnumSelectorStub)

        expect(selector.props()).toMatchObject({ attributeId: 18, valueIndex: 0, disabled: true })
    })
})

// ── AttributeCPE ──────────────────────────────────────────────────────────────

describe('AttributeCPE', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeCPE, baseProps({ value: 'cpe:/a:vendor:product:1.0' })).exists()).toBe(true)
    })

    it('shows read-only CPE value', () => {
        const wrapper = mountAttr(AttributeCPE, readOnlyProps({ value: 'cpe:/a:vendor:product:1.0' }))
        expect(wrapper.find('.numbered-cpe-value').exists()).toBe(true)
        expect(wrapper.text()).toContain('cpe:/a:vendor:product:1.0')
    })

    it('shows editable text field in edit mode', () => {
        const wrapper = mountAttr(AttributeCPE, baseProps({ value: 'cpe:/a:vendor:product:1.0' }))
        expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
    })

    it('offers the same enum lookup for CPE attributes', () => {
        const props = baseProps({ value: 'cpe:/a:vendor:product:1.0' }, { attribute: { id: 19, type: 'CPE' } })
        const wrapper = mountAttr(AttributeCPE, props)

        expect(wrapper.findComponent(EnumSelectorStub).props()).toMatchObject({
            attributeId: 19,
            valueIndex: 0,
            disabled: false
        })
    })
})

// ── AttributeCVSS ─────────────────────────────────────────────────────────────

describe('AttributeCVSS', () => {
    beforeEach(() => setActivePinia(createPinia()))

    const cvssVector = 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H'

    it('renders without error', () => {
        expect(mountAttr(AttributeCVSS, baseProps({ value: cvssVector })).exists()).toBe(true)
    })

    it('shows read-only CVSS value', () => {
        const wrapper = mountAttr(AttributeCVSS, readOnlyProps({ value: cvssVector }))
        expect(wrapper.find('.numbered-cvss-value').exists()).toBe(true)
        expect(wrapper.text()).toContain(cvssVector)
        expect(wrapper.get('bdi[dir="ltr"]').text()).toBe(cvssVector)
    })

    it('shows VTextField and calculator in edit mode', () => {
        const wrapper = mountAttr(AttributeCVSS, baseProps({ value: cvssVector }))
        const field = wrapper.findComponent({ name: 'VTextField' })
        expect(field.exists()).toBe(true)
        expect(field.props('label')).toBe('CVSS vector and score')
        expect(wrapper.get('input').attributes('dir')).toBe('ltr')
        expect(wrapper.findComponent({ name: 'CalculatorCVSS' }).exists()).toBe(true)
    })
})

// ── AttributeRichText ─────────────────────────────────────────────────────────

describe('AttributeRichText', () => {
    beforeEach(() => setActivePinia(createPinia()))

    it('renders without error', () => {
        expect(mountAttr(AttributeRichText, baseProps({ value: '<p>Hello</p>' })).exists()).toBe(true)
    })

    it('shows read-only rich text display', () => {
        const wrapper = mountAttr(AttributeRichText, readOnlyProps({ value: '<p>Hello</p>' }))
        expect(wrapper.find('.richtext-display').exists()).toBe(true)
    })

    it('shows Editor component in edit mode', () => {
        const wrapper = mountAttr(AttributeRichText, baseProps({ value: '<p>Hello</p>' }))
        const editor = wrapper.findComponent({ name: 'Editor' })
        expect(editor.exists()).toBe(true)
        expect(editor.props('placeholder')).toBe('Enter rich text')
    })
})

// ── AttributeAttachment ───────────────────────────────────────────────────────

describe('AttributeAttachment', () => {
    beforeEach(() => {
        setActivePinia(createPinia())
        vi.clearAllMocks()
        vi.spyOn(AuthService, 'hasPermission').mockReturnValue(true)
    })

    const attachmentValue = {
        id: 10,
        index: 0,
        value: 'document.pdf',
        file_name: 'document.pdf',
        locked: false,
        remote: false,
        user: null,
        last_updated: null
    }

    it('renders without error', () => {
        expect(mountAttr(AttributeAttachment, baseProps(attachmentValue)).exists()).toBe(true)
    })

    it('shows read-only attachment display', () => {
        const wrapper = mountAttr(AttributeAttachment, readOnlyProps(attachmentValue))
        expect(wrapper.find('.attachment-row').exists()).toBe(true)
        expect(wrapper.find('.attachment-dropzone').exists()).toBe(false)
    })

    it('locale-formats attachment metadata and bidi-isolates dynamic values without mutating payload data', async () => {
        const rawTimestamp = '2026-08-09T17:30:00.000Z'
        const value = {
            ...attachmentValue,
            value: 'دليل.pdf',
            binary_description: 'وصف الدليل',
            binary_mime_type: 'application/pdf',
            binary_size: 1536,
            last_updated: rawTimestamp,
            user: { name: 'المحلل' }
        }
        const wrapper = mountAttr(AttributeAttachment, readOnlyProps(value))

        wrapper.vm.$i18n.locale = 'ar'
        await wrapper.vm.$nextTick()

        expect(wrapper.get('.attachment-row__name').attributes('dir')).toBe('auto')
        expect(wrapper.get('.attachment-row__description').attributes('dir')).toBe('auto')
        const metadataTokens = wrapper.findAll('.attachment-row__meta > bdi')
        expect(metadataTokens.map((token) => token.attributes('dir'))).toEqual(['ltr', 'ltr'])
        expect(metadataTokens.map((token) => token.text())).toEqual([
            'application/pdf',
            `${new Intl.NumberFormat('ar', { maximumFractionDigits: 2 }).format(1.5)} KiB`
        ])
        const expectedTimestamp = new Intl.DateTimeFormat('ar', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(rawTimestamp))
        expect(wrapper.vm.formatAttachmentTimestamp(rawTimestamp)).toBe(expectedTimestamp)
        expect(wrapper.findAll('bdi[dir="auto"]').map((token) => token.text())).toContain(expectedTimestamp)
        expect(value).toMatchObject({ binary_size: 1536, last_updated: rawTimestamp, user: { name: 'المحلل' } })
    })

    it('preserves an unparseable legacy timestamp for display', () => {
        const rawTimestamp = 'وقت قديم'
        const value = { ...attachmentValue, last_updated: rawTimestamp }
        const wrapper = mountAttr(AttributeAttachment, readOnlyProps(value))

        expect(wrapper.vm.formatAttachmentTimestamp(rawTimestamp)).toBe(rawTimestamp)
        expect(wrapper.findAll('bdi[dir="auto"]').map((token) => token.text())).toContain(rawTimestamp)
        expect(value.last_updated).toBe(rawTimestamp)
    })

    it('shows editable layout in edit mode', () => {
        const wrapper = mountAttr(AttributeAttachment, { ...baseProps(attachmentValue), modify: true })
        expect(wrapper.find('.attachment-row').exists()).toBe(true)
        expect(wrapper.find('.attachment-dropzone').exists()).toBe(true)
    })

    it('queues a selected file with its description while creating a report', async () => {
        const props = {
            ...baseProps({}, { attribute: { type: 'ATTACHMENT' } }),
            values: [],
            edit: false,
            modify: true,
            reportItemId: null
        }
        const wrapper = mountAttr(AttributeAttachment, props)
        const file = new File(['contents'], 'evidence.txt', { type: 'text/plain' })

        wrapper.vm.acceptFiles([file])
        await wrapper.vm.$nextTick()
        wrapper.vm.descriptionDraft = 'Collected evidence'
        await wrapper.vm.confirmDescription()

        expect(props.values).toHaveLength(1)
        expect(props.values[0]).toMatchObject({
            value: 'evidence.txt',
            binary_description: 'Collected evidence',
            binary_mime_type: 'text/plain',
            binary_size: 8,
            file
        })
        expect(uploadAttachment).not.toHaveBeenCalled()
    })

    it('uploads a selected file immediately for an existing report', async () => {
        const props = {
            ...baseProps({}, { attribute: { type: 'ATTACHMENT' } }),
            values: [],
            modify: true
        }
        const wrapper = mountAttr(AttributeAttachment, props)
        const file = new File(['contents'], 'evidence.txt', { type: 'text/plain' })

        wrapper.vm.acceptFiles([file])
        await wrapper.vm.$nextTick()
        wrapper.vm.descriptionDraft = 'Collected evidence'
        await wrapper.vm.confirmDescription()

        expect(uploadAttachment).toHaveBeenCalledWith(42, 'ag-1', file, 'Collected evidence')
        expect(props.values[0]).toMatchObject({ id: 99, value: 'evidence.txt', binary_description: 'Collected evidence' })
        expect(props.values[0].file).toBeUndefined()
    })

    it('updates an existing attachment description', async () => {
        updateAttachmentDescription.mockResolvedValueOnce({ data: { binary_description: 'Updated description' } })
        const props = { ...baseProps({ ...attachmentValue, binary_description: 'Old description' }), modify: true }
        const wrapper = mountAttr(AttributeAttachment, props)

        wrapper.vm.openDescriptionEditor(props.values[0])
        wrapper.vm.descriptionDraft = 'Updated description'
        await wrapper.vm.confirmDescription()

        expect(updateAttachmentDescription).toHaveBeenCalledWith({
            report_item_id: 42,
            attribute_id: 10,
            description: 'Updated description'
        })
        expect(props.values[0].binary_description).toBe('Updated description')
    })

    it('deletes an existing attachment after confirmation', async () => {
        const props = { ...baseProps(attachmentValue), modify: true }
        const wrapper = mountAttr(AttributeAttachment, props)

        wrapper.vm.selectedValue = props.values[0]
        await wrapper.vm.deleteSelectedAttachment()

        expect(removeAttachment).toHaveBeenCalledWith({ report_item_id: 42, attribute_id: 10 })
        expect(props.values).toHaveLength(0)
    })
})

// ── min_occurrence seeding (shared useAttributes hook) ────────────────────────

describe('min_occurrence seeding on mount', () => {
    beforeEach(() => setActivePinia(createPinia()))

    // Every editable attribute type seeds the rows its attribute group requires. Types are
    // listed explicitly (rather than derived) so a new type without the hook is a failure here.
    const seedingTypes = [
        ['AttributeString', AttributeString],
        ['AttributeText', AttributeText],
        ['AttributeEnum', AttributeEnum],
        ['AttributeRadio', AttributeRadio],
        ['AttributeMultiChoice', AttributeMultiChoice],
        ['AttributeBoolean', AttributeBoolean],
        ['AttributeNumber', AttributeNumber],
        ['AttributeDate', AttributeDate],
        ['AttributeTime', AttributeTime],
        ['AttributeDateTime', AttributeDateTime],
        ['AttributeRichText', AttributeRichText],
        ['AttributeTLP', AttributeTLP],
        ['AttributeCVE', AttributeCVE],
        ['AttributeCWE', AttributeCWE],
        ['AttributeCPE', AttributeCPE],
        ['AttributeCVSS', AttributeCVSS]
    ]

    const emptyProps = (minOccurrence) => ({
        ...baseProps(),
        values: [],
        attributeGroup: makeAttributeGroup({ min_occurrence: minOccurrence, max_occurrence: 10 })
    })

    it.each(seedingTypes)('%s seeds one value per min_occurrence', async (_name, component) => {
        const props = emptyProps(2)
        mountAttr(component, props)
        await flushPromises()
        expect(props.values).toHaveLength(2)
    })

    it.each(seedingTypes)('%s seeds nothing when min_occurrence is 0', async (_name, component) => {
        const props = emptyProps(0)
        mountAttr(component, props)
        await flushPromises()
        expect(props.values).toHaveLength(0)
    })

    it.each(seedingTypes)('%s seeds nothing for a label-only attribute (max_occurrence 0)', async (_name, component) => {
        const props = {
            ...baseProps(),
            values: [],
            attributeGroup: makeAttributeGroup({ min_occurrence: 0, max_occurrence: 0 })
        }
        mountAttr(component, props)
        await flushPromises()
        expect(props.values).toHaveLength(0)
    })
})
