import { flushPromises } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
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
    afterEach(() => {
        vi.unstubAllGlobals()
    })

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

    it('downloads a configured URL through the CSV preview and merge flow without credentials', async () => {
        const fetchMock = vi.fn().mockResolvedValue({
            ok: true,
            text: () => Promise.resolve('description,value\nnew,the\nconjunction,and\n')
        })
        vi.stubGlobal('fetch', fetchMock)

        const wrapper = mountWithPlugins(WordListCsvImport, {
            props: {
                modelValue: [{ value: 'the', description: 'old' }],
                sourceUrl: ' https://lists.example.test/words.csv '
            },
            global: { stubs: { VDialog: VDialogStub } }
        })

        const downloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Download from URL')
        if (!downloadButton) throw new Error('URL download button was not rendered')
        await downloadButton.trigger('click')
        await flushPromises()

        expect(fetchMock).toHaveBeenCalledWith(new globalThis.URL('https://lists.example.test/words.csv'), {
            credentials: 'omit',
            referrerPolicy: 'no-referrer',
            cache: 'no-store'
        })
        expect(wrapper.text()).toContain('the')
        expect(wrapper.text()).toContain('and')

        const importButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import')
        if (!importButton) throw new Error('CSV import confirmation button was not rendered')
        await importButton.trigger('click')

        expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual([
            { value: 'the', description: 'new' },
            { value: 'and', description: 'conjunction' }
        ])
    })

    it('reports URL failures without replacing existing category entries', async () => {
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
        const original = [{ value: 'keep', description: 'existing' }]
        const wrapper = mountWithPlugins(WordListCsvImport, {
            props: { modelValue: original, sourceUrl: 'https://lists.example.test/down.csv' },
            global: { stubs: { VDialog: VDialogStub } }
        })

        const downloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Download from URL')
        if (!downloadButton) throw new Error('URL download button was not rendered')
        await downloadButton.trigger('click')
        await flushPromises()

        expect(wrapper.text()).toContain('Could not download the word list from the URL.')
        expect(wrapper.emitted('update:modelValue')).toBeUndefined()
        expect(original).toEqual([{ value: 'keep', description: 'existing' }])
    })

    it('replaces existing category entries only after explicit confirmation', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                text: () => Promise.resolve('value,description\nreplacement,new list\n')
            })
        )
        const wrapper = mountWithPlugins(WordListCsvImport, {
            props: {
                modelValue: [{ value: 'keep', description: 'existing' }],
                sourceUrl: 'https://lists.example.test/replacement.csv'
            },
            global: { stubs: { VDialog: VDialogStub } }
        })

        const downloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Download from URL')
        if (!downloadButton) throw new Error('URL download button was not rendered')
        await downloadButton.trigger('click')
        await flushPromises()

        const replaceCheckbox = wrapper.findAllComponents({ name: 'VCheckbox' })[1]
        if (!replaceCheckbox) throw new Error('Replace-existing checkbox was not rendered')
        await replaceCheckbox.setValue(true)
        const importButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import')
        if (!importButton) throw new Error('CSV import confirmation button was not rendered')
        await importButton.trigger('click')

        expect(wrapper.emitted('update:modelValue')?.at(-1)?.[0]).toEqual([{ value: 'replacement', description: 'new list' }])
    })

    it('does not expose URL download for blank or unsupported links', async () => {
        const wrapper = mountWithPlugins(WordListCsvImport, {
            props: { sourceUrl: '' },
            global: { stubs: { VDialog: VDialogStub } }
        })
        expect(wrapper.text()).not.toContain('Download from URL')

        await wrapper.setProps({ sourceUrl: 'file:///etc/passwd' })
        const downloadButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Download from URL')
        if (!downloadButton) throw new Error('Configured URL action was not rendered')
        await downloadButton.trigger('click')
        await flushPromises()

        expect(wrapper.text()).toContain('Could not download the word list from the URL.')
        expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    })

    it('uses a complete CSV-import error message for local file failures', async () => {
        const failingFileInput = {
            name: 'VFileInput',
            emits: ['update:modelValue'],
            template: '<button class="choose-file" @click="$emit(\'update:modelValue\', file)">file</button>',
            data: () => ({ file: { text: () => Promise.reject(new Error('read failed')) } })
        }
        const wrapper = mountWithPlugins(WordListCsvImport, {
            global: { stubs: { VDialog: VDialogStub, VFileInput: failingFileInput } }
        })

        const openButton = wrapper.findAllComponents({ name: 'VBtn' }).find((button) => button.text() === 'Import from CSV')
        if (!openButton) throw new Error('CSV import button was not rendered')
        await openButton.trigger('click')
        await wrapper.find('.choose-file').trigger('click')
        await flushPromises()

        expect(wrapper.text()).toContain('Could not import the word-list file.')
        expect(wrapper.text()).not.toContain('Could not download the word list from the URL.')
    })
})
