import { ref } from 'vue'

/**
 * Guards an editing dialog against losing unsaved changes.
 *
 * The dialog captures a baseline snapshot of its form state when it opens
 * (`capture()`), and thereafter `requestClose()` compares the current state to
 * that baseline. If nothing changed it closes straight away; otherwise it opens
 * the shared UnsavedChangesDialog, whose three actions map to `continueEditing`,
 * `saveAndClose`, and `discardAndClose`.
 *
 * Usage:
 *   const guard = useUnsavedChanges({
 *       getState: () => localItem.value,   // whatever should count as "the form"
 *       save: persist,                     // async, returns true on success
 *       close: closeDialog
 *   })
 *   // on open:  guard.capture()
 *   // cancel/esc: guard.requestClose()
 *   // toolbar Save button: guard.saveAndClose()
 */
export function useUnsavedChanges(options: {
    /** Returns the current form state; must be JSON-serializable. */
    getState: () => unknown
    /**
     * Persists the form. Resolves to true on success, false otherwise. Optional:
     * omit it when the dialog drives "save and close" itself (e.g. a component that
     * already closes on save), and just use the cancel/discard/continue handlers.
     */
    save?: () => Promise<boolean> | boolean
    /** Closes and resets the dialog. */
    close: () => void
}) {
    const confirmVisible = ref(false)
    const baseline = ref<string | null>(null)

    const snapshot = (): string => JSON.stringify(options.getState())

    /** Record the current state as the clean baseline (call when the dialog opens). */
    const capture = (): void => {
        baseline.value = snapshot()
    }

    const isDirty = (): boolean => baseline.value !== null && snapshot() !== baseline.value

    /** Cancel/Escape entry point: prompt only when there are unsaved changes. */
    const requestClose = (): void => {
        if (isDirty()) {
            confirmVisible.value = true
        } else {
            options.close()
        }
    }

    const continueEditing = (): void => {
        confirmVisible.value = false
    }

    const saveAndClose = async (): Promise<void> => {
        // Hide the prompt first so any validation errors surfaced by save() are
        // visible on the still-open edit dialog when save fails.
        confirmVisible.value = false
        if (!options.save) {
            return
        }
        const ok = await options.save()
        if (ok) {
            options.close()
        }
    }

    const discardAndClose = (): void => {
        confirmVisible.value = false
        options.close()
    }

    return {
        confirmVisible,
        capture,
        isDirty,
        requestClose,
        continueEditing,
        saveAndClose,
        discardAndClose
    }
}
