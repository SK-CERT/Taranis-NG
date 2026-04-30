import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeContainer from '@/components/common/attribute/AttributeContainer.vue'

// Map type → actual component name (matching file names)
const typeToComponentName = {
  STRING: 'AttributeString',
  NUMBER: 'AttributeNumber',
  BOOLEAN: 'AttributeBoolean',
  ENUM: 'AttributeEnum',
  RADIO: 'AttributeRadio',
  TEXT: 'AttributeText',
  DATE: 'AttributeDate',
  TIME: 'AttributeTime',
  DATE_TIME: 'AttributeDateTime',
  RICH_TEXT: 'AttributeRichText',
  TLP: 'AttributeTLP',
  ATTACHMENT: 'AttributeAttachment',
  CPE: 'AttributeCPE',
  CVE: 'AttributeCVE',
  CWE: 'AttributeCWE',
  CVSS: 'AttributeCVSS'
}

const attributeTypes = Object.keys(typeToComponentName)

const stubs = {}
attributeTypes.forEach((type) => {
  const name = typeToComponentName[type]
  stubs[name] = {
    template: `<div class="stub-${type}" />`,
    props: ['attributeGroup', 'values', 'readOnly', 'edit', 'modify', 'reportItemId']
  }
})

function makeItem(type, values = []) {
  return {
    attribute_group_item: {
      attribute: { type }
    },
    values
  }
}

const baseProps = {
  readOnly: false,
  edit: true,
  modify: false,
  reportItemId: 42
}

describe('AttributeContainer', () => {
  // ── Dynamic Rendering ─────────────────────────
  describe('dynamic rendering', () => {
    it.each(attributeTypes)(
      'should render the correct component for type %s',
      (type) => {
        const wrapper = mountWithPlugins(AttributeContainer, {
          props: { ...baseProps, attributeItem: makeItem(type) },
          global: { stubs }
        })

        expect(wrapper.find(`.stub-${type}`).exists()).toBe(true)
      }
    )

    it('should render nothing for unknown attribute type', () => {
      const wrapper = mountWithPlugins(AttributeContainer, {
        props: { ...baseProps, attributeItem: makeItem('UNKNOWN') },
        global: { stubs }
      })

      // v-if="attributeComponent" should produce nothing
      expect(wrapper.html()).toContain('<!--')
    })
  })

  // ── Prop Passing ──────────────────────────────
  describe('prop passing', () => {
    it('should pass attributeGroup to child component', () => {
      const item = makeItem('STRING')
      const wrapper = mountWithPlugins(AttributeContainer, {
        props: { ...baseProps, attributeItem: item },
        global: { stubs }
      })

      const child = wrapper.findComponent(stubs['AttributeString'])
      expect(child.props('attributeGroup')).toEqual(item.attribute_group_item)
    })

    it('should pass values to child component', () => {
      const values = [{ value: 'test-val' }]
      const item = makeItem('NUMBER', values)
      const wrapper = mountWithPlugins(AttributeContainer, {
        props: { ...baseProps, attributeItem: item },
        global: { stubs }
      })

      const child = wrapper.findComponent(stubs['AttributeNumber'])
      expect(child.props('values')).toEqual(values)
    })

    it('should default values to empty array when not provided', () => {
      const item = { attribute_group_item: { attribute: { type: 'BOOLEAN' } } }
      const wrapper = mountWithPlugins(AttributeContainer, {
        props: { ...baseProps, attributeItem: item },
        global: { stubs }
      })

      const child = wrapper.findComponent(stubs['AttributeBoolean'])
      expect(child.props('values')).toEqual([])
    })

    it('should pass readOnly, edit, modify, and reportItemId', () => {
      const wrapper = mountWithPlugins(AttributeContainer, {
        props: {
          attributeItem: makeItem('CVSS'),
          readOnly: true,
          edit: false,
          modify: true,
          reportItemId: 99
        },
        global: { stubs }
      })

      const child = wrapper.findComponent(stubs['AttributeCVSS'])
      expect(child.props('readOnly')).toBe(true)
      expect(child.props('edit')).toBe(false)
      expect(child.props('modify')).toBe(true)
      expect(child.props('reportItemId')).toBe(99)
    })
  })
})
