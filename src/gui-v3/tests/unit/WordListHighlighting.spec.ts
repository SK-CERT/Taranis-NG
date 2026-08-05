import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import HighlightedText from '@/components/common/HighlightedText.vue'
import { collectHighlightWords, splitHighlightedText } from '@/utils/word-list-highlighting'

describe('word-list highlighting', () => {
    it('collects unique configured entries and prefers longer overlapping terms', () => {
        const words = collectHighlightWords([
            {
                categories: [
                    { entries: [{ value: 'risk' }, { value: 'supply chain' }, { value: '' }, { value: '<script>' }] },
                    { entries: [{ value: 'RISK' }] }
                ]
            }
        ])

        expect(words).toEqual(['supply chain', '<script>', 'risk'])
    })

    it('treats regex metacharacters as text and preserves the original content', () => {
        const segments = splitHighlightedText('C++ and a.b <script>', ['C++', 'a.b', '<script>'])

        expect(segments.filter((segment) => segment.highlighted).map((segment) => segment.text)).toEqual(['C++', 'a.b', '<script>'])
        expect(segments.map((segment) => segment.text).join('')).toBe('C++ and a.b <script>')
    })

    it('renders matches as text nodes rather than executable HTML', () => {
        const wrapper = mount(HighlightedText, {
            props: { text: '<img src=x onerror=alert(1)> critical', words: ['<img', 'critical'] }
        })

        expect(wrapper.findAll('.word-list-highlight').map((mark) => mark.text())).toEqual(['<img', 'critical'])
        expect(wrapper.find('img').exists()).toBe(false)
        expect(wrapper.html()).toContain('&lt;img')
    })

    it('renders unmodified text when disabled or no lists are available', async () => {
        const wrapper = mount(HighlightedText, {
            props: { text: 'critical issue', words: ['critical'], enabled: false }
        })

        expect(wrapper.find('.word-list-highlight').exists()).toBe(false)
        expect(wrapper.text()).toBe('critical issue')

        await wrapper.setProps({ enabled: true, words: [] })
        expect(wrapper.find('.word-list-highlight').exists()).toBe(false)
        expect(wrapper.text()).toBe('critical issue')
    })
})
