import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WordCloud from '@/components/dashboard/WordCloud.vue'

const data = [
    { word: 'minor', word_quantity: 2 },
    { word: 'major', word_quantity: 20 },
    { word: 'middle', word_quantity: 8 }
]

describe('WordCloud', () => {
    it('renders every valid word in relevance order without a scrolling region', () => {
        const wrapper = mount(WordCloud, {
            props: { data },
            global: {
                stubs: {
                    VContainer: { template: '<div><slot /></div>' },
                    VAlert: { template: '<div><slot /></div>' }
                }
            }
        })

        expect(wrapper.findAll('.word-cloud-item').map((item) => item.text())).toEqual(['major', 'middle', 'minor'])
        expect(wrapper.find('.word-cloud-container').attributes('role')).toBe('list')
        expect(wrapper.find('.word-cloud-container').attributes('style')).toBeUndefined()
    })

    it('uses stable colors and scales frequent words more prominently', () => {
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

        const words = wrapper.findAll('.word-cloud-item')
        expect(words).toHaveLength(3)
        const majorWord = words[0]!
        const minorWord = words[2]!
        const majorStyle = majorWord.attributes('style') ?? ''
        const minorStyle = minorWord.attributes('style') ?? ''

        expect(majorStyle).toContain('font-weight: 700')
        expect(minorStyle).toContain('font-weight: 450')
        expect(majorStyle).toBe(majorWord.attributes('style'))
        expect(['#123456', '#abcdef'].some((color) => majorStyle.includes(color))).toBe(true)
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
        expect(wrapper.find('.word-cloud-container').exists()).toBe(false)
    })
})
