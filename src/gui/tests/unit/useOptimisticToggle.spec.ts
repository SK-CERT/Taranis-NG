import { describe, it, expect, vi } from 'vitest'
import { useOptimisticToggle } from '@/composables/useOptimisticToggle'

/**
 * The switch on a row flips before the server has agreed to it, because waiting for a round-trip
 * makes a switch feel broken. That trade is only safe if a refused save puts the row back, and if
 * the row is marked busy meanwhile so a second click cannot race the first.
 */

const row = (enabled = true) => ({ id: 'row-1', enabled })

describe('useOptimisticToggle', () => {
    it('flips the row before the save resolves', async () => {
        const { toggle, busyId } = useOptimisticToggle()
        const item = row(true)
        let flippedDuringSave: boolean | undefined
        let busyDuringSave: string | number | null = null

        await toggle(item, false, {
            save: async () => {
                flippedDuringSave = item.enabled
                busyDuringSave = busyId.value
            },
            reload: async () => {}
        })

        expect(flippedDuringSave).toBe(false)
        expect(busyDuringSave).toBe('row-1')
        // Released once the save lands, or a second click could never happen.
        expect(busyId.value).toBeNull()
    })

    it('puts the row back and reports when the save is refused', async () => {
        const { toggle, busyId } = useOptimisticToggle()
        const item = row(true)
        const onError = vi.fn()
        const reload = vi.fn()

        await toggle(item, false, {
            save: () => Promise.reject(new Error('refused')),
            reload,
            onError
        })

        expect(item.enabled).toBe(true)
        expect(onError).toHaveBeenCalledOnce()
        // The list is not re-read: nothing changed, and a reload would only flicker the row.
        expect(reload).not.toHaveBeenCalled()
        expect(busyId.value).toBeNull()
    })

    it('re-reads the list once the save lands, so the row shows what was stored', async () => {
        const { toggle } = useOptimisticToggle()
        const reload = vi.fn()

        await toggle(row(false), true, { save: async () => {}, reload })

        expect(reload).toHaveBeenCalledOnce()
    })

    it('does nothing when the switch is already where it is being put', async () => {
        const { toggle } = useOptimisticToggle()
        const save = vi.fn()

        await toggle(row(true), true, { save, reload: vi.fn() })

        expect(save).not.toHaveBeenCalled()
    })

    it('treats a row with no enabled field as enabled', async () => {
        // Rows arrive from two different endpoints; one of them omits the field when it is true.
        const { toggle } = useOptimisticToggle()
        const save = vi.fn()

        await toggle({ id: 'row-2' }, true, { save, reload: vi.fn() })

        expect(save).not.toHaveBeenCalled()
    })
})
