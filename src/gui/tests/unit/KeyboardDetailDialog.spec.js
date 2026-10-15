import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { useSettingsStore } from '@/stores/settings'
import { useAssessStore } from '@/stores/assess'
import { Action } from '@/types/actions'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

/**
 * While a news item is open in the detail dialog, the shortcuts belong to it. The up / down
 * keys moved along the card list behind the dialog instead of scrolling the item, and like /
 * dislike / read... pressed the card's button behind it: the change was made, but the
 * dialog's icon never showed it.
 */
describe('keyboard shortcuts with the news item detail open', () => {
    // useKeyboard resolves its Pinia stores at module scope, so a store must be
    // active before the module is imported - hence the dynamic import. The stores are
    // taken here too: mounting a component activates a fresh Pinia, and that one is
    // not the composable's.
    let useKeyboard
    let settingsStore
    let assessStore
    let keyboard
    let cardLike

    beforeAll(async () => {
        setActivePinia(createPinia())
        settingsStore = useSettingsStore()
        assessStore = useAssessStore()
        ;({ useKeyboard } = await import('@/composables/useKeyboard'))
    })

    const actionButton = (action) => {
        const button = document.createElement('button')
        button.setAttribute('data-action', action)
        button.click = vi.fn()
        return button
    }

    const renderCards = () => {
        const list = document.createElement('div')
        list.className = 'card-list'
        for (const id of [1, 2]) {
            const card = document.createElement('div')
            card.className = 'card-item'
            card.tabIndex = 0
            card.setAttribute('data-id', String(id))
            const like = actionButton(Action.LIKE)
            card.appendChild(like)
            if (id === 1) {
                cardLike = like
            }
            list.appendChild(card)
        }
        document.body.appendChild(list)
    }

    const press = (key, options = {}) => {
        const event = new KeyboardEvent('keydown', { key, cancelable: true, ...options })
        keyboard.keyAction(event)
        return event
    }

    beforeEach(() => {
        settingsStore.settings = [{ key: 'HOTKEYS', value: 'true' }]
        settingsStore.resetHotkeys()
        assessStore.multiSelect(false)

        renderCards()
        keyboard = useKeyboard('assess', {})
        keyboard.onInit()
        keyboard.reindexCardItems('append')
        keyboard.setCurrentCard(1)
    })

    afterEach(() => {
        document.body.innerHTML = ''
    })

    it('moves along the list while no item is open', () => {
        press('ArrowDown')

        expect(keyboard.pos.value).toBe(1)
    })

    describe('on a stand-in dialog', () => {
        let dialogLike
        let scroller
        let hiddenScroller

        const scrollable = () => {
            const element = document.createElement('div')
            element.setAttribute('data-detail-scroll', '')
            element.scrollBy = vi.fn()
            element.scrollTo = vi.fn()
            Object.defineProperty(element, 'scrollHeight', { value: 900 })
            return element
        }

        // The source tab is inactive and scrolls its article body; the active tab scrolls whole.
        beforeEach(() => {
            const dialog = document.createElement('div')
            dialog.className = 'v-overlay v-overlay--active v-dialog news-item-detail-dialog'
            dialog.appendChild((dialogLike = actionButton(Action.LIKE)))
            const sourcePane = document.createElement('div')
            sourcePane.className = 'pane'
            sourcePane.appendChild((hiddenScroller = scrollable()))
            scroller = scrollable()
            scroller.classList.add('pane', 'pane--active')
            dialog.append(sourcePane, scroller)
            document.body.appendChild(dialog)
        })

        it('scrolls the open item down instead of moving along the list', () => {
            const event = press('ArrowDown')
            press('j')

            expect(event.defaultPrevented).toBe(true)
            expect(scroller.scrollBy).toHaveBeenCalledTimes(2)
            expect(scroller.scrollBy).toHaveBeenCalledWith({ top: 40, behavior: 'smooth' })
            expect(hiddenScroller.scrollBy).not.toHaveBeenCalled()
            expect(keyboard.pos.value).toBe(0)
        })

        it('scrolls the open item up, and jumps while the key is held', () => {
            press('ArrowUp')
            press('k', { repeat: true })

            expect(scroller.scrollBy).toHaveBeenNthCalledWith(1, { top: -40, behavior: 'smooth' })
            expect(scroller.scrollBy).toHaveBeenNthCalledWith(2, { top: -40, behavior: 'instant' })
        })

        it('scrolls the open item to its top and bottom on Home / End', () => {
            press('End')
            press('Home')

            expect(scroller.scrollTo).toHaveBeenNthCalledWith(1, { top: 900, behavior: 'smooth' })
            expect(scroller.scrollTo).toHaveBeenNthCalledWith(2, { top: 0, behavior: 'smooth' })
            expect(keyboard.pos.value).toBe(0)
        })

        it('presses the open item’s own button, so the dialog shows the change', () => {
            press('u')

            expect(dialogLike.click).toHaveBeenCalledTimes(1)
            expect(cardLike.click).not.toHaveBeenCalled()
        })

        it('leaves the list behind the open item alone', () => {
            press('s')

            expect(assessStore.getMultiSelect).toBe(false)
        })
    })

    describe('on the real NewsItemDetailDialog', () => {
        let wrapper
        let originalScrollBy
        let scrolled

        beforeEach(async () => {
            scrolled = []
            originalScrollBy = HTMLElement.prototype.scrollBy
            HTMLElement.prototype.scrollBy = function () {
                scrolled.push(this)
            }
            wrapper = mountWithPlugins(NewsItemDetailDialog, {
                props: {
                    newsItem: {
                        id: 1,
                        title: 'Item',
                        likes: 0,
                        dislikes: 0,
                        news_items: [{ id: 10, news_item_data: { content: '<p>Body</p>', attributes: [] } }]
                    }
                },
                global: { stubs: { NewsItemAttribute: true, RichTextEditor: true } }
            })
            // Opened the way ContentDataAssess does it: the dialog follows modelValue changes only.
            await wrapper.setProps({ modelValue: true })
        })

        afterEach(() => {
            HTMLElement.prototype.scrollBy = originalScrollBy
            wrapper.unmount()
        })

        it('scrolls the article body of the source tab', () => {
            press('j')

            expect(scrolled).toHaveLength(1)
            expect(scrolled[0].classList.contains('source-body')).toBe(true)
        })

        it('scrolls the whole tab of the comments', async () => {
            // The dialog is teleported to the body, out of the wrapper's reach.
            ;[...document.querySelectorAll('.v-tab')].find((tab) => tab.textContent.trim() === 'Comments').click()
            await nextTick()

            press('j')

            expect(scrolled).toHaveLength(1)
            expect(scrolled[0].classList.contains('tab-pane')).toBe(true)
        })

        it('likes the open item from the dialog', () => {
            press('u')

            expect(wrapper.emitted('action')).toEqual([[{ action: Action.LIKE, newsItem: expect.objectContaining({ id: 1 }) }]])
            expect(cardLike.click).not.toHaveBeenCalled()
        })
    })
})
