import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { mountWithPlugins } from '../helpers/mount-helpers'

import AttributeString from '@/components/common/attribute/AttributeString.vue'
import AttributeNumber from '@/components/common/attribute/AttributeNumber.vue'
import AttributeText from '@/components/common/attribute/AttributeText.vue'
import AttributeEnum from '@/components/common/attribute/AttributeEnum.vue'
import AttributeRadio from '@/components/common/attribute/AttributeRadio.vue'
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

// ── API mocks (prevent network calls from useAttributes) ─────────────────────
vi.mock('@/api/analyze', () => ({
  getReportItemData: vi.fn().mockResolvedValue({ data: {} }),
  holdLockReportItem: vi.fn().mockResolvedValue({}),
  lockReportItem: vi.fn().mockResolvedValue({}),
  unlockReportItem: vi.fn().mockResolvedValue({}),
  updateReportItem: vi.fn().mockResolvedValue({}),
  downloadAttachment: vi.fn().mockResolvedValue({})
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
  props: ['modelValue', 'readonly'],
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

const globalStubs = {
  AttributeItemLayout: AttributeItemLayoutStub,
  AttributeValueLayout: AttributeValueLayoutStub,
  Editor: EditorStub,
  CalculatorCVSS: CalculatorCVSSStub
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
    expect(wrapper.find('.text-value').exists()).toBe(true)
  })

  it('shows VTextarea in edit mode', () => {
    const wrapper = mountAttr(AttributeText, baseProps())
    expect(wrapper.findComponent({ name: 'VTextarea' }).exists()).toBe(true)
  })
})

// ── AttributeEnum ─────────────────────────────────────────────────────────────

describe('AttributeEnum', () => {
  beforeEach(() => setActivePinia(createPinia()))

  const enumGroup = makeAttributeGroup({
    attribute: {
      type: 'ENUM',
      enum_items: [{ id: 1, value: 'option-a' }, { id: 2, value: 'option-b' }]
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
})

// ── AttributeRadio ────────────────────────────────────────────────────────────

describe('AttributeRadio', () => {
  beforeEach(() => setActivePinia(createPinia()))

  const radioGroup = makeAttributeGroup({
    attribute: {
      type: 'RADIO',
      enum_items: [{ id: 1, value: 'yes' }, { id: 2, value: 'no' }]
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
})

// ── AttributeDate ─────────────────────────────────────────────────────────────

describe('AttributeDate', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders without error', () => {
    expect(mountAttr(AttributeDate, baseProps({ value: '2024-01-15' })).exists()).toBe(true)
  })

  it('shows read-only date value', () => {
    const wrapper = mountAttr(AttributeDate, readOnlyProps({ value: '2024-01-15' }))
    // Value is formatted via toLocaleDateString() — locale-specific, just check element exists
    expect(wrapper.find('.date-value').exists()).toBe(true)
    expect(wrapper.text().trim()).not.toBe('')
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

  it('shows read-only datetime value', () => {
    const wrapper = mountAttr(AttributeDateTime, readOnlyProps({ value: '2024-01-15T14:30' }))
    // Value is formatted via toLocaleDateString/TimeString — locale-specific, just check element
    expect(wrapper.find('.datetime-value').exists()).toBe(true)
    expect(wrapper.text().trim()).not.toBe('')
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
  })

  it('shows VTextField and calculator in edit mode', () => {
    const wrapper = mountAttr(AttributeCVSS, baseProps({ value: cvssVector }))
    expect(wrapper.findComponent({ name: 'VTextField' }).exists()).toBe(true)
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
    expect(wrapper.findComponent({ name: 'Editor' }).exists()).toBe(true)
  })
})

// ── AttributeAttachment ───────────────────────────────────────────────────────

describe('AttributeAttachment', () => {
  beforeEach(() => setActivePinia(createPinia()))

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
    expect(wrapper.find('.attachment-display').exists()).toBe(true)
  })

  it('shows editable layout in edit mode', () => {
    const wrapper = mountAttr(AttributeAttachment, baseProps(attachmentValue))
    // Attachment edit mode shows a value-layout stub with file info / download button
    expect(wrapper.find('.value-layout-stub').exists()).toBe(true)
  })
})
