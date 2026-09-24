import { afterEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewWordList from '@/components/config/word-lists/NewWordList.vue'

vi.mock('@/api/config', () => ({
    createNewWordList: vi.fn(),
    updateWordList: vi.fn()
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

vi.mock('@/composables/useSpellcheck', () => ({
    useSpellcheck: () => false
}))

describe('NewWordList locale-safe category display', () => {
    let wrapper: ReturnType<typeof mountWithPlugins> | undefined

    afterEach(() => {
        wrapper?.unmount()
        wrapper = undefined
    })

    it('locale-formats entry counts and isolates list and category names', async () => {
        const entries = Array.from({ length: 1234 }, (_, index) => ({ value: `word-${index}`, description: '' }))
        wrapper = mountWithPlugins(NewWordList, {
            props: {
                editItem: {
                    id: 1,
                    name: 'List العربية',
                    description: '',
                    use_for_stop_words: false,
                    categories: [{ name: 'Category العربية', description: '', link: '', entries }]
                }
            }
        })
        await wrapper.vm.$nextTick()

        expect(document.body.textContent).toContain(new Intl.NumberFormat('en').format(entries.length))
        expect(document.body.querySelector('bdi[dir="auto"]')?.textContent).toBe('Category العربية')
        expect(document.body.querySelector('.me-2')).not.toBeNull()
        expect(document.body.querySelector('input[dir="auto"]')?.getAttribute('value')).toBe('List العربية')
    })
})
