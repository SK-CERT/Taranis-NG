import { ref, computed, nextTick, Ref, ComputedRef, onMounted, onUnmounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useConfigStore } from '@/stores/config'
import { useAssessStore } from '@/stores/assess'
import { Settings, HotkeyAction, type SettingEntry, type SettingKey, type HotkeyActionType } from '@/types/settings'
import { Action, type ActionKey } from '@/types/actions'
import { type GroupNavItem } from '@/types/routing'
import type { Router } from 'vue-router'

const settingsStore = useSettingsStore()
const configStore = useConfigStore()
const assessStore = useAssessStore()

// Input types that do not accept typed characters, so a shortcut may still fire
// while one has focus. Everything else - text, password, email, number, search,
// tel, url, date... - swallows the keystroke. The list is deliberately of what
// is *safe* rather than of what types: an input type nobody thought of must not
// silently leak keystrokes into the shortcut handler, which is how a password
// field came to trigger shortcuts (users could not type Shift+J into one).
const NON_TYPING_INPUT_TYPES = new Set(['button', 'checkbox', 'color', 'file', 'hidden', 'image', 'radio', 'range', 'reset', 'submit'])

/**
 * Tell whether the element being typed into should swallow keyboard shortcuts.
 *
 * Exported for the unit tests; the composable reads `document.activeElement`.
 */
export function isTypingTarget(element: Element | null): boolean {
    if (!element) return false

    if (element.tagName === 'INPUT') {
        return !NON_TYPING_INPUT_TYPES.has((element as HTMLInputElement).type)
    }
    if (element.tagName === 'TEXTAREA' || element.tagName === 'SELECT') return true

    // Covers rich text editors (Quill's .ql-editor among them), including a
    // focused descendant of a contenteditable container.
    return (element as HTMLElement).isContentEditable === true
}

interface Shortcut {
    key: string
    alias: HotkeyActionType
}

interface CardInfo {
    element: HTMLElement
    // data_id: string
}

interface KeyboardState {
    target: string
    pos: number
    use_focus: boolean
    cardItems: CardInfo[]
    shortcuts: Shortcut[]
    keyActionEnabled: boolean
    dialogCloseCallback: (() => void) | null
    reloadCallback: (() => void) | null
}

