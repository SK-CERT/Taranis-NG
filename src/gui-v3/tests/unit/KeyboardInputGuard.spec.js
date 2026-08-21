import { describe, it, expect, beforeAll } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

/**
 * Keyboard shortcuts must never fire while the user is typing. The guard used to
 * recognise only `input[type="text"]`, so every other typing input - a password
 * field above all - leaked keystrokes into the shortcut handler: typing Shift+J
 * into "edit user password" triggered whatever J was bound to.
 */

const input = (type) => {
    const element = document.createElement('input')
    // Assigning an unknown type leaves `element.type` at "text", which is exactly
    // how the browser treats it, so the guard sees what it would see for real.
    element.type = type
    return element
}

describe('keyboard shortcut input guard', () => {
    // useKeyboard resolves its Pinia stores at module scope, so a store must be
    // active before the module is imported - hence the dynamic import.
    let isTypingTarget

    beforeAll(async () => {
        setActivePinia(createPinia())
        ;({ isTypingTarget } = await import('@/composables/useKeyboard'))
    })

    it.each(['text', 'password', 'email', 'number', 'search', 'tel', 'url', 'date', 'datetime-local', 'month', 'time', 'week'])(
        'treats input[type=%s] as typing, so shortcuts stay out of the way',
        (type) => {
            expect(isTypingTarget(input(type))).toBe(true)
        }
    )

    it.each(['button', 'checkbox', 'color', 'file', 'radio', 'range', 'reset', 'submit'])(
        'lets shortcuts through while input[type=%s] has focus',
        (type) => {
            expect(isTypingTarget(input(type))).toBe(false)
        }
    )

    it('treats textareas and selects as typing', () => {
        expect(isTypingTarget(document.createElement('textarea'))).toBe(true)
        expect(isTypingTarget(document.createElement('select'))).toBe(true)
    })

    it('treats a rich text editor as typing', () => {
        const editor = document.createElement('div')
        editor.className = 'ql-editor'
        editor.setAttribute('contenteditable', 'true')
        document.body.appendChild(editor)

        expect(isTypingTarget(editor)).toBe(true)

        editor.remove()
    })

    it('lets shortcuts through for ordinary elements and when nothing has focus', () => {
        expect(isTypingTarget(document.createElement('div'))).toBe(false)
        expect(isTypingTarget(document.createElement('button'))).toBe(false)
        expect(isTypingTarget(null)).toBe(false)
    })
})
