import { describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import { contentLanguageOf, getLanguageName, languageChain, localizedTitle, useContentLanguages } from '@/composables/useContentLanguages'
import { useSettingsStore } from '@/stores/settings'

// Names in lists follow the GUI's language: its translation, else English, else the item's own
// text. A language that is the item's own gives its own text, so English never replaces it.

const report = {
    title: 'Kritická chyba',
    title_prefix: 'ZRANITELNOST',
    language: 'cs',
    title_translations: {
        en: { title: 'Critical bug', title_prefix: 'VULNERABILITY' },
        sk: { title: 'Kritická chyba v jadre' }
    }
}

describe('content languages', () => {
    it('maps a GUI locale to its content language', () => {
        expect(contentLanguageOf('cs')).toBe('cs')
        expect(contentLanguageOf('pt-BR')).toBe('pt')
        expect(contentLanguageOf('zh-CN')).toBe('zh')
        expect(contentLanguageOf('tlh')).toBeNull()
        expect(contentLanguageOf(undefined)).toBeNull()
    })

    it('looks in the requested language, then English, then the source', () => {
        expect(languageChain('sk', 'cs')).toEqual(['sk', 'en', 'cs'])
        expect(languageChain('en', 'cs')).toEqual(['en', 'cs'])
        expect(languageChain(null, 'cs')).toEqual(['en', 'cs'])
        expect(languageChain('de', null)).toEqual(['de', 'en'])
    })

    it('shows the translation into the GUI language', () => {
        expect(localizedTitle(report, 'en')).toEqual({ title: 'Critical bug', title_prefix: 'VULNERABILITY' })
    })

    it('resolves name and prefix on their own', () => {
        // Slovak has a name but no prefix: the prefix falls back to English.
        expect(localizedTitle(report, 'sk')).toEqual({ title: 'Kritická chyba v jadre', title_prefix: 'VULNERABILITY' })
    })

    it('never replaces the original with English', () => {
        expect(localizedTitle(report, 'cs')).toEqual({ title: 'Kritická chyba', title_prefix: 'ZRANITELNOST' })
    })

    it('falls back to English, then to the original', () => {
        expect(localizedTitle(report, 'de')).toEqual({ title: 'Critical bug', title_prefix: 'VULNERABILITY' })
        expect(localizedTitle({ ...report, title_translations: {} }, 'de')).toEqual({ title: 'Kritická chyba', title_prefix: 'ZRANITELNOST' })
    })

    it('shows the original of a report whose language is not set unless a translation fits', () => {
        const unset = { title: 'Old report', title_prefix: '', language: null, title_translations: {} }
        expect(localizedTitle(unset, 'cs')).toEqual({ title: 'Old report', title_prefix: '' })
    })

    it("names a language the browser does not know by the setting's name, not its code", () => {
        expect(getLanguageName('qaa', 'en', 'Local dialect')).toBe('Local dialect')
        expect(getLanguageName('qaa', 'en')).toBe('qaa')
        expect(getLanguageName('sk', 'en', 'Slovak (configured)')).toBe('Slovak')
    })

    it('tells apart languages named alike by their code', () => {
        const Probe = defineComponent({ setup: () => useContentLanguages(), template: '<div />' })
        const wrapper = mountWithPlugins(Probe)
        // Browsers call both ak and tw "Akan"; two private-use codes named alike stand in for them.
        useSettingsStore().settings = [
            {
                key: 'CONTENT_DEFAULT_LANGUAGE',
                value: 'en',
                options: JSON.stringify([
                    { id: 'qab', txt: 'Local' },
                    { id: 'qaa', txt: 'Local' },
                    { id: 'sk', txt: 'Slovak' }
                ])
            }
        ] as never

        const options = (wrapper.vm as unknown as { languageOptions: { id: string; txt: string }[] }).languageOptions
        expect(options).toEqual([
            { id: 'qaa', txt: 'Local (qaa)' },
            { id: 'qab', txt: 'Local (qab)' },
            { id: 'sk', txt: 'Slovak' }
        ])
    })
})
