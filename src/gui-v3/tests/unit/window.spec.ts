import { afterEach, describe, expect, it, vi } from 'vitest'
import { navigateReservedTabOrCurrentWindow, openBlankTabWithoutOpener, openInNewTabWithoutOpener } from '@/utils/window'

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

describe('reserved popup helpers', () => {
    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('reserves a blank tab and removes its opener synchronously', () => {
        const openedWindow = { opener: window }
        const open = vi.spyOn(window, 'open').mockReturnValue(openedWindow as Window)

        expect(openBlankTabWithoutOpener()).toBe(openedWindow)
        expect(open).toHaveBeenCalledWith('about:blank', '_blank')
        expect(openedWindow.opener).toBeNull()
    })

    it('navigates the reserved tab when it is available', () => {
        const openedWindow = { closed: false, location: { href: 'about:blank' } }

        navigateReservedTabOrCurrentWindow(openedWindow as Window, '/preview/123')

        expect(openedWindow.location.href).toBe('/preview/123')
    })

    it('falls back to the current window when the popup was blocked', () => {
        const assign = vi.spyOn(window.location, 'assign').mockImplementation(() => undefined)

        navigateReservedTabOrCurrentWindow(null, '/preview/blocked')

        expect(assign).toHaveBeenCalledWith('/preview/blocked')
    })
})
