export const openInNewTabWithoutOpener = (url: string): Window | null => {
    const openedWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (openedWindow) openedWindow.opener = null
    return openedWindow
}

/**
 * Reserve a tab while a click still has transient browser user activation.
 *
 * `noopener` cannot be passed as a window feature here because browsers may
 * then deliberately return `null`, leaving us unable to navigate the reserved
 * tab after an asynchronous preview request. Clear the opener synchronously
 * instead, before any application code yields back to the browser.
 */
export const openBlankTabWithoutOpener = (): Window | null => {
    const openedWindow = window.open('about:blank', '_blank')
    if (openedWindow) openedWindow.opener = null
    return openedWindow
}

export const navigateReservedTabOrCurrentWindow = (openedWindow: Window | null, url: string): void => {
    if (openedWindow && !openedWindow.closed) {
        openedWindow.location.href = url
        return
    }

    window.location.assign(url)
}
