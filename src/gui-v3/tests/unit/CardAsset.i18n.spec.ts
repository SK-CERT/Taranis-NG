import { describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CardAsset from '@/components/assets/CardAsset.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const ConfirmationDialogStub = {
    name: 'ConfirmationDialog',
    props: ['message'],
    template: '<div data-test="confirmation"><slot /></div>'
}

const createCardMessages = () =>
    createI18n({
        legacy: false,
        locale: 'de',
        messages: {
            de: {
                asset: {
                    serial_with_value: 'Serial: {value}',
                    cpe_count: 'No CPE codes | {count} CPE code | {count} CPE codes',
                    vulnerabilities_count: 'No vulnerabilities | {count} vulnerability | {count} vulnerabilities'
                }
            }
        }
    })

const makeAsset = (overrides: Record<string, unknown> = {}) => ({
    id: 1,
    name: 'Server',
    serial: '',
    description: '',
    asset_group_id: 'group-1',
    asset_cpes: [],
    vulnerabilities_count: 0,
    ...overrides
})

const mountCard = (overrides: Record<string, unknown> = {}) =>
    mountWithPlugins(CardAsset, {
        props: { asset: makeAsset(overrides) },
        global: {
            plugins: [createCardMessages()],
            stubs: {
                ActionButton: true,
                ConfirmationDialog: ConfirmationDialogStub
            }
        }
    })

describe('CardAsset locale-safe messages', () => {
    it.each([
        [0, 'No vulnerabilities'],
        [1, '1 vulnerability'],
        [2, '2 vulnerabilities'],
        [12000, '12.000 vulnerabilities']
    ])('renders vulnerability count %i as a complete plural message', (count, expected) => {
        const wrapper = mountCard({ vulnerabilities_count: count })

        expect(wrapper.findComponent({ name: 'VChip' }).text()).toContain(expected)
        expect(wrapper.findComponent({ name: 'VChip' }).attributes('aria-label')).toBeUndefined()
    })

    it('provides a complete plural accessible label for the CPE count', () => {
        const wrapper = mountCard({ asset_cpes: Array.from({ length: 12000 }, () => ({ value: 'cpe' })) })
        const count = wrapper.get('.asset-card__cpes')

        expect(count.text()).toContain('12.000')
        expect(count.attributes('title')).toBe('12.000 CPE codes')
        expect(count.attributes('aria-label')).toBeUndefined()
        expect(count.get('.d-sr-only').text()).toBe('12.000 CPE codes')
        expect(count.get('strong').attributes('aria-hidden')).toBe('true')
    })

    it('renders the serial label/value as one message and isolates machine and human values', () => {
        const wrapper = mountCard({
            name: 'خادم الويب',
            serial: 'SRV-123',
            description: 'خادم الإنتاج'
        })

        expect(wrapper.text()).toContain('Serial: SRV-123')
        expect(wrapper.get('bdi[dir="ltr"]').text()).toBe('SRV-123')
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual(expect.arrayContaining(['خادم الويب', 'خادم الإنتاج']))
        expect(wrapper.get('[data-test="confirmation"] bdi[dir="auto"]').text()).toBe('خادم الويب')
    })
})
