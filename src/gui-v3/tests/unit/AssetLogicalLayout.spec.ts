import { nextTick } from 'vue'
import { createI18n } from 'vue-i18n'
import { describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AssetDialog from '@/components/assets/AssetDialog.vue'
import CpeEditor from '@/components/assets/CpeEditor.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/composables/useSpellcheck', () => ({
    useSpellcheck: () => true
}))

vi.mock('@/api/assets', () => ({
    createNewAsset: vi.fn(),
    solveVulnerability: vi.fn(),
    updateAsset: vi.fn(),
    getCPEAttributeEnums: vi.fn().mockResolvedValue({ data: { items: [] } })
}))

const passthroughStub = (name: string) => ({ name, template: '<div><slot /></div>' })
const dataTableStub = {
    name: 'VDataTable',
    props: ['items'],
    template: `
        <div class="data-table-stub">
            <div v-for="(item, index) in items" :key="index">
                <slot name="item.value" :item="item" :value="item.value" :index="index" />
                <slot name="item.description" :item="item" :value="item.description" :index="index" />
                <slot name="item.actions" :item="item" :index="index" />
            </div>
            <slot />
        </div>
    `
}
const badgeStub = {
    name: 'VBadge',
    props: ['content'],
    template: '<div data-test="unsolved-count" :data-content="content"><slot /></div>'
}

const layoutStubs = {
    VDialog: passthroughStub('VDialog'),
    VCard: passthroughStub('VCard'),
    VCardText: passthroughStub('VCardText'),
    VTabs: passthroughStub('VTabs'),
    VTab: passthroughStub('VTab'),
    VBadge: badgeStub,
    VWindow: passthroughStub('VWindow'),
    VWindowItem: passthroughStub('VWindowItem'),
    VForm: passthroughStub('VForm'),
    VExpansionPanels: passthroughStub('VExpansionPanels'),
    VExpansionPanel: passthroughStub('VExpansionPanel'),
    VExpansionPanelTitle: passthroughStub('VExpansionPanelTitle'),
    VExpansionPanelText: passthroughStub('VExpansionPanelText'),
    VCardTitle: passthroughStub('VCardTitle'),
    VToolbar: passthroughStub('VToolbar'),
    VToolbarTitle: passthroughStub('VToolbarTitle'),
    VDataTable: dataTableStub,
    VIcon: passthroughStub('VIcon'),
    VSpacer: true,
    VSwitch: true,
    VAlert: passthroughStub('VAlert'),
    VTextField: true,
    VTextarea: true,
    VCombobox: true,
    VFileInput: true,
    VCheckbox: true,
    DialogToolbar: true,
    VulnerabilityDetail: true
}

describe('asset dialog logical layout', () => {
    it('locale-formats the unsolved count and declares input direction without changing values', () => {
        const arabicI18n = createI18n({
            legacy: false,
            locale: 'ar-EG',
            fallbackLocale: 'en',
            messages: { 'ar-EG': {} }
        })
        const asset = {
            id: 1,
            name: 'خادم',
            serial: 'SRV-123',
            description: 'خادم الإنتاج',
            asset_cpes: [],
            vulnerabilities: [{ solved: false, report_item: { id: 9, title: 'ثغرة' } }]
        }
        const wrapper = mountWithPlugins(AssetDialog, {
            props: { modelValue: true, groupId: 'group-1', asset },
            global: {
                plugins: [arabicI18n],
                stubs: { ...layoutStubs, VTextField: false, VTextarea: false, CpeEditor: true }
            }
        })

        expect(wrapper.get('[data-test="unsolved-count"]').attributes('data-content')).toBe('١')
        const textFields = wrapper.findAll('input')
        expect(textFields[0]!.attributes('dir')).toBe('auto')
        expect(textFields[0]!.element.value).toBe(asset.name)
        expect(textFields[1]!.attributes('dir')).toBe('ltr')
        expect(textFields[1]!.element.value).toBe(asset.serial)
        expect(wrapper.get('textarea').attributes('dir')).toBe('auto')
        expect(wrapper.get('textarea').element.value).toBe(asset.description)
    })

    it('uses logical spacing and isolates a dynamic vulnerability title', () => {
        const wrapper = mountWithPlugins(AssetDialog, {
            props: {
                modelValue: true,
                groupId: 'group-1',
                asset: {
                    id: 1,
                    name: 'Asset',
                    serial: 'serial',
                    description: 'description',
                    asset_cpes: [],
                    vulnerabilities: [
                        {
                            solved: false,
                            report_item: { id: 9, title: 'عنوان الثغرة' }
                        }
                    ]
                }
            },
            global: { stubs: { ...layoutStubs, CpeEditor: true } }
        })

        expect(wrapper.find('.ms-3').exists()).toBe(true)
        expect(wrapper.find('.pe-4').exists()).toBe(true)
        expect(wrapper.find('.me-3').exists()).toBe(true)
        expect(wrapper.find('.ml-3, .pr-4, .mr-3').exists()).toBe(false)
        expect(wrapper.get('bdi[dir="auto"]').text()).toBe('عنوان الثغرة')
    })

    it('keeps the CPE import action condition while using inline-end spacing', async () => {
        const wrapper = mountWithPlugins(CpeEditor, {
            props: { modelValue: [], disabled: false },
            global: { stubs: layoutStubs }
        })

        expect(wrapper.find('.me-2').exists()).toBe(true)
        expect(wrapper.find('.mr-2').exists()).toBe(false)

        await wrapper.setProps({ disabled: true })
        expect(wrapper.find('.me-2').exists()).toBe(false)
    })

    it('keeps CPE values LTR and descriptions auto-directed in inputs and both tables', async () => {
        const row = { value: 'cpe:2.3:a:vendor:product:*:*:*:*:*:*:*:*', description: 'خادم الإنتاج' }
        const wrapper = mountWithPlugins(CpeEditor, {
            props: { modelValue: [row], disabled: false },
            global: { stubs: { ...layoutStubs, VCombobox: false, VTextField: false } }
        })

        const inputs = wrapper.findAll('input')
        expect(inputs[0]!.attributes('dir')).toBe('ltr')
        expect(inputs[1]!.attributes('dir')).toBe('auto')
        expect(wrapper.get('bdi[dir="ltr"]').text()).toBe(row.value)
        expect(wrapper.get('bdi[dir="auto"]').text()).toBe(row.description)
        expect(wrapper.props('modelValue')).toEqual([row])

        ;(wrapper.vm as unknown as { csvRows: (typeof row)[] }).csvRows = [row]
        await nextTick()

        expect(wrapper.findAll('.data-table-stub')).toHaveLength(2)
        expect(wrapper.findAll('bdi[dir="ltr"]').map((node) => node.text())).toEqual([row.value, row.value])
        expect(wrapper.findAll('bdi[dir="auto"]').map((node) => node.text())).toEqual([row.description, row.description])
    })
})
