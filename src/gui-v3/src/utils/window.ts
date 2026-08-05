export const openInNewTabWithoutOpener = (url: string): Window | null => {
    const openedWindow = window.open(url, '_blank', 'noopener,noreferrer')
    if (openedWindow) openedWindow.opener = null
    return openedWindow
}
