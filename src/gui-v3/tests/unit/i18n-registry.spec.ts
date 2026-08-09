import { describe, expect, it, vi } from 'vitest'
import { createApp, defineComponent, h, nextTick } from 'vue'
import { createVuetify, useLocale } from 'vuetify'
import {
    getLocaleName,
    localeOptions,
    messages,
    pluralRules,
    resolveLocale,
    resolveLocaleDirection,
    supportedLocales,
    synchronizeLocalePresentation,
    vuetifyMessages,
    vuetifyRtlLocales
} from '@/i18n'

describe('i18n catalog registry', () => {
    it('selects all six documented Arabic plural forms', () => {
        const originalRule = vi.fn(() => -1)
        const counts = [0, 1, 2, 3, 5, 10, 11, 12, 21, 99, 100, 102, 103, 1.5]

        expect(counts.map((count) => pluralRules.ar(count, 6, originalRule))).toEqual([0, 1, 2, 3, 3, 3, 4, 4, 4, 4, 5, 5, 3, 5])
        expect(originalRule).not.toHaveBeenCalled()
    })

    it.each([
        ['cs', [0, 1, 2, 3, 3]],
        ['sk', [0, 1, 2, 3, 3]],
        ['pl', [0, 1, 2, 3, 3]],
        ['ru', [0, 1, 2, 3, 1]],
        ['uk', [0, 1, 2, 3, 1]]
    ])('selects the zero, one, few and many forms for %s at 0/1/2/5/21', (locale, expected) => {
        const rule = pluralRules[locale as keyof typeof pluralRules]
        const originalRule = vi.fn(() => -1)

        expect([0, 1, 2, 5, 21].map((count) => rule(count, 4, originalRule))).toEqual(expected)
        expect(originalRule).not.toHaveBeenCalled()
    })

    it.each([
        ['cs', 12, 3],
        ['sk', 14, 3],
        ['pl', 12, 3],
        ['pl', 22, 2],
        ['ru', 11, 3],
        ['ru', 22, 2],
        ['uk', 12, 3],
        ['uk', 22, 2]
    ])('handles the %s teen/compound edge %i', (locale, count, expected) => {
        expect(pluralRules[locale as keyof typeof pluralRules](count, 4, () => -1)).toBe(expected)
    })

    it('delegates non-four-form messages to Vue I18n without changing simple-locale behavior', () => {
        const originalRule = vi.fn(() => 1)

        expect(pluralRules.cs(2, 2, originalRule)).toBe(1)
        expect(originalRule).toHaveBeenCalledWith(2, 2)
        expect(pluralRules).not.toHaveProperty('en')
    })

    it('delegates non-six-form Arabic messages to Vue I18n', () => {
        const originalRule = vi.fn(() => 2)

        expect(pluralRules.ar(2, 3, originalRule)).toBe(2)
        expect(originalRule).toHaveBeenCalledWith(2, 3)
    })

    it('discovers every JSON catalog and exposes matching selector options', () => {
        expect(supportedLocales).toHaveLength(20)
        expect(Object.keys(messages).sort()).toEqual([...supportedLocales].sort())
        expect(localeOptions.map(({ id }) => id).sort()).toEqual([...supportedLocales].sort())
        expect(supportedLocales).toEqual(expect.arrayContaining(['ar', 'en', 'cs', 'sk', 'pt-BR', 'zh-CN']))
    })

    it.each([
        ['pt-BR', 'pt-BR'],
        ['pt_BR', 'pt-BR'],
        ['pt', 'pt-BR'],
        ['pt-PT', 'pt-BR'],
        ['zh-CN', 'zh-CN'],
        ['zh_CN', 'zh-CN'],
        ['zh', 'zh-CN'],
        ['zh-TW', 'zh-CN'],
        ['cs-CZ', 'cs'],
        ['ar', 'ar'],
        ['ar-EG', 'ar'],
        ['ar_SA', 'ar'],
        ['EN-us', 'en'],
        ['xx-YY', 'en'],
        ['', 'en']
    ])('resolves %j to an available catalog', (candidate, expected) => {
        expect(resolveLocale(candidate)).toBe(expected)
    })

    it.each([
        ['ar', 'rtl'],
        ['ar-EG', 'rtl'],
        ['fa_IR', 'rtl'],
        ['he', 'rtl'],
        ['ur-PK', 'rtl'],
        ['en', 'ltr'],
        ['not-a-locale', 'ltr'],
        ['', 'ltr']
    ])('resolves %j writing direction to %s', (candidate, expected) => {
        expect(resolveLocaleDirection(candidate)).toBe(expected)
    })

    it('synchronizes document metadata and Vuetify locale state across runtime changes', () => {
        const vuetifyLocale = { current: { value: 'en' } }

        expect(synchronizeLocalePresentation('ar', vuetifyLocale)).toBe('rtl')
        expect(document.documentElement.lang).toBe('ar')
        expect(document.documentElement.dir).toBe('rtl')
        expect(vuetifyLocale.current.value).toBe('ar')
        expect(vuetifyRtlLocales['ar']).toBe(true)

        expect(synchronizeLocalePresentation('pt-BR', vuetifyLocale)).toBe('ltr')
        expect(document.documentElement.lang).toBe('pt-BR')
        expect(document.documentElement.dir).toBe('ltr')
        expect(vuetifyLocale.current.value).toBe('pt-BR')
        expect(vuetifyRtlLocales['pt-BR']).toBe(false)
    })

    it('updates Vuetify RTL state when the active locale changes', async () => {
        const vuetify = createVuetify({
            locale: {
                locale: 'en',
                fallback: 'en',
                rtl: vuetifyRtlLocales
            }
        })
        let activeVuetifyLocale: ReturnType<typeof useLocale> | undefined
        const app = createApp(
            defineComponent({
                setup() {
                    activeVuetifyLocale = useLocale()
                    return () => h('div')
                }
            })
        )

        app.use(vuetify).mount(document.createElement('div'))
        expect(activeVuetifyLocale?.isRtl.value).toBe(false)

        synchronizeLocalePresentation('ar', activeVuetifyLocale)
        await nextTick()
        expect(activeVuetifyLocale?.isRtl.value).toBe(true)

        synchronizeLocalePresentation('en', activeVuetifyLocale)
        await nextTick()
        expect(activeVuetifyLocale?.isRtl.value).toBe(false)
        app.unmount()
    })

    it('provides localized framework labels for production locale keys', () => {
        expect(vuetifyMessages.ar.close).toBe('إغلاق')
        expect(vuetifyMessages.cs.close).not.toBe(vuetifyMessages.en.close)
        expect(vuetifyMessages['pt-BR']).toBeDefined()
        expect(vuetifyMessages['zh-CN']).toBeDefined()
    })

    it('uses representative native language names when the display locale is supported', () => {
        if (typeof Intl.DisplayNames !== 'function' || Intl.DisplayNames.supportedLocalesOf(['ar', 'de', 'ja']).length !== 3) return

        expect(getLocaleName('ar')).toBe('العربية')
        expect(getLocaleName('de')).toBe('Deutsch')
        expect(getLocaleName('ja')).toBe('日本語')
        expect(localeOptions.find(({ id }) => id === 'ar')?.txt).toBe('العربية')
        expect(localeOptions.find(({ id }) => id === 'de')?.txt).toBe('Deutsch')
        expect(localeOptions.find(({ id }) => id === 'ja')?.txt).toBe('日本語')
    })

    it('falls back to deterministic English when the requested display locale is unsupported', () => {
        if (typeof Intl.DisplayNames !== 'function') return

        const supportedLocales = vi.spyOn(Intl.DisplayNames, 'supportedLocalesOf').mockReturnValueOnce([])
        try {
            expect(getLocaleName('de')).toBe('German')
        } finally {
            supportedLocales.mockRestore()
        }
    })

    it('returns the raw locale code when DisplayNames cannot name it or is unavailable', () => {
        expect(getLocaleName('not-a-locale')).toBe('not-a-locale')

        const originalDisplayNames = Intl.DisplayNames
        Object.defineProperty(Intl, 'DisplayNames', { configurable: true, value: undefined })
        try {
            expect(getLocaleName('de')).toBe('de')
        } finally {
            Object.defineProperty(Intl, 'DisplayNames', { configurable: true, value: originalDisplayNames })
        }
    })
})
