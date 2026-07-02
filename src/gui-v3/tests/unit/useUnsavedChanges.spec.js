import { describe, it, expect, vi } from 'vitest'
import { useUnsavedChanges } from '@/composables/useUnsavedChanges'

/**
 * Build a guard over a small mutable form state. `state` is returned so tests can
 * mutate it and observe the dirty-tracking behaviour.
 */
function setup(overrides = {}) {
    const state = { name: 'initial' }
    const close = vi.fn()
    const save = 'save' in overrides ? overrides.save : vi.fn().mockResolvedValue(true)
    const guard = useUnsavedChanges({
        getState: () => ({ ...state }),
        save,
        close
    })
    return { state, close, save, guard }
}

describe('useUnsavedChanges', () => {
    // ── Dirty tracking ────────────────────────────
    describe('isDirty', () => {
        it('is not dirty before a baseline is captured', () => {
            const { guard } = setup()
            expect(guard.isDirty()).toBe(false)
        })

        it('is not dirty when the state is unchanged since capture', () => {
            const { guard } = setup()
            guard.capture()
            expect(guard.isDirty()).toBe(false)
        })

        it('is dirty when the state changed after capture', () => {
            const { guard, state } = setup()
            guard.capture()
            state.name = 'edited'
            expect(guard.isDirty()).toBe(true)
        })

        it('re-captures a new clean baseline (e.g. after reopening)', () => {
            const { guard, state } = setup()
            guard.capture()
            state.name = 'edited'
            guard.capture()
            expect(guard.isDirty()).toBe(false)
        })
    })

    // ── requestClose ──────────────────────────────
    describe('requestClose', () => {
        it('closes immediately when there are no unsaved changes', () => {
            const { guard, close } = setup()
            guard.capture()
            guard.requestClose()
            expect(close).toHaveBeenCalledTimes(1)
            expect(guard.confirmVisible.value).toBe(false)
        })

        it('opens the confirmation prompt when there are unsaved changes', () => {
            const { guard, close, state } = setup()
            guard.capture()
            state.name = 'edited'
            guard.requestClose()
            expect(close).not.toHaveBeenCalled()
            expect(guard.confirmVisible.value).toBe(true)
        })
    })

    // ── Prompt actions ────────────────────────────
    describe('prompt actions', () => {
        it('continueEditing hides the prompt without closing', () => {
            const { guard, close } = setup()
            guard.confirmVisible.value = true
            guard.continueEditing()
            expect(guard.confirmVisible.value).toBe(false)
            expect(close).not.toHaveBeenCalled()
        })

        it('discardAndClose hides the prompt and closes', () => {
            const { guard, close } = setup()
            guard.confirmVisible.value = true
            guard.discardAndClose()
            expect(guard.confirmVisible.value).toBe(false)
            expect(close).toHaveBeenCalledTimes(1)
        })

        it('saveAndClose persists then closes on success', async () => {
            const { guard, save, close } = setup()
            guard.confirmVisible.value = true
            await guard.saveAndClose()
            expect(save).toHaveBeenCalledTimes(1)
            expect(close).toHaveBeenCalledTimes(1)
            expect(guard.confirmVisible.value).toBe(false)
        })

        it('saveAndClose keeps the dialog open when the save fails', async () => {
            const save = vi.fn().mockResolvedValue(false)
            const { guard, close } = setup({ save })
            await guard.saveAndClose()
            expect(save).toHaveBeenCalledTimes(1)
            expect(close).not.toHaveBeenCalled()
        })

        it('saveAndClose hides the prompt before saving (so validation errors are visible)', async () => {
            // A save that inspects confirmVisible at call time must see it already hidden.
            let visibleDuringSave = null
            const save = vi.fn().mockImplementation(() => {
                visibleDuringSave = guard.confirmVisible.value
                return false
            })
            const { guard } = setup({ save })
            guard.confirmVisible.value = true
            await guard.saveAndClose()
            expect(visibleDuringSave).toBe(false)
        })
    })

    // ── Optional save ─────────────────────────────
    describe('without a save callback', () => {
        it('saveAndClose is a no-op and does not throw or close', async () => {
            const { guard, close } = setup({ save: undefined })
            await expect(guard.saveAndClose()).resolves.toBeUndefined()
            expect(close).not.toHaveBeenCalled()
        })
    })
})
