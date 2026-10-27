import { describe, expect, it } from 'vitest'
import { reactive } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeTable from '@/components/config/reports/AttributeTable.vue'

// Only text fields (string, text, rich text) can be translated per report, so the Translate tick
// is offered only for them and is dropped when the field changes to another type.

const EditableEntityTableStub = {
    name: 'EditableEntityTable',
    props: ['modelValue'],
    template: '<div><slot name="form" :item="modelValue[0]" /></div>'
}

const templates = [
    { id: 1, name: 'Description', type: 'TEXT' },
    { id: 2, name: 'CVE', type: 'CVE' }
]

const mountTable = (attributeId: number, translate = false) => {
    const item = reactive({
        id: 9,
        index: 0,
        attribute_id: attributeId,
        attribute_name: '',
        title: 'Field',
        description: '',
        min_occurrence: 0,
        max_occurrence: 1,
        ai_provider_id: null,
        ai_prompt: '',
        translate,
        translations: {}
    })
    const wrapper = mountWithPlugins(AttributeTable, {
        props: { modelValue: [item], attributeTemplates: templates },
        global: { stubs: { EditableEntityTable: EditableEntityTableStub } }
    })
    return { wrapper, item }
}

describe('AttributeTable Translate', () => {
    it('is offered for a text field', () => {
        const { wrapper } = mountTable(1)

        expect(wrapper.find('[data-test="attribute-translate"]').exists()).toBe(true)
    })

    it('is not offered for other types', () => {
        const { wrapper } = mountTable(2)

        expect(wrapper.find('[data-test="attribute-translate"]').exists()).toBe(false)
    })

    it('is dropped when the field changes to a type that is not translated', async () => {
        const { wrapper, item } = mountTable(1, true)

        wrapper.findComponent({ name: 'VSelect' }).vm.$emit('update:modelValue', 2)
        await wrapper.vm.$nextTick()

        expect(item.attribute_id).toBe(2)
        expect(item.translate).toBe(false)
        expect(wrapper.find('[data-test="attribute-translate"]').exists()).toBe(false)
    })
})
