import { describe, it, expect, beforeAll, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

/**
 * A list refresh puts the focus back on the current card, so keyboard navigation carries on
 * from there. It must not do that while a dialog is open: the autosave of an Assess comment
 * refreshes the list, and taking the focus to the card behind the dialog threw away
 * whatever the user typed next (issue #1753).
 */
describe('keyboard card focus on a list refresh', () => {
    // useKeyboard resolves its Pinia stores at module scope, so a store must be
    // active before the module is imported - hence the dynamic import.
    let useKeyboard

    beforeAll(async () => {
        setActivePinia(createPinia())
        ;({ useKeyboard } = await import('@/composables/useKeyboard'))
    })

    afterEach(() => {
        document.body.innerHTML = ''
    })

    const renderCards = () => {
        const list = document.createElement('div')
        list.className = 'card-list'
        for (const id of [1, 2]) {
            const card = document.createElement('div')
            card.className = 'card-item'
            card.tabIndex = 0
            card.setAttribute('data-id', String(id))
            list.appendChild(card)
        }
        document.body.appendChild(list)
    }

    const keyboardOnCard = (id) => {
        renderCards()
        const keyboard = useKeyboard('assess', {})
        keyboard.reindexCardItems('append')
        keyboard.setCurrentCard(id)
        return keyboard
    }

    it('focuses the current card again after a refresh', () => {
        const keyboard = keyboardOnCard(2)

        keyboard.reindexCardItems('refresh')

        expect(document.activeElement?.getAttribute('data-id')).toBe('2')
    })

    const openDialogWith = (element) => {
        const dialog = document.createElement('div')
        dialog.className = 'v-overlay v-overlay--active v-dialog'
        dialog.appendChild(element)
        document.body.appendChild(dialog)
        element.focus()
        return element
    }

    it('leaves the focus in the editor of an open dialog', () => {
        const keyboard = keyboardOnCard(2)
        const editor = document.createElement('div')
        editor.setAttribute('contenteditable', 'true')
        openDialogWith(editor)

        keyboard.reindexCardItems('refresh')

        expect(document.activeElement).toBe(editor)
    })

    it('leaves the focus on a button of an open dialog', () => {
        const keyboard = keyboardOnCard(2)
        const button = openDialogWith(document.createElement('button'))

        keyboard.reindexCardItems('append')

        expect(document.activeElement).toBe(button)
    })

    it('leaves the focus in a field outside any dialog', () => {
        const keyboard = keyboardOnCard(2)
        const search = document.createElement('input')
        document.body.appendChild(search)
        search.focus()

        keyboard.reindexCardItems('refresh')

        expect(document.activeElement).toBe(search)
    })
})
