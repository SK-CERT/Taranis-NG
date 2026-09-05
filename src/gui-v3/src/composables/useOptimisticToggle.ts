import { ref, type Ref } from 'vue'

type Toggleable = { id: string | number; enabled?: boolean }

type ToggleOptions = {
    /** Persist the new value. Rejecting rolls the switch back. */
    save: (enabled: boolean) => Promise<unknown>
    /** Re-read the list once the save lands, so the row shows what the server actually stored. */
    reload: () => Promise<unknown>
    /** Report the failure, after the roll-back has already happened. */
    onError?: (error: unknown) => void
}

/**
 * Flip an on/off switch on a row before the server has agreed to it.
 *
 * A switch that waits for a round-trip feels broken, so the row is flipped at once and put back
 * if the save fails. The id of the row being saved is exposed so its switch can show that it is
 * busy - without it, a second click during the round-trip would race the first.
 *
 * Public webs and OSINT sources had a copy of this each, identical but for which endpoint they
 * called and how loudly they complained.
 */
export function useOptimisticToggle(): {
    busyId: Ref<string | number | null>
    toggle: (item: Toggleable, desired: boolean, options: ToggleOptions) => Promise<void>
} {
    const busyId = ref<string | number | null>(null)

    const toggle = async (item: Toggleable, desired: boolean, options: ToggleOptions): Promise<void> => {
        const previous = item.enabled !== false
        if (desired === previous) return

        item.enabled = desired
        busyId.value = item.id
        try {
            await options.save(desired)
            await options.reload()
        } catch (error) {
            item.enabled = previous
            options.onError?.(error)
        } finally {
            busyId.value = null
        }
    }

    return { busyId, toggle }
}
