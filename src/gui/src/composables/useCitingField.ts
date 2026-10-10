import { nextTick } from 'vue'
import { useLinkReferences } from '@/composables/useLinkReferences'
import { insertAtCaret, linkToken } from '@/utils/linkReferences'

type CitingValue = { value?: unknown; [key: string]: unknown }

type FieldElement = HTMLInputElement | HTMLTextAreaElement

/**
 * Citing links from the text inputs of an attribute: remembers where the caret was in each
 * value's input, and inserts a citation token there.
 *
 * @param values The attribute's values.
 * @param save Persists the value at an index (useAttributes' onEdit; a no-op while creating).
 */
export function useCitingField(values: () => CitingValue[], save: (index: number) => Promise<void>) {
    const references = useLinkReferences()
    const fields = new Map<number, FieldElement>()
    const selections = new Map<number, { start: number | null; end: number | null }>()

    /** Template ref callback for the Vuetify field of value `index`. */
    const setField = (index: number, component: unknown): void => {
        const root = (component as { $el?: Element } | null)?.$el
        const element = root?.querySelector?.('textarea, input') as FieldElement | null | undefined
        if (element) {
            fields.set(index, element)
        } else {
            fields.delete(index)
        }
    }

    /** Remember the caret of value `index` (on keyup, click and blur). */
    const trackSelection = (index: number): void => {
        const element = fields.get(index)
        if (element) {
            selections.set(index, { start: element.selectionStart, end: element.selectionEnd })
        }
    }

    /** Insert a citation of `key` where the caret was, save, and put the caret after it. */
    const cite = async (index: number, key: string): Promise<void> => {
        const value = values()[index]
        if (!value) {
            return
        }
        const selection = selections.get(index)
        const { text, caret } = insertAtCaret(
            typeof value.value === 'string' ? value.value : '',
            linkToken(key),
            selection?.start,
            selection?.end
        )
        value.value = text
        selections.set(index, { start: caret, end: caret })
        await save(index)

        await nextTick()
        const element = fields.get(index)
        if (element && !element.disabled) {
            element.focus()
            element.setSelectionRange(caret, caret)
        }
    }

    return { references, setField, trackSelection, cite }
}
