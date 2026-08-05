import { afterEach, describe, expect, it, vi } from 'vitest'
import { openInNewTabWithoutOpener } from '@/utils/window'

describe('openInNewTabWithoutOpener', () => {
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('opens a new tab with opener access disabled', () => {
        const openedWindow = { opener: window }
        const open = vi.spyOn(window, 'open').mockReturnValue(openedWindow as Window)

        expect(openInNewTabWithoutOpener('/preview/123')).toBe(openedWindow)
        expect(open).toHaveBeenCalledWith('/preview/123', '_blank', 'noopener,noreferrer')
        expect(openedWindow.opener).toBeNull()
    })

    it('handles a browser-blocked popup without throwing', () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null)

        expect(openInNewTabWithoutOpener('/preview/blocked')).toBeNull()
        expect(open).toHaveBeenCalledWith('/preview/blocked', '_blank', 'noopener,noreferrer')
    })
})
