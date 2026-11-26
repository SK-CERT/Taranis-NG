import { ref, watch, type Ref } from 'vue'

/**
 * Removing a stored credential from a module parameter (source, bot preset, product format,
 * publishing channel).
 *
 * Core never sends a stored secret back, and saving the field empty keeps it, so an empty field
 * cannot mean "remove it". The dialog's remove button marks the parameter instead, and the save
 * sends `clear_stored: true` for it (core managers/stored_secrets.py keep_secret_parameter).
 * A value typed into the field still replaces the stored one.
 */
export function useStoredSecretRemoval(storedSecrets: Ref<Set<string>>) {
    const removed = ref<Set<string>>(new Set())

    // Another record (or the same one reloaded) starts with nothing marked.
    watch(storedSecrets, () => {
        removed.value = new Set()
    })

    const isRemoved = (key: unknown): boolean => removed.value.has(String(key))

    /** Mark the stored value for removal, or keep it after all; returns whether it is now marked. */
    const toggleRemoved = (key: unknown): boolean => {
        const next = new Set(removed.value)
        const name = String(key)
        if (next.has(name)) next.delete(name)
        else next.add(name)
        removed.value = next
        return next.has(name)
    }

    /** What a save sends besides the value: the remove request, only when nothing replaces the stored value. */
    const removalFlag = (key: unknown, value: string): { clear_stored?: true } =>
        isRemoved(key) && !value.trim() ? { clear_stored: true } : {}

    return { removed, isRemoved, toggleRemoved, removalFlag }
}
