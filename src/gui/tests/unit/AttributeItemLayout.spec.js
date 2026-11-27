import { describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeItemLayout from '@/components/common/attribute/AttributeItemLayout.vue'

function mountLayout(props) {
    setActivePinia(createPinia())
    return mountWithPlugins(AttributeItemLayout, {
        props,
        slots: { content: '<div class="value">a value</div>' }
    })
}

describe('AttributeItemLayout', () => {
    it('shows the values without sort chips or an add button when there is nothing to sort or add', () => {
        const wrapper = mountLayout({ values: [{ id: 1 }] })

        expect(wrapper.find('.value').exists()).toBe(true)
        expect(wrapper.find('.attribute-item-layout__sort').exists()).toBe(false)
        expect(wrapper.find('.attribute-item-layout__add').exists()).toBe(false)
    })

    it('offers sorting once there are several values', () => {
        const wrapper = mountLayout({ values: [{ id: 1 }, { id: 2 }] })

        expect(wrapper.findAll('.attribute-item-layout__sort .v-chip')).toHaveLength(2)
    })

    it('adds a value from a labelled button', async () => {
        const wrapper = mountLayout({ values: [{ id: 1 }], addButton: true })

        const button = wrapper.get('.attribute-item-layout__add button')
        expect(button.text()).toBe('Add value')
        expect(button.attributes('title')).toBe('Add new value to this attribute')
        await button.trigger('click')

        expect(wrapper.emitted('add-value')).toHaveLength(1)
    })
})
