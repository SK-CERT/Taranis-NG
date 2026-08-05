import { flushPromises } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import WordListCsvImport from '@/components/config/word-lists/WordListCsvImport.vue'

const VDialogStub = {
    name: 'VDialog',
    props: ['modelValue'],
    template: '<div v-if="modelValue"><slot /></div>'
}

const VFileInputStub = {
    name: 'VFileInput',
    emits: ['update:modelValue'],
    template: '<button class="choose-file" @click="$emit(\'update:modelValue\', file)">file</button>',
    data: () => ({ file: new File(['value;description\nthe;new\nand;conjunction\n'], 'words.csv', { type: 'text/csv' }) })
}

describe('WordListCsvImport', () => {
    it('imports and merges a selected GUI CSV file', async () => {
        const wrapper = mountWithPlugins(WordListCsvImport, {
            props: { modelValue: [{ value: 'the', description: 'old' }] },
            global: { stubs: { VDialog: VDialogStub, VFileInput: VFileInputStub } }
        })

        const openButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import from CSV')
        if (!openButton) throw new Error('CSV import button was not rendered')
        await openButton.trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await flushPromises()

        const importButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import')
        if (!importButton) throw new Error('CSV import confirmation button was not rendered')
        await importButton.trigger('click')

        expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual([
            { value: 'the', description: 'new' },
            { value: 'and', description: 'conjunction' }
        ])
    })
})
