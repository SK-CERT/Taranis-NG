import { mount } from '@vue/test-utils'
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
    { word: 'major', word_quantity: 20 },
    { word: 'middle', word_quantity: 8 }
]

describe('WordCloud', () => {
    it('renders every valid word in relevance order without a scrolling region', async () => {
        const wrapper = mount(WordCloud, {
            props: { data },
            global: {
                stubs: {
                    VContainer: { template: '<div><slot /></div>' },
                    VAlert: { template: '<div><slot /></div>' }
                }
            }
        })

        await vi.waitFor(() => expect(wrapper.findAll('.word-cloud-item')).toHaveLength(3))

        expect(wrapper.findAll('.word-cloud-item').map((item) => item.attributes('aria-label'))).toEqual([
            'Search: major (20)',
            'Search: middle (8)',
            'Search: minor (2)'
        ])
        expect(wrapper.find('.word-cloud').attributes('role')).toBe('group')
        expect(wrapper.find('.word-cloud-container').attributes('style')).toBeUndefined()
        wrapper.unmount()
    })

    it('uses stable colors and scales frequent words more prominently', async () => {
        const wrapper = mount(WordCloud, {
            props: {
                data,
                colorScheme: ['#123456', '#abcdef'],
                minFontSize: 10,
                maxFontSize: 40
            },
            global: {
                stubs: {
                    VContainer: { template: '<div><slot /></div>' },
                    VAlert: { template: '<div><slot /></div>' }
                }
            }
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
        const wrapper = mount(WordCloud, {
            props: {
                data: [{ word: '', word_quantity: 1 }],
                emptyMessage: 'Nothing collected yet'
            },
            global: {
                stubs: {
                    VContainer: { template: '<div><slot /></div>' },
                    VAlert: { template: '<div><slot /></div>' }
                }
            }
        })

        expect(wrapper.text()).toContain('Nothing collected yet')
        expect(wrapper.find('.word-cloud').exists()).toBe(false)
        expect(wrapper.find('.word-cloud-empty').exists()).toBe(true)
        wrapper.unmount()
    })
})