export function useKeyboard(targetId: string, router: Router) {
    // ============ STATE ============
    const state = ref<KeyboardState>({
        target: targetId,
        pos: 0,
        use_focus: false,
        cardItems: [],
        shortcuts: [],
        keyActionEnabled: true,
        dialogCloseCallback: null,
        reloadCallback: null
    })

    // ============ COMPUTED ============
    const currentCard = computed(() => {
        if (state.value.pos >= 0 && state.value.pos < state.value.cardItems.length) {
            return state.value.cardItems[state.value.pos]
        }
        return null
    })

    // ============ METHODS ============
    function getCurrentCardElement(): HTMLElement | null {
        return currentCard.value?.element || null
    }

    function updateCardsFocus(): void {
        // console.log('[Keyboard] updateCardsFocus')
        // Remove focus from all cards
        state.value.cardItems.forEach((card) => {
            card.element.removeAttribute('data-focused')
        })
        updateCardFocus()
    }

    function updateCardFocus(): void {
        if (state.value.use_focus) {
            const card = getCurrentCardElement()
            if (!card) {
                return
            }
            // console.log('[Keyboard] updateCardFocus:', String(state.value.pos))
            card.setAttribute('data-focused', 'true') // not used yet, but can be used for styling
            card.focus()
        }
    }

    function scrollToTop(): void {
        const container = document.querySelector<HTMLElement>('.view-content')
        if (!container) {
            console.warn('[Keyboard] Scroll container not found')
            return
        }
        // console.log('[Keyboard] scrollToTop before:', container.scrollTop)
        container.scrollTo({ top: 0, behavior: 'instant' })
    }

    function scrollToCard(): void {
        const card = getCurrentCardElement()
        const container = document.querySelector<HTMLElement>('.view-content')
        if (!card || !container) {
            console.warn('[Keyboard] Scroll container or card not found')
            return
        }

        const offset = card.offsetHeight + 20
        const cardTop = card.getBoundingClientRect().top - container.getBoundingClientRect().top
        const target = Math.max(0, container.scrollTop + cardTop - offset)

        // console.log('[Keyboard] scrollToCard', { current: container.scrollTop, target, offset })
        container.scrollTo({ top: target, behavior: 'smooth' })
    }

    function setPosition(newPos: number): void {
        if (state.value.cardItems.length === 0) {
            console.warn('[Keyboard] setPosition: No card items available')
            return
        }
        // Clamp position within valid range
        state.value.pos = Math.max(0, Math.min(newPos, state.value.cardItems.length - 1))
        // console.log(`[Keyboard] Position changed: ${state.value.pos} (total: ${state.value.cardItems.length})`)

        // Ensure focus flag is set
        if (!state.value.use_focus) {
            state.value.use_focus = true
        }
        // Update focus and scroll
        updateCardsFocus()
        scrollToCard()
    }

    function moveUp(): void {
        if (state.value.pos > 0) {
            setPosition(state.value.pos - 1)
        }
    }

    function moveDown(): void {
        if (state.value.pos < state.value.cardItems.length - 1) {
            setPosition(state.value.pos + 1)
        }
    }

    function moveToStart(): void {
        setPosition(0)
    }

    function moveToEnd(): void {
        setPosition(state.value.cardItems.length - 1)
    }

    function resetPosition(): void {
        // console.log(`[Keyboard] resetPosition 0`)
        state.value.pos = 0
        state.value.use_focus = false
    }

    function getKeyAlias(event: KeyboardEvent): HotkeyActionType | null {
        // Don't process events with Ctrl or Alt keys
        if (event.ctrlKey || event.altKey) {
            return null
        }
        // Find matching shortcut by key
        for (const shortcut of state.value.shortcuts) {
            if (shortcut.key === event.key) {
                return shortcut.alias
            }
        }
        return null
    }

    function reindexCardItems(mode: string): void {
        if (!state.value.keyActionEnabled) return

        const elements = document.querySelectorAll<HTMLElement>('.card-list .card-item')
        state.value.cardItems = Array.from(elements).map((element) => ({
            element
        }))
        // console.log(`[Keyboard] Reindexed ${state.value.cardItems.length} cards, (${mode})`)
        switch (mode) {
            case 'reset':
            case 'reload':
                resetPosition()
                scrollToTop()
                break

            default: // refresh, append
                updateCardFocus()
                break
        }
    }

    function isInputFieldFocused(): boolean {
        return isTypingTarget(document.activeElement)
    }

    function groupPosition(direction: boolean): void {
        const groups = configStore.osintSourceGroupsForAssess as GroupNavItem[]
        const activeGroupId = assessStore.getCurrentGroup
        // console.log(`[Keyboard] groupPosition`, activeGroupId)
        let index: number
        for (index = 0; index < groups.length; index++) {
            if (String(groups[index]?.id) === activeGroupId) {
                break
            }
        }
        if (direction) {
            if (index < groups.length) {
                index++
            }
        } else {
            if (index > 0) {
                index--
            }
        }
        const group = groups[index]
        if (group) {
            router.push(`/assess/group/${group.id}`)
        }
    }

    function triggerCardAction(action: ActionKey): void {
        if (assessStore.getMultiSelect) return
        // console.log(`[Keyboard] triggerCardAction: ${action}`)
        const card = getCurrentCardElement()
        const button = card?.querySelector(`[data-action="${action}"]`) as HTMLElement | null
        if (!button) {
            console.warn(`[Keyboard] Card action not found: ${action}`)
            return
        }
        button.click()
    }

    function triggerToolbarAction(action: ActionKey): void {
        if (!assessStore.getMultiSelect) return
        // console.log(`[Keyboard] triggerToolbarAction: ${action}`)
        const button = document.querySelector<HTMLElement>(`[data-multi-action="${action}"]`)
        if (!button) {
            console.warn(`[Keyboard] Toolbar action not found: ${action}`)
            return
        }
        button.click()
    }

    function triggerAction(action: ActionKey): void {
        if (assessStore.getMultiSelect) {
            triggerToolbarAction(action)
        } else {
            triggerCardAction(action)
        }
    }

    function keyAction(event: KeyboardEvent): void {
        // Don't process if hotkeys are disabled
        if (!state.value.keyActionEnabled) return

        // console.debug("Key:", event.key, ", type:", document.activeElement.type, ", class:", document.activeElement.className, ", activeElement:", document.activeElement);

        const searchField = document.getElementById('search') as HTMLInputElement | null
        // Don't process if input is focused
        if (isInputFieldFocused()) {
            if (event.key === 'Escape') {
                // Pressing Esc in the search field removes the focus
                if (searchField && document.activeElement == searchField) {
                    searchField.blur()
                    updateCardFocus()
                }
            }
            return
        }

        const keyAlias = getKeyAlias(event)
        if (!keyAlias) return

        // console.info(`[Keyboard] keyAction: ${keyAlias}`)

        // just initialize focus on first keypress, ignore for source_group keys
        if (
            !state.value.use_focus &&
            state.value.cardItems.length > 0 &&
            keyAlias !== HotkeyAction.SOURCE_GROUP_UP &&
            keyAlias !== HotkeyAction.SOURCE_GROUP_DOWN &&
            keyAlias !== HotkeyAction.OPEN_SEARCH
        ) {
            state.value.use_focus = true
            updateCardsFocus()
            scrollToCard()
            return
        }

        // Handle navigation shortcuts
        switch (keyAlias) {
            case HotkeyAction.COLLECTION_UP_1:
            case HotkeyAction.COLLECTION_UP_2:
                event.preventDefault()
                moveUp()
                break

            case HotkeyAction.COLLECTION_DOWN_1:
            case HotkeyAction.COLLECTION_DOWN_2:
                event.preventDefault()
                moveDown()
                break

            case HotkeyAction.HOME:
                event.preventDefault()
                moveToStart()
                break

            case HotkeyAction.END:
                event.preventDefault()
                moveToEnd()
                break

            case HotkeyAction.SHOW_ITEM_1:
            case HotkeyAction.SHOW_ITEM_2:
            case HotkeyAction.SHOW_ITEM_3:
                getCurrentCardElement()?.click()
                break

            case HotkeyAction.CLOSE_ITEM_1:
            case HotkeyAction.CLOSE_ITEM_2:
            case HotkeyAction.CLOSE_ITEM_3:
                if (state.value.dialogCloseCallback) {
                    state.value.dialogCloseCallback()
                }
                updateCardFocus()
                break

            case HotkeyAction.READ_ITEM:
                triggerAction(Action.READ)
                break

            case HotkeyAction.IMPORTANT_ITEM:
                triggerAction(Action.IMPORTANT)
                break

            case HotkeyAction.LIKE_ITEM:
                triggerAction(Action.LIKE)
                break

            case HotkeyAction.UNLIKE_ITEM:
                triggerAction(Action.DISLIKE)
                break

            case HotkeyAction.DELETE_ITEM:
                triggerAction(Action.DELETE)
                break

            case HotkeyAction.UNGROUP:
                triggerAction(Action.UNGROUP)
                break

            case HotkeyAction.GROUP:
                triggerToolbarAction(Action.GROUP) // not exists on card, only on toolbar
                break

            case HotkeyAction.NEW_PRODUCT:
                triggerAction(Action.CREATE_REPORT)
                break

            case HotkeyAction.OPEN_ITEM_SOURCE:
                triggerCardAction(Action.OPEN) // not exists on toolbar, only on card
                break

            case HotkeyAction.SOURCE_GROUP_UP:
                groupPosition(false)
                break

            case HotkeyAction.SOURCE_GROUP_DOWN:
                groupPosition(true)
                break

            case HotkeyAction.OPEN_SEARCH:
                event.preventDefault()
                searchField?.focus()
                break

            case HotkeyAction.SELECTION: {
                const id = String(getCurrentCardElement()?.getAttribute('data-id'))
                if (!id) {
                    console.warn('[Keyboard] selection: missing card id')
                    break
                }
                if (assessStore.getMultiSelect) {
                    if (assessStore.isSelectedById(id)) {
                        if (assessStore.getNumberOfSelected() === 1) {
                            assessStore.multiSelect(false)
                        } else {
                            assessStore.deselectById(id)
                        }
                    } else {
                        assessStore.selectById(id)
                    }
                } else {
                    assessStore.multiSelect(true)
                    assessStore.selectById(id)
                }
                break
            }

            case HotkeyAction.AGGREGATE_OPEN:
                triggerCardAction(Action.AGGREGATE_OPEN) // not exists on toolbar, only on card
                break

            case HotkeyAction.RELOAD:
                if (state.value.reloadCallback) {
                    state.value.reloadCallback()
                }
                break

            default:
                break
        }
    }

    function setDetailDialogCloseCallback(callback: (() => void) | null): void {
        state.value.dialogCloseCallback = callback
    }

    function setReloadCallback(callback: (() => void) | null): void {
        state.value.reloadCallback = callback
    }

    function onInit(): void {
        state.value.keyActionEnabled = settingsStore.getSettingBoolean(Settings.HOTKEYS, false)

        // Initialize keyboard shortcuts from settings
        state.value.shortcuts = settingsStore.getProfileHotkeys || []
    }

    return {
        // State
        state: computed(() => state.value),
        pos: computed(() => state.value.pos),
        cardCount: computed(() => state.value.cardItems.length),
        currentCard: computed(() => currentCard.value),

        onInit,
        keyAction,
        setDetailDialogCloseCallback,
        setReloadCallback,
        reindexCardItems
    }
}

export default useKeyboard
