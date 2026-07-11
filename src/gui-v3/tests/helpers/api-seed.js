/**
 * API-based seed helpers for E2E tests.
 *
 * Creates throwaway news-items, report-items, and products for the badge/
 * confirmation-dialog E2E specs. Each creator returns the created entity's
 * ID so the test can clean it up via the matching deleter. All helpers are
 * best-effort and must tolerate a missing backend.
 */

const CORE_API = process.env.E2E_CORE_API || 'http://127.0.0.1:8082/api/v1'

async function getToken(request, username = 'admin', password = 'admin') {
    // Poll until the backend is reachable — the E2E webServer may have just
    // rebuilt the Docker core image, and the backend can take a while to warm up.
    const maxAttempts = 60
    for (let i = 0; i < maxAttempts; i++) {
        try {
            const res = await request.post(`${CORE_API}/auth/login`, { data: { username, password } })
            if (res.ok()) {
                const body = await res.json()
                return body.access_token
            }
        } catch {
            // backend not yet reachable — keep polling
        }
        await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    throw new Error(`E2E seed: backend not reachable at ${CORE_API} after ${maxAttempts} attempts`)
}

/**
 * Create a standalone authenticated API request context.
 * @param {import('@playwright/test').Playwright} playwright
 * @returns {Promise<{ request: import('@playwright/test').APIRequestContext, token: string }>}
 */
export async function createApiContext(playwright) {
    const request = await playwright.request.newContext()
    const token = await getToken(request)
    return { request, token }
}

function authHeaders(token) {
    return { Authorization: `Bearer ${token}` }
}

/**
 * Fetch the first OSINT source ID that belongs to a group.
 * Needed because createNewsItem requires a valid osint_source_id for the
 * aggregate to be assigned to an OSINT source group (otherwise it never
 * appears in the Assess view).
 */
export async function getFirstOSINTSourceId(request, token) {
    try {
        const res = await request.get(`${CORE_API}/collectors/osint-source-groups?search=`, { headers: authHeaders(token) })
        if (!res.ok()) return null
        const body = await res.json()
        const groups = body?.items || body?.data?.items || []
        for (const group of groups) {
            const sources = group.osint_sources || []
            if (sources.length > 0) {
                const first = sources[0]
                return first.id || first
            }
        }
        return null
    } catch {
        return null
    }
}

/**
 * Create a manual news item aggregate via the Assess API.
 * @returns {Promise<{ aggregateId: number | null }>} the created aggregate ID (or null on failure)
 */
export async function createNewsItem(request, token, { title, description = 'E2E test item', osintSourceId }) {
    try {
        // The AddNewsItem endpoint expects a NewsItemData-shaped payload.
        const time = new Date().toISOString()
        const res = await request.post(`${CORE_API}/assess/news-items`, {
            headers: authHeaders(token),
            data: {
                title,
                review: description,
                source: 'E2E',
                link: '',
                published: time,
                author: 'E2E',
                collected: time,
                content: description,
                osint_source_id: osintSourceId || null
            }
        })
        if (!res.ok()) return { aggregateId: null }
        // The endpoint returns no body; fetch the aggregate by searching.
        const groupsRes = await request.get(`${CORE_API}/assess/news-item-aggregates-by-group/all`, {
            headers: authHeaders(token),
            params: { offset: 0, limit: 50, sort: 'DATE_DESC', search: title }
        })
        if (!groupsRes.ok()) return { aggregateId: null }
        const body = await groupsRes.json()
        const items = body?.items || body?.data?.items || []
        const match = items.find((it) => it.title === title)
        return { aggregateId: match ? match.id : null }
    } catch {
        return { aggregateId: null }
    }
}

/**
 * Look up a news-item aggregate ID by its title (after GUI-based creation).
 * @returns {Promise<number | null>} the aggregate ID, or null if not found
 */
export async function findAggregateIdByTitle(request, token, title) {
    try {
        const groupsRes = await request.get(`${CORE_API}/assess/news-item-aggregates-by-group/all`, {
            headers: authHeaders(token),
            params: { offset: 0, limit: 50, sort: 'DATE_DESC', search: title }
        })
        if (!groupsRes.ok()) return null
        const body = await groupsRes.json()
        const items = body?.items || body?.data?.items || []
        const match = items.find((it) => it.title === title)
        return match ? match.id : null
    } catch {
        return null
    }
}

/**
 * Fetch the first report-item-type ID (needed to create report items).
 */
export async function getFirstReportItemTypeId(request, token) {
    try {
        const res = await request.get(`${CORE_API}/analyze/report-item-types`, { headers: authHeaders(token) })
        if (!res.ok()) return null
        const body = await res.json()
        const item = (body?.items || [])[0]
        return item ? item.id : null
    } catch {
        return null
    }
}

/**
 * Fetch the COMPLETED state definition ID for report_items.
 */
export async function getCompletedStateId(request, token) {
    try {
        const res = await request.get(`${CORE_API}/state/entity-types/report_item/states`, { headers: authHeaders(token) })
        if (!res.ok()) return null
        const body = await res.json()
        const states = body?.states || []
        // Prefer a FINAL state; fall back to one named "completed".
        const final = states.find((s) => s.state_type === 'final')
        if (final) return final.id
        const completed = states.find((s) => s.display_name?.toLowerCase() === 'completed')
        return completed ? completed.id : null
    } catch {
        return null
    }
}

/**
 * Fetch the initial/default state definition ID for report_items.
 */
export async function getInitialStateId(request, token) {
    try {
        const res = await request.get(`${CORE_API}/state/entity-types/report_item/states`, { headers: authHeaders(token) })
        if (!res.ok()) return null
        const body = await res.json()
        const states = body?.states || []
        const initial = states.find((s) => s.state_type === 'initial')
        if (initial) return initial.id
        const wip = states.find((s) => s.display_name?.toLowerCase() === 'work_in_progress')
        return wip ? wip.id : null
    } catch {
        return null
    }
}

/**
 * Create a report item linked to a news-item aggregate.
 * @param {object} opts
 * @param {number} opts.aggregateId - news-item aggregate ID to attach
 * @param {string} opts.title - report item title
 * @param {number} opts.reportItemTypeId - report-item-type ID
 * @param {number|null} [opts.stateId] - state ID (null = default/initial)
 * @returns {Promise<number|null>} the created report-item ID
 */
export async function createReportItem(request, token, { aggregateId, title, reportItemTypeId, stateId = null }) {
    try {
        const payload = {
            title,
            title_prefix: '',
            report_item_type_id: reportItemTypeId,
            news_item_aggregates: aggregateId ? [aggregateId] : [],
            attributes: []
        }
        if (stateId !== null) {
            payload.state_id = stateId
        }
        const res = await request.post(`${CORE_API}/analyze/report-items`, {
            headers: authHeaders(token),
            data: payload
        })
        if (!res.ok()) return null
        const id = await res.json()
        return typeof id === 'number' ? id : null
    } catch {
        return null
    }
}

/**
 * Update a report item's state.
 */
export async function updateReportItemState(request, token, reportItemId, stateId) {
    try {
        await request.put(`${CORE_API}/analyze/report-items/${reportItemId}`, {
            headers: authHeaders(token),
            data: { update: true, state_id: stateId }
        })
    } catch {
        // best-effort
    }
}

/**
 * Delete a report item.
 */
export async function deleteReportItem(request, token, reportItemId) {
    try {
        await request.delete(`${CORE_API}/analyze/report-items/${reportItemId}`, { headers: authHeaders(token) })
    } catch {
        // best-effort
    }
}

/**
 * Delete a news-item aggregate.
 */
export async function deleteNewsItemAggregate(request, token, aggregateId) {
    try {
        await request.delete(`${CORE_API}/assess/news-item-aggregates/${aggregateId}`, { headers: authHeaders(token) })
    } catch {
        // best-effort
    }
}

/**
 * Delete a product type.
 */
export async function deleteProductType(request, token, productTypeId) {
    try {
        await request.delete(`${CORE_API}/config/product-types/${productTypeId}`, { headers: authHeaders(token) })
    } catch {
        // best-effort
    }
}

/**
 * Delete a publisher preset.
 */
export async function deletePublisherPreset(request, token, presetId) {
    try {
        await request.delete(`${CORE_API}/config/publishers-presets/${presetId}`, { headers: authHeaders(token) })
    } catch {
        // best-effort
    }
}

/**
 * Best-effort cleanup: deletes the given report-item IDs then news-item-aggregate IDs.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} token
 * @param {{ reportItemIds: number[], aggregateIds: number[] }} ids
 */
export async function cleanupSeedData(request, token, { reportItemIds = [], aggregateIds = [] }) {
    for (const id of reportItemIds) {
        await deleteReportItem(request, token, id)
    }
    for (const id of aggregateIds) {
        await deleteNewsItemAggregate(request, token, id)
    }
}
