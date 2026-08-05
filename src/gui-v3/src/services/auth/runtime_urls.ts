const GUI_BASE_PATH = '/v2/'
const RUNTIME_PLACEHOLDER = /\$\{?VITE_APP_[A-Z0-9_]+\}?/i

export const getExternalAuthUrl = (value: unknown): string | null => {
    if (typeof value !== 'string') return null

    const configured = value.trim()
    if (!configured || configured.startsWith('$') || RUNTIME_PLACEHOLDER.test(configured)) return null

    try {
        const url = new URL(configured, window.location.origin)
        if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
        return configured
    } catch {
        return null
    }
}

export const getExternalAuthCallbackUrl = (): string => new URL(`${GUI_BASE_PATH}login`, window.location.origin).toString()

export const resolveExternalAuthUrl = (configured: string, callbackUrl = getExternalAuthCallbackUrl()): string =>
    configured.replaceAll('TARANIS_GUI_URI', encodeURIComponent(callbackUrl))
