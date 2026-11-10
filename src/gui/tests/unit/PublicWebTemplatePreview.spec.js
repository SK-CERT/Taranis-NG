import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import PublicWebTemplatePreview from '@/components/config/public-web/PublicWebTemplatePreview.vue'

const api = vi.hoisted(() => ({
    getPublicWebTemplatePreviewOptions: vi.fn(),
    previewPublicWebTemplate: vi.fn()
}))

vi.mock('@/api/config', () => api)

const OPTIONS = {
    webs: [
        { id: 1, name: 'Main', node: 'node', unavailable: null, languages: ['en', 'cs'], default_language: 'cs' },
        { id: 2, name: 'Old', node: 'off', unavailable: 'Its public-web node is switched off', languages: ['en'], default_language: 'en' }
    ],
    web_id: 1,
    products: [
        { id: 42, title: 'Newest advisory', created: '2026-11-07T10:00:00' },
        { id: 41, title: 'Older advisory', created: '2026-11-01T10:00:00' }
    ]
}

const mountPreview = (props = {}) =>
    mountWithPlugins(PublicWebTemplatePreview, {
        props: {
            active: true,
            productPresetId: 5,
            reportItemTypeId: null,
            source: '{% extends "builtin/product_base.html" %}',
            requireTlpClear: true,
            publicWebIds: [],
            ...props
        }
    })

