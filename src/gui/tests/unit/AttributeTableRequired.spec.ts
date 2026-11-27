import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeTable from '@/components/config/reports/AttributeTable.vue'

// A field is required when it needs at least one value: the Required tick sets the minimum
// occurrence, which the report form then shows to authors.

const EditableEntityTableStub = {
    name: 'EditableEntityTable',
    props: ['modelValue'],
    template: '<div><slot name="item.required" :item="modelValue[0]" /><slot name="form" :item="modelValue[0]" /></div>'
}

const mountTable = (minOccurrence: number, maxOccurrence: number) => {
    const item = reactive({
        id: 9,
        index: 0,
        attribute_id: 1,
        attribute_name: 'Text',
        title: 'Field',
        description: '',
        min_occurrence: minOccurrence,
        max_occurrence: maxOccurrence,
        ai_provider_id: null,
        ai_prompt: '',
        translate: false,
        translations: {}
    })
    const wrapper = mountWithPlugins(AttributeTable, {
        props: { modelValue: [item], attributeTemplates: [{ id: 1, name: 'Text', type: 'STRING' }] },
        global: { stubs: { EditableEntityTable: EditableEntityTableStub } }
    })
    return { wrapper, item }
}

const requiredBox = (wrapper: ReturnType<typeof mountTable>['wrapper']) =>
    wrapper.findAllComponents({ name: 'VCheckbox' }).find((box) => box.attributes('data-test') === 'attribute-required')!

describe('AttributeTable Required', () => {
    it('is ticked for a field that needs a value, and marked in the table', () => {
        const { wrapper } = mountTable(1, 1)

        expect(requiredBox(wrapper).props('modelValue')).toBe(true)
        expect(wrapper.find('[data-test="attribute-required-mark"]').exists()).toBe(true)
    })

    it('makes an optional field need one value, with room for it', async () => {
        const { wrapper, item } = mountTable(0, 0)

        requiredBox(wrapper).vm.$emit('update:modelValue', true)
        await wrapper.vm.$nextTick()

        expect(item.min_occurrence).toBe(1)
        expect(item.max_occurrence).toBe(1)
    })

    it('keeps a larger minimum, and untick makes the field optional', async () => {
        const { wrapper, item } = mountTable(2, 5)

        requiredBox(wrapper).vm.$emit('update:modelValue', true)
        expect(item.min_occurrence).toBe(2)

        requiredBox(wrapper).vm.$emit('update:modelValue', false)
        await wrapper.vm.$nextTick()

        expect(item.min_occurrence).toBe(0)
        expect(item.max_occurrence).toBe(5)
        expect(wrapper.find('[data-test="attribute-required-mark"]').exists()).toBe(false)
    })
})
