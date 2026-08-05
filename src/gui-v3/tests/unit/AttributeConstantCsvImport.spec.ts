import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AttributeConstantCsvImport from '@/components/config/reports/AttributeConstantCsvImport.vue'
import { mapAttributeConstantRows, mergeAttributeConstants, readAttributeConstantCsv } from '@/utils/attribute-constant-csv'

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div v-if="modelValue"><slot /></div>'
}

const VFileInputStub = {
    name: 'VFileInput',
    emits: ['update:modelValue'],
    template: '<button class="choose-file" @click="$emit(\'update:modelValue\', file)">file</button>',
    data: () => ({
        file: new File(
            ['summary;identifier;ignored\nRemote code execution;CVE-2026-1;x\nDuplicate;CVE-2026-1;y\nWeakness;CWE-79;z\n'],
            'constants.csv',
            {
                type: 'text/csv'
            }
        )
    })
}

const VSelectStub = defineComponent({
    name: 'VSelect',
    props: {
        modelValue: { type: Number, default: null },
        items: { type: Array, default: () => [] },
        label: { type: String, default: '' }
    },
    emits: ['update:modelValue'],
    template: '<div class="column-select" />'
})

describe('attribute constant CSV utilities', () => {
    it('reads headers, maps selected columns, removes empty values, and deduplicates case-insensitively', () => {
        const csv = readAttributeConstantCsv('description;value\nFirst;Alpha\nSecond;alpha\nEmpty;\n', true)

        expect(csv.headers).toEqual(['description', 'value'])
        expect(mapAttributeConstantRows(csv.records, 1, 0)).toEqual([{ value: 'alpha', description: 'Second' }])
    })

    it('supports merge and replace behavior', () => {
        const existing = [{ value: 'Alpha', description: 'old' }]
        const incoming = [
            { value: 'alpha', description: 'new' },
            { value: 'Beta', description: 'second' }
        ]

        expect(mergeAttributeConstants(existing, incoming, false)).toEqual([
            { value: 'alpha', description: 'new' },
            { value: 'Beta', description: 'second' }
        ])
        expect(mergeAttributeConstants(existing, incoming, true)).toEqual(incoming)
    })

    it('rejects malformed quoted CSV with a clear parser error', () => {
        expect(() => readAttributeConstantCsv('value;description\n"unfinished', true)).toThrow('Unterminated quoted CSV field')
    })
})

describe('AttributeConstantCsvImport', () => {
    it('previews manually mapped headers and emits the selected replace mode', async () => {
        const wrapper = mountWithPlugins(AttributeConstantCsvImport, {
            global: { stubs: { VDialog: VDialogStub, VFileInput: VFileInputStub, VSelect: VSelectStub } }
        })

        const openButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import from CSV')
        if (!openButton) throw new Error('CSV import button was not rendered')
        await openButton.trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await flushPromises()

        const selects = wrapper
            .findAllComponents(VSelectStub)
            .filter((select) => ['Value', 'Description'].includes(select.props('label') ?? ''))
        expect(selects).toHaveLength(2)
        expect(selects[0]!.props('items')).toEqual([
            { title: 'summary', value: 0 },
            { title: 'identifier', value: 1 },
            { title: 'ignored', value: 2 }
        ])
        selects[0]!.vm.$emit('update:modelValue', 1)
        selects[1]!.vm.$emit('update:modelValue', 0)
        await flushPromises()

        const checkbox = wrapper.findAllComponents({ name: 'VCheckbox' }).at(1)
        if (!checkbox) throw new Error('Replace checkbox was not rendered')
        checkbox.vm.$emit('update:modelValue', true)

        const importButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import')
        if (!importButton) throw new Error('CSV import confirmation button was not rendered')
        await importButton.trigger('click')

        expect(wrapper.emitted('import')?.[0]?.[0]).toEqual({
            items: [
                { value: 'CVE-2026-1', description: 'Duplicate' },
                { value: 'CWE-79', description: 'Weakness' }
            ],
            replaceExisting: true
        })
    })

    it('disables import and shows progress while the parent operation is busy', async () => {
        const wrapper = mountWithPlugins(AttributeConstantCsvImport, {
            props: { modelValue: true, busy: true },
            global: { stubs: { VDialog: VDialogStub, VFileInput: VFileInputStub, VSelect: VSelectStub } }
        })

        expect(wrapper.findComponent({ name: 'VProgressLinear' }).exists()).toBe(true)
        const importButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import')
        expect(importButton?.attributes('disabled')).toBeDefined()
    })
})
