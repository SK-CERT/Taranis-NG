import { describe, it, expect, beforeAll, beforeEach, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

/**
 * Hovering a card in Assess makes it the current one: the shortcuts act on it and the arrows
 * carry on from it. It stays current when the mouse leaves. Hovering never scrolls, and never
 * takes the focus out of a field being typed in.
 */
describe('hovering a card makes it current', () => {
    let useKeyboard
    let HotkeyAction
    let keyboard
    let x = 0

    beforeAll(async () => {
        setActivePinia(createPinia())
        ;({ useKeyboard } = await import('@/composables/useKeyboard'))
        ;({ HotkeyAction } = await import('@/types/settings'))
    })

    const card = (id) => document.querySelector(`.card-item[data-id="${id}"]`)

    const renderCards = (ids) => {
        const scroller =
            document.querySelector('.view-content') ??
            document.body.appendChild(Object.assign(document.createElement('div'), { className: 'view-content' }))
        scroller.scrollTo = vi.fn()
        scroller.innerHTML = ''
        const list = document.createElement('div')
        list.className = 'card-list'
        for (const id of ids) {
            const element = document.createElement('div')
            element.className = 'card-item'
            element.tabIndex = 0
            element.setAttribute('data-id', String(id))
            element.innerHTML = `<span class="title">${id}</span><button data-action="READ">read</button>`
            list.appendChild(element)
        }
        scroller.appendChild(list)
        return scroller
    }

    // A real mouse move over an element inside the card (the event bubbles to window).
    const hover = (id, pointerType = 'mouse') => {
        x += 10
        const event = new window.MouseEvent('pointermove', { bubbles: true, clientX: x, clientY: 5 })
        Object.defineProperty(event, 'pointerType', { value: pointerType })
        card(id).querySelector('.title').dispatchEvent(event)
    }

    beforeEach(() => {
        renderCards([1, 2, 3])
        keyboard = useKeyboard('assess', {})
        keyboard.state.value.shortcuts = [
            { key: 'j', alias: HotkeyAction.COLLECTION_DOWN_1 },
            { key: 'r', alias: HotkeyAction.READ_ITEM }
        ]
        keyboard.reindexCardItems('append')
        window.addEventListener('pointermove', keyboard.onPointerMove)
    })

    afterEach(() => {
        window.removeEventListener('pointermove', keyboard.onPointerMove)
        document.body.innerHTML = ''
        vi.useRealTimers()
    })

    it('makes the hovered card current, without scrolling or taking the focus', () => {
        const scroller = document.querySelector('.view-content')
        hover(2)

        expect(keyboard.currentCard.value.element).toBe(card(2))
        expect(card(2).getAttribute('data-focused')).toBe('true')
        expect(document.activeElement).toBe(document.body)
        expect(scroller.scrollTo).not.toHaveBeenCalled()
    })

    it('lets the shortcuts act on it, and the arrows carry on from it', () => {
        hover(2)
        const clicked = vi.fn()
        card(2).querySelector('[data-action="READ"]').addEventListener('click', clicked)

        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'r' }))
        expect(clicked).toHaveBeenCalledOnce()

        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'j' }))
        expect(keyboard.currentCard.value.element).toBe(card(3))
    })

    it('moves the focus along only when the focus was on a card already', () => {
        card(1).focus()
        hover(3)
        expect(document.activeElement).toBe(card(3))

        const search = document.body.appendChild(Object.assign(document.createElement('input'), { id: 'search' }))
        search.focus()
        hover(2)
        expect(document.activeElement).toBe(search)
        expect(keyboard.currentCard.value.element).toBe(card(2))
    })

    it('ignores a touch, a pointer that did not move, and the scroll right after a keyboard move', () => {
        hover(1)
        // The cards scroll under a mouse resting still: the same coordinates again.
        const resting = new window.MouseEvent('pointermove', { bubbles: true, clientX: x, clientY: 5 })
        card(3).dispatchEvent(resting)
        expect(keyboard.currentCard.value.element).toBe(card(1))

        hover(2, 'touch')
        expect(keyboard.currentCard.value.element).toBe(card(1))

        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'j' }))
        expect(keyboard.currentCard.value.element).toBe(card(2))
        hover(3)
        expect(keyboard.currentCard.value.element).toBe(card(2))
    })

    it('ignores the list behind a dialog', () => {
        const dialog = document.body.appendChild(
            Object.assign(document.createElement('div'), { className: 'v-overlay v-overlay--active v-dialog' })
        )
        hover(3)
        expect(keyboard.currentCard.value?.element).not.toBe(card(3))
        dialog.remove()
    })

    it('keeps the current card when cards arrive above it', () => {
        hover(2)
        const list = document.querySelector('.card-list')
        const newer = card(1).cloneNode(true)
        newer.setAttribute('data-id', '0')
        list.prepend(newer)

        keyboard.reindexCardItems('refresh')

        expect(keyboard.currentCard.value.element).toBe(card(2))
        const clicked = vi.fn()
        card(2).querySelector('[data-action="READ"]').addEventListener('click', clicked)
        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'r' }))
        expect(clicked).toHaveBeenCalledOnce()
    })
})

describe('Analyze and Publish lists', () => {
    let useKeyboard
    let HotkeyAction

    beforeAll(async () => {
        setActivePinia(createPinia())
        ;({ useKeyboard } = await import('@/composables/useKeyboard'))
        ;({ HotkeyAction } = await import('@/types/settings'))
    })

    afterEach(() => {
        document.body.innerHTML = ''
    })

    it('move through their cards and open one, reading the list as it is now; other shortcuts do nothing', () => {
        const scroller = document.body.appendChild(Object.assign(document.createElement('div'), { className: 'view-content' }))
        scroller.scrollTo = vi.fn()
        scroller.innerHTML =
            '<div class="analyze-list"><div class="card-item" data-id="7" tabindex="0"><button data-action="READ"></button></div></div>'
        const keyboard = useKeyboard('analyze', {}, { listSelector: '.analyze-list', navigationOnly: true })
        keyboard.state.value.shortcuts = [
            { key: 'j', alias: HotkeyAction.COLLECTION_DOWN_1 },
            { key: 'Enter', alias: HotkeyAction.SHOW_ITEM_1 },
            { key: 'r', alias: HotkeyAction.READ_ITEM }
        ]
        // The list renders after the view is set up: more cards arrive without anyone saying so.
        scroller.querySelector('.analyze-list').insertAdjacentHTML('beforeend', '<div class="card-item" data-id="8" tabindex="0"></div>')
        const opened = vi.fn()
        scroller.querySelector('[data-id="8"]').addEventListener('click', opened)
        const read = vi.fn()
        scroller.querySelector('[data-action="READ"]').addEventListener('click', read)

        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'j' })) // the first key only shows the current card
        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'j' }))
        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'Enter' }))
        expect(opened).toHaveBeenCalledOnce()

        keyboard.keyAction(new KeyboardEvent('keydown', { key: 'r' }))
        expect(read).not.toHaveBeenCalled()
    })
})