describe('PublicWebTemplatePreview', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        api.getPublicWebTemplatePreviewOptions.mockResolvedValue({ data: OPTIONS })
        api.previewPublicWebTemplate.mockResolvedValue({
            data: { view: 'detail', page_url: '/config/public-web-templates/preview/ticket-1', errors: [], warnings: [] }
        })
    })

    afterEach(() => {
        vi.useRealTimers()
    })

    it('renders the newest product the template applies to, on the chosen web in its language', async () => {
        const wrapper = mountPreview()
        await flushPromises()

        expect(api.getPublicWebTemplatePreviewOptions).toHaveBeenCalledWith({
            product_preset_id: 5,
            report_item_type_id: null,
            builtin: null,
            web_id: null,
            public_web_ids: []
        })
        expect(api.previewPublicWebTemplate).toHaveBeenCalledWith({
            template: {
                product_preset_id: 5,
                report_item_type_id: null,
                source: '{% extends "builtin/product_base.html" %}',
                require_tlp_clear: true,
                public_web_ids: []
            },
            web_id: 1,
            language: 'cs',
            product_id: 42,
            view: 'detail'
        })
        // Served by core with a policy of its own, not inline: an inline page takes the GUI's.
        const frame = wrapper.find('[data-test="preview-frame"]')
        expect(frame.attributes('src')).toBe('/api/v1/config/public-web-templates/preview/ticket-1')
        expect(frame.attributes('srcdoc')).toBeUndefined()
        // An origin of its own; the one script core's policy lets run is the web's colour-mode selector.
        expect(frame.attributes('sandbox')).toBe('allow-scripts')
        // The same page, in a tab of the browser.
        const opened = vi.spyOn(window, 'open').mockReturnValue(null)
        await wrapper.find('[data-test="preview-open"]').trigger('click')
        expect(opened).toHaveBeenCalledWith('/api/v1/config/public-web-templates/preview/ticket-1', '_blank', 'noopener,noreferrer')
        opened.mockRestore()
        wrapper.unmount()
    })

    it('asks nothing while it is closed', async () => {
        const wrapper = mountPreview({ active: false })
        await flushPromises()

        expect(api.getPublicWebTemplatePreviewOptions).not.toHaveBeenCalled()
        expect(api.previewPublicWebTemplate).not.toHaveBeenCalled()
        wrapper.unmount()
    })

    it('follows the editor a moment after typing stops', async () => {
        vi.useFakeTimers()
        const wrapper = mountPreview()
        await flushPromises()
        api.previewPublicWebTemplate.mockClear()

        await wrapper.setProps({ source: '{% extends "builtin/product_base.html" %}{# 1 #}' })
        await wrapper.setProps({ source: '{% extends "builtin/product_base.html" %}{# 12 #}' })
        vi.advanceTimersByTime(500)
        expect(api.previewPublicWebTemplate).not.toHaveBeenCalled()

        vi.advanceTimersByTime(400)
        await flushPromises()
        expect(api.previewPublicWebTemplate).toHaveBeenCalledOnce()
        expect(api.previewPublicWebTemplate.mock.calls[0][0].template.source).toContain('{# 12 #}')
        wrapper.unmount()
    })

    it('opens the next rendering in the colour mode picked inside the page', async () => {
        vi.useFakeTimers()
        const wrapper = mountPreview()
        await flushPromises()
        const frame = () => wrapper.find('[data-test="preview-frame"]')
        const post = (source, data) => window.dispatchEvent(new MessageEvent('message', { source, data }))
        // happy-dom loads no frame page: the frame's window is stood in for.
        const pageWindow = {}
        Object.defineProperty(frame().element, 'contentWindow', { value: pageWindow, configurable: true })

        // Another window, or something that is not a mode: ignored.
        post(window, { taranisPublicWebTheme: 'dark' })
        post(pageWindow, { taranisPublicWebTheme: 'sepia' })
        // The page's selector: the shown page stays as it is (no reload)...
        post(pageWindow, { taranisPublicWebTheme: 'dark' })
        await flushPromises()
        expect(frame().attributes('src')).toBe('/api/v1/config/public-web-templates/preview/ticket-1')

        // ...and the next one opens dark, in the frame and in a tab.
        api.previewPublicWebTemplate.mockResolvedValueOnce({
            data: { view: 'detail', page_url: '/config/public-web-templates/preview/ticket-2', errors: [], warnings: [] }
        })
        await wrapper.setProps({ source: '{% extends "builtin/product_base.html" %}{# 1 #}' })
        vi.advanceTimersByTime(800)
        await flushPromises()
        expect(frame().attributes('src')).toBe('/api/v1/config/public-web-templates/preview/ticket-2#theme=dark')
        const opened = vi.spyOn(window, 'open').mockReturnValue(null)
        await wrapper.find('[data-test="preview-open"]').trigger('click')
        expect(opened).toHaveBeenCalledWith(
            '/api/v1/config/public-web-templates/preview/ticket-2#theme=dark',
            '_blank',
            'noopener,noreferrer'
        )
        opened.mockRestore()
        wrapper.unmount()
    })

    it('renders again in a language picked in the language menu of the page', async () => {
        vi.useFakeTimers()
        const wrapper = mountPreview()
        await flushPromises()
        // The web's default language, picked on opening, renders once more: let it.
        vi.advanceTimersByTime(800)
        await flushPromises()
        api.previewPublicWebTemplate.mockClear()
        const pageWindow = {}
        Object.defineProperty(wrapper.find('[data-test="preview-frame"]').element, 'contentWindow', { value: pageWindow, configurable: true })
        const post = (data) => window.dispatchEvent(new MessageEvent('message', { source: pageWindow, data }))
        // No select of its own: the page has one.
        expect(wrapper.find('[data-test="preview-language"]').exists()).toBe(false)

        // A language the web does not offer: nothing to render.
        post({ taranisPublicWebLanguage: 'de' })
        await flushPromises()
        vi.advanceTimersByTime(800)
        await flushPromises()
        expect(api.previewPublicWebTemplate).not.toHaveBeenCalled()

        post({ taranisPublicWebLanguage: 'en' })
        await flushPromises()
        vi.advanceTimersByTime(800)
        await flushPromises()
        expect(api.previewPublicWebTemplate).toHaveBeenCalledOnce()
        expect(api.previewPublicWebTemplate.mock.calls[0][0].language).toBe('en')
        wrapper.unmount()
    })

    it('lists the template failures and the reasons the web would not show the product', async () => {
        api.previewPublicWebTemplate.mockResolvedValue({
            data: {
                view: 'detail',
                page_url: '/config/public-web-templates/preview/ticket-2',
                errors: [{ template: 'product/5', line: 3, message: 'TypeError: nope' }],
                warnings: ['The web would not show this product: TLP AMBER must not be published']
            }
        })
        const wrapper = mountPreview()
        await flushPromises()

        expect(wrapper.find('[data-test="preview-template-errors"]').text()).toContain('product/5, line 3: TypeError: nope')
        expect(wrapper.find('[data-test="preview-warning"]').text()).toContain('TLP AMBER')
        wrapper.unmount()
    })

    it('shows the whole RSS item', async () => {
        api.previewPublicWebTemplate.mockResolvedValue({
            data: {
                view: 'rss',
                rss: { title: 'Newest advisory', link: 'https://web.example/reports/42', description: 'Plain text' },
                xml: '<item><title>Newest advisory</title></item>',
                errors: [],
                warnings: []
            }
        })
        const wrapper = mountPreview()
        await flushPromises()

        const rss = wrapper.find('[data-test="preview-rss"]')
        expect(rss.text()).toContain('Newest advisory')
        expect(rss.find('a').attributes('href')).toBe('https://web.example/reports/42')
        expect(rss.text()).toContain('Plain text')
        expect(rss.find('pre').text()).toBe('<item><title>Newest advisory</title></item>')
        // No page to open.
        expect(wrapper.find('[data-test="preview-frame"]').exists()).toBe(false)
        expect(wrapper.find('[data-test="preview-open"]').classes()).toContain('v-btn--disabled')
        wrapper.unmount()
    })

    it('keeps the last preview under the reason a new one could not be made', async () => {
        vi.useFakeTimers()
        const wrapper = mountPreview()
        await flushPromises()

        api.previewPublicWebTemplate.mockRejectedValueOnce({
            response: { status: 400, data: { error: 'Template error on line 1: unexpected end' } }
        })
        await wrapper.setProps({ source: '{% if %}' })
        vi.advanceTimersByTime(900)
        await flushPromises()

        expect(wrapper.find('[data-test="preview-error"]').text()).toBe('Template error on line 1: unexpected end')
        expect(wrapper.find('[data-test="preview-frame"]').exists()).toBe(true)
        wrapper.unmount()
    })

    it('says to choose a target first', async () => {
        const wrapper = mountPreview({ productPresetId: null })
        await flushPromises()

        expect(wrapper.text()).toContain('Choose what the template is for')
        expect(api.getPublicWebTemplatePreviewOptions).not.toHaveBeenCalled()
        wrapper.unmount()
    })
})
