import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewOrganization from '@/components/config/access-management/NewOrganization.vue'

vi.mock('@/api/config', () => ({
    createNewOrganization: vi.fn(),
    updateOrganization: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/composables/useSpellcheck', () => ({
    useSpellcheck: () => false
}))

describe('NewOrganization required-field affordance', () => {
    it('marks the mandatory name before validation, visually and for assistive technology', async () => {
        const wrapper = mountWithPlugins(NewOrganization, {
            attachTo: document.body,
            props: {
                editItem: {
                    id: 1,
                    name: 'CERT',
                    description: '',
                    require_mfa: false,
                    address: { street: '', city: '', zip: '', country: '' }
                }
            }
        })
        await new Promise((resolve) => setTimeout(resolve, 0))
        await wrapper.vm.$nextTick()

        const nameField = document.body.querySelector('[data-test="organization-name"]')
        const input = nameField?.querySelector('input')
        const form = document.body.querySelector('form[aria-describedby="organization-required-fields-hint"]')

        expect(document.body.textContent).toContain('Fields marked with * are required.')
        expect(nameField?.textContent).toContain('Name')
        expect(nameField?.querySelector('.text-error[aria-hidden="true"]')?.textContent).toBe('*')
        expect(input?.hasAttribute('required')).toBe(true)
        expect(input?.getAttribute('aria-required')).toBe('true')
        expect(form).not.toBeNull()

        wrapper.unmount()
    })
})
