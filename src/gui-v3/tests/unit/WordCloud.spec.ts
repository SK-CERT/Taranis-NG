import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { describe, expect, it, vi } from 'vitest'
import WordCloud from '@/components/dashboard/WordCloud.vue'

vi.mock('d3-cloud', () => ({
    default: () => {
        let words: Array<Record<string, unknown>> = []
        let endLayout: (placedWords: Array<Record<string, unknown>>) => void = () => undefined

        const layout = {
            size: () => layout,
            words: (value: Array<Record<string, unknown>>) => {
                words = value
                return layout
            },
            padding: () => layout,
            rotate: () => layout,
            font: () => layout,
            fontWeight: () => layout,
            fontSize: () => layout,
            spiral: () => layout,
            random: () => layout,
            on: (event: string, callback: (placedWords: Array<Record<string, unknown>>) => void) => {
                if (event === 'end') endLayout = callback
                return layout
            },
            start: () => {
                endLayout(words.map((word, index) => ({ ...word, x: index * 10, y: index * 5 })))
                return layout
            },
            stop: () => layout
        }

        return layout
    }
}))

const data = [
    { word: 'minor', word_quantity: 2 },
    { word: 'مصدر', word_quantity: 12000 },
    { word: 'middle', word_quantity: 8 }
]

const mountWordCloud = (props: Record<string, unknown>) =>
    mount(WordCloud, {
        props,
        global: {
            plugins: [
                createI18n({
                    legacy: false,
                    locale: 'de',
                    messages: {
                        de: {
                            common: { no_data: 'Keine Daten verfügbar' },
                            toolbar_filter: { search: 'Suchen' },
                            word_cloud: {
                                label: 'Wortwolke',
                                word_action_count:
                                    '{action} {word}: keine Ergebnisse | {action} {word}: {count} Ergebnis | {action} {word}: {count} Ergebnisse'
                            }
                        }
                    }
                })
            ],
            stubs: {
                VContainer: { template: '<div><slot /></div>' },
                VAlert: { template: '<div><slot /></div>' }
            }
        }
    })

describe('WordCloud', () => {
    it('renders every valid word in relevance order without a scrolling region', async () => {
        const wrapper = mountWordCloud({ data })

        await vi.waitFor(() => expect(wrapper.findAll('.word-cloud-item')).toHaveLength(3))

        expect(wrapper.findAll('.word-cloud-item').map((item) => item.attributes('aria-label'))).toEqual([
            'Suchen \u2068مصدر\u2069: 12.000 Ergebnisse',
            'Suchen \u2068middle\u2069: 8 Ergebnisse',
            'Suchen \u2068minor\u2069: 2 Ergebnisse'
        ])
        expect(wrapper.find('.word-cloud').attributes('role')).toBe('group')
        expect(wrapper.find('.word-cloud').attributes('aria-label')).toBe('Wortwolke')
        expect(wrapper.findAll('.word-cloud-item').every((item) => item.attributes('dir') === 'auto')).toBe(true)
        expect(wrapper.find('title').text()).toBe('Suchen \u2068مصدر\u2069: 12.000 Ergebnisse')
        expect(wrapper.find('.word-cloud-container').attributes('style')).toBeUndefined()
        wrapper.unmount()
    })

    it('uses stable colors and scales frequent words more prominently', async () => {
        const wrapper = mountWordCloud({
            data,
            colorScheme: ['#123456', '#abcdef'],
            minFontSize: 10,
            maxFontSize: 40
        })

        await vi.waitFor(() => expect(wrapper.findAll('.word-cloud-item')).toHaveLength(3))

        const words = wrapper.findAll('.word-cloud-item')
        const majorWord = words[0]!
        const minorWord = words[2]!

        expect(majorWord.attributes('font-weight')).toBe('700')
        expect(minorWord.attributes('font-weight')).toBe('450')
        expect(Number(majorWord.attributes('font-size'))).toBeGreaterThan(Number(minorWord.attributes('font-size')))
        expect(['#123456', '#abcdef']).toContain(majorWord.attributes('fill'))
        wrapper.unmount()
    })

    it('shows the supplied empty message when there are no valid words', () => {
        const wrapper = mountWordCloud({
            data: [{ word: '', word_quantity: 1 }],
            emptyMessage: 'Nothing collected yet'
        })

        expect(wrapper.text()).toContain('Nothing collected yet')
        expect(wrapper.find('.word-cloud').exists()).toBe(false)
        expect(wrapper.find('.word-cloud-empty').exists()).toBe(true)
        wrapper.unmount()
    })

    it('uses translated defaults and preserves click and keyboard selection payloads', async () => {
        const wrapper = mountWordCloud({ data: [{ word: 'مصدر', word_quantity: 1 }] })
        await vi.waitFor(() => expect(wrapper.find('.word-cloud-item').exists()).toBe(true))

        const word = wrapper.get('.word-cloud-item')
        expect(word.attributes('aria-label')).toBe('Suchen \u2068مصدر\u2069: 1 Ergebnis')
        await word.trigger('click')
        await word.trigger('keydown', { key: 'Enter' })
        await word.trigger('keydown', { key: ' ' })

        expect(wrapper.emitted('select-word')).toEqual([['مصدر'], ['مصدر'], ['مصدر']])
        await wrapper.setProps({ wordActionLabel: 'Nachschlagen' })
        expect(word.attributes('aria-label')).toBe('Nachschlagen \u2068مصدر\u2069: 1 Ergebnis')
        wrapper.unmount()

        const zeroWrapper = mountWordCloud({ data: [{ word: 'leer', word_quantity: 0 }] })
        await vi.waitFor(() => expect(zeroWrapper.find('.word-cloud-item').exists()).toBe(true))
        expect(zeroWrapper.get('.word-cloud-item').attributes('aria-label')).toBe('Suchen \u2068leer\u2069: keine Ergebnisse')
        zeroWrapper.unmount()

        const emptyWrapper = mountWordCloud({ data: [] })
        expect(emptyWrapper.text()).toContain('Keine Daten verfügbar')
        emptyWrapper.unmount()
    })
})
