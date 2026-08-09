import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemAttribute from '@/components/assess/NewsItemAttribute.vue'

const apiMocks = vi.hoisted(() => ({ downloadAttachment: vi.fn() }))

vi.mock('@/api/analyze', () => ({ downloadAttachment: apiMocks.downloadAttachment }))

const mountAttribute = (attribute: Record<string, unknown>) =>
    mountWithPlugins(NewsItemAttribute, {
        props: {
            attribute: { id: 7, key: 'مفتاح attribute', value: 'قيمة value', binary_mime_type: '', ...attribute },
            newsItemData: { id: 42 }
        }
    })

describe('NewsItemAttribute direction-safe rendering', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('uses logical spacing and isolates directly rendered text', () => {
        const wrapper = mountAttribute({})
        const isolatedText = wrapper.findAll('bdi[dir="auto"]')
        const keyContainer = wrapper.find('bdi[dir="auto"]').element.parentElement

        expect(isolatedText.map((value) => value.text())).toEqual(['مفتاح attribute', 'قيمة value'])
        expect(keyContainer?.style.marginInlineEnd).toBe('20px')
        expect(keyContainer?.style.marginRight).toBe('')
    })

    it('preserves the binary download target and isolates its displayed value', async () => {
        const wrapper = mountAttribute({ binary_mime_type: 'application/pdf', value: 'تقرير report.pdf' })

        expect(wrapper.findAll('bdi[dir="auto"]').map((value) => value.text())).toEqual(['مفتاح attribute', 'تقرير report.pdf'])
        await wrapper.find('button').trigger('click')

        expect(apiMocks.downloadAttachment).toHaveBeenCalledOnce()
        expect(apiMocks.downloadAttachment).toHaveBeenCalledWith('/assess/news-item-data/42/attributes/7/file', undefined)
    })
})
