/**
 * API-based cleanup helpers for E2E tests.
 *
 * The workflow lifecycle tests create real state definitions and state-entity-type
 * associations. Cleaning them up through the UI is unreliable — a failed/timed-out
 * test tears the page down before its cleanup runs, so junk accumulates and eventually
 * breaks later runs (pagination, name collisions, slow lists).
 *
 * These helpers talk to the core API directly, so cleanup works regardless of the page
 * state. They are best-effort: callers should tolerate failures (e.g. backend not up)
 * rather than failing the suite on cleanup.
 */

// The core API base. Defaults to the backend the Playwright webServer boots; override
// with E2E_CORE_API if your setup differs.
const CORE_API = process.env.E2E_CORE_API || 'http://127.0.0.1:8082/api/v1'

async function getToken(request, username = 'admin', password = 'admin') {
    const res = await request.post(`${CORE_API}/auth/login`, { data: { username, password } })
    if (!res.ok()) {
        throw new Error(`E2E cleanup login failed: ${res.status()} ${res.statusText()}`)
    }
    const body = await res.json()
    return body.access_token
}

/**
 * Create a standalone API request context authenticated as admin.
 * Usable from beforeAll/afterEach (no page required). Dispose it when done.
 * @param {import('@playwright/test').Playwright} playwright
 * @returns {Promise<{ request: import('@playwright/test').APIRequestContext, token: string }>}
 */
export async function createApiContext(playwright) {
    const request = await playwright.request.newContext()
    const token = await getToken(request)
    return { request, token }
}

/**
 * Delete every state-entity-type association referencing a matching state definition,
 * then delete those state definitions. Associations are removed first to respect the
 * state -> association foreign key.
 *
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} token - Bearer token
 * @param {(displayName: string) => boolean} matches - selects which states to purge by display name
 */
export async function purgeStates(request, token, matches) {
    const headers = { Authorization: `Bearer ${token}` }

    const statesRes = await request.get(`${CORE_API}/config/state-definitions?search=E2E`, { headers })
    const states = statesRes.ok() ? (await statesRes.json()).items || [] : []
    const targets = states.filter((s) => matches(String(s.display_name ?? '')))
    const targetIds = new Set(targets.map((s) => s.id))

    const assocRes = await request.get(`${CORE_API}/config/state-entity-types`, { headers })
    const assocs = assocRes.ok() ? (await assocRes.json()).items || [] : []
    for (const a of assocs) {
        if (targetIds.has(a.state_id) || matches(String(a.state?.display_name ?? ''))) {
            await request.delete(`${CORE_API}/config/state-entity-types/${a.id}`, { headers })
        }
    }

    for (const s of targets) {
        await request.delete(`${CORE_API}/config/state-definitions/${s.id}`, { headers })
    }
}

/**
 * Best-effort purge: creates a context, purges matching states, disposes. Never throws —
 * cleanup problems (e.g. backend unavailable) are logged, not fatal to the test run.
 * @param {import('@playwright/test').Playwright} playwright
 * @param {(displayName: string) => boolean} matches
 */
export async function purgeStatesBestEffort(playwright, matches) {
    let request
    try {
        const ctx = await createApiContext(playwright)
        request = ctx.request
        await purgeStates(request, ctx.token, matches)
    } catch (error) {
        console.warn('E2E state cleanup skipped:', error.message)
    } finally {
        await request?.dispose()
    }
}
