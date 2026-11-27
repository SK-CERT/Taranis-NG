import axios from 'axios'

/** Translation keys for the two failures an entity can word in its own terms. */
export type DeleteErrorLocs = {
    /** Core answered 409: other records still reference the one being deleted. */
    inUse?: string
    /** Any other refusal or server error. */
    failed?: string
}

// What a proxy answers in core's place while it is down or restarting.
const PROXY_STATUSES = new Set([502, 503, 504])

/**
 * True when core never answered: a network or TLS failure, a timeout, or the proxy in front
 * of a core that is down. A plain Error is a bug on this side and does not count.
 */
export function isServerUnreachable(error: unknown): boolean {
    const status = (error as { response?: { status?: number } } | null)?.response?.status
    if (status === undefined) return axios.isAxiosError(error)
    return PROXY_STATUSES.has(status)
}

/**
 * The message to show for a failed delete.
 *
 * Saying "in use" for every failure (SK-CERT#527) told the user to go and detach records
 * when the server had simply not been reached. Core answers 409 only for a row that is still
 * referenced, so that is the one case worded as "in use".
 */
export function deleteErrorLoc(error: unknown, { inUse = 'error.in_use', failed = 'common.error_deleting' }: DeleteErrorLocs = {}): string {
    if (isServerUnreachable(error)) return 'error.server_unreachable'
    if ((error as { response?: { status?: number } } | null)?.response?.status === 409) return inUse
    return failed
}

/**
 * Core's own explanation of a 409, where it gives one in words: a CVD Report whose GCVE or CVE
 * record is published, or whose CVE ID is still reserved, answers with what to do instead (a
 * plain string). The generic "still in use" answer is an object, and keeps its translated wording.
 */
export function conflictExplanation(error: unknown): string {
    const response = (error as { response?: { status?: number; data?: unknown } } | null)?.response
    return response?.status === 409 && typeof response.data === 'string' ? response.data.trim() : ''
}

/**
 * Show the message for a failed delete in the notification snackbar. With ``explainConflict``,
 * a 409 that core explains is shown in its words.
 */
export function notifyDeleteError(error: unknown, locs?: DeleteErrorLocs, explainConflict = false): void {
    const explanation = explainConflict ? conflictExplanation(error) : ''
    const detail = explanation ? { type: 'error', message: explanation } : { type: 'error', loc: deleteErrorLoc(error, locs) }
    window.dispatchEvent(new CustomEvent('notification', { detail }))
}
