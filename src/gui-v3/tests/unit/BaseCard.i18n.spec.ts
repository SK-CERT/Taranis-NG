import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import BaseCard from '@/components/common/BaseCard.vue'

const createArabicI18n = () =>
    createI18n({
        legacy: false,
        locale: 'ar',
        fallbackLocale: 'ar',
        messages: { ar: { common: { select: 'تحديد' } } }
    })

const mountCard = (props: Record<string, unknown> = {}, rtl = false) =>
    mount(BaseCard, {
        props: { multiSelectActive: true, ...props },
        slots: {
            content: '<span>Card content</span>',
            actions: '<button class="card-action">Action</button>'
        },
        global: {
            plugins: [
                createVuetify({
                    components,
                    directives,
                    locale: { locale: rtl ? 'ar' : 'en', rtl: { ar: true } }
                }),
                createArabicI18n()
            ]
        }
    })

describe('BaseCard locale and direction behavior', () => {
    it('uses the translated default as the checkbox accessible name', () => {
        const wrapper = mountCard()

        expect(wrapper.find('input[type="checkbox"]').attributes('aria-label')).toBe('تحديد')
        expect(wrapper.text()).not.toContain('تحديد')
    })

    it('keeps an explicit checkbox label and selection events unchanged', async () => {
        const wrapper = mountCard({ checkboxLabel: 'Select advisory' })
        const checkbox = wrapper.find('input[type="checkbox"]')

        expect(checkbox.attributes('aria-label')).toBe('Select advisory')
        await checkbox.setValue(true)

        expect(wrapper.emitted('selection-change')).toEqual([[true]])
        expect(wrapper.find('.card-action').exists()).toBe(false)
    })

    it('reverses the leave translation in RTL', () => {
        const wrapper = mountCard({}, true)

        expect(wrapper.classes()).toContain('v-locale--is-rtl')
    })

    it('preserves card click behavior', async () => {
        const wrapper = mountCard({ multiSelectActive: false })

        await wrapper.find('.card-item').trigger('click')

        expect(wrapper.emitted('card-click')).toEqual([[]])
        expect(wrapper.find('.card-action').exists()).toBe(true)
    })
})
