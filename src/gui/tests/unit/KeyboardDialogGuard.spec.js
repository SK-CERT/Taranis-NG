import { describe, it, expect, beforeAll, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'

/**
 * Keyboard shortcuts must not fire behind a dialog - pressing j/k or Delete behind a
 * delete confirmation acted on the list underneath. The guard first silenced *every*
 * v-dialog, though, and the news item detail is one: ArrowLeft / h stopped closing it and
 * r / i / u / Delete stopped acting on the item being read. The detail is the dialog the
 * shortcuts are built around, so it is the one exception.
 */

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const overlay = (...classes) => {
    const element = document.createElement('div')
    element.className = ['v-overlay', ...classes].join(' ')
    document.body.appendChild(element)
    return element
}

describe('keyboard shortcut dialog guard', () => {
    // useKeyboard resolves its Pinia stores at module scope, so a store must be
    // active before the module is imported - hence the dynamic import.
    let isBlockingDialogOpen
    let wrapper

    beforeAll(async () => {
        setActivePinia(createPinia())
        ;({ isBlockingDialogOpen } = await import('@/composables/useKeyboard'))
    })

    afterEach(() => {
        wrapper?.unmount()
        wrapper = undefined
        document.body.innerHTML = ''
    })

    it('lets shortcuts through when no dialog is open', () => {
        expect(isBlockingDialogOpen()).toBe(false)
    })

    it('blocks shortcuts behind an open dialog', () => {
        overlay('v-dialog', 'v-overlay--active')

        expect(isBlockingDialogOpen()).toBe(true)
    })

    it('lets shortcuts through while only the news item detail is open', () => {
        overlay('v-dialog', 'v-overlay--active', 'news-item-detail-dialog')

        expect(isBlockingDialogOpen()).toBe(false)
    })

    it('blocks shortcuts behind a dialog opened on top of the news item detail', () => {
        overlay('v-dialog', 'v-overlay--active', 'news-item-detail-dialog')
        overlay('v-dialog', 'v-overlay--active')

        expect(isBlockingDialogOpen()).toBe(true)
    })

    it('ignores closed dialogs and overlays that are not dialogs', () => {
        overlay('v-dialog')
        overlay('v-menu', 'v-overlay--active')
        overlay('v-tooltip', 'v-overlay--active')

        expect(isBlockingDialogOpen()).toBe(false)
    })

    it('recognises the real NewsItemDetailDialog as the exception', async () => {
        wrapper = mountWithPlugins(NewsItemDetailDialog, {
            props: {
                newsItem: { id: 1, title: 'Item', news_items: [{ news_item_data: { content: '<p>Body</p>', attributes: [] } }] }
            },
            global: { stubs: { AssessItemActions: true, NewsItemAttribute: true, Editor: true } }
        })
        // Opened the way ContentDataAssess does it: the dialog follows modelValue changes only.
        await wrapper.setProps({ modelValue: true })

        expect(document.querySelector('.v-overlay--active.v-dialog.news-item-detail-dialog')).not.toBeNull()
        expect(isBlockingDialogOpen()).toBe(false)
    })
})
