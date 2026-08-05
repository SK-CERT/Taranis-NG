import { describe, expect, it } from 'vitest'
import { localeOptions, messages, resolveLocale, supportedLocales } from '@/i18n'

describe('i18n catalog registry', () => {
    it('discovers every JSON catalog and exposes matching selector options', () => {
        expect(supportedLocales).toHaveLength(19)
        expect(Object.keys(messages).sort()).toEqual([...supportedLocales].sort())
        expect(localeOptions.map(({ id }) => id).sort()).toEqual([...supportedLocales].sort())
        expect(supportedLocales).toEqual(expect.arrayContaining(['en', 'cs', 'sk', 'pt-BR', 'zh-CN']))
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
        ['EN-us', 'en'],
        ['xx-YY', 'en'],
        ['', 'en']
    ])('resolves %j to an available catalog', (candidate, expected) => {
        expect(resolveLocale(candidate)).toBe(expected)
    })
})
