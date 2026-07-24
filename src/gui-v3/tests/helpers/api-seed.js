/**
 * API-based seed helpers for E2E tests.
 *
 * Creates throwaway news-items, report-items, and products for the badge/
 * confirmation-dialog E2E specs. Each creator returns the created entity's
 * ID so the test can clean it up via the matching deleter. All helpers are
 * best-effort and must tolerate a missing backend.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

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
        // First try /config/osint-source-groups — the admin path. /collectors/osint-source-groups
        // is an EXTERNAL-API endpoint (Collector API key auth, not JWT) that returns 401 here.
        const groupsRes = await request.get(`${CORE_API}/config/osint-source-groups?search=`, { headers: authHeaders(token) })
        if (groupsRes.ok()) {
            const groupsBody = await groupsRes.json()
            const groups = groupsBody?.items || []
            for (const group of groups) {
                const sources = group.osint_sources || []
                if (sources.length > 0) {
                    const first = sources[0]
                    return first.id || first
                }
            }
        }

        // Fall back to /config/osint-sources (a flat list) — used when no sources have been
        // assigned to a group yet (the seed test creates a manual source that may not be
        // associated with any group initially).
        const sourcesRes = await request.get(`${CORE_API}/config/osint-sources?search=`, { headers: authHeaders(token) })
        if (sourcesRes.ok()) {
            const sourcesBody = await sourcesRes.json()
            const sources = sourcesBody?.items || []
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
        // The AddNewsItem endpoint expects a NewsItemData-shaped payload with
        // `collected`/`published` in the format "%d.%m.%Y - %H:%M" — see
        // `shared/schema/news_item.py:NewsItemDataBaseSchema.collected`. ISO 8601 strings
        // (`new Date().toISOString()`) are REJECTED with ValidationError
        // {'collected': ['Not a valid datetime.']} and the POST returns 500 — silently
        // failing this helper and returning aggregateId: null, which in turn makes the
        // downstream createReportItem link to NO aggregate. Format the timestamp locally.
        const formatTaranisTimestamp = (d) => {
            const pad = (n) => String(n).padStart(2, '0')
            return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} - ${pad(d.getHours())}:${pad(d.getMinutes())}`
        }
        const time = formatTaranisTimestamp(new Date())

        const res = await request.post(`${CORE_API}/assess/news-items`, {
            headers: authHeaders(token),
            data: {
                hash: '',
                title,
                review: description,
                source: 'E2E',
                link: '',
                published: time,
                author: 'E2E',
                collected: time,
                content: description,
                osint_source_id: osintSourceId || null,
                attributes: []
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
        // The backend's NewReportItemSchema → ReportItem(**data) requires `uuid` and `state_id`
        // as positional args of ReportItem.__init__ (they're generated server-side when empty,
        // but must be PRESENT in the payload — like the NodeDialog's required `id: ''`).
        // Omitting uuid/state_id → TypeError: __init__() missing 2 required positional arguments.
        //
        // `news_item_aggregates` is `fields.Nested(NewsItemAggregateIdSchema, many=True)` — i.e.
        // a list of OBJECTS each having an `id` (integer) field, NOT a list of bare IDs. Sending
        // `[aggregateId]` (a list of ints/strings) is rejected with
        // "news_item_aggregates: {0: {'_schema': ['Invalid input type.']}}". Send
        // `[{ id: aggregateId }]` instead so the nested schema deserializes each entry to an id.
        const payload = {
            uuid: '',
            title,
            title_prefix: '',
            report_item_type_id: reportItemTypeId,
            state_id: stateId ?? '',
            news_item_aggregates: aggregateId ? [{ id: aggregateId }] : [],
            attributes: []
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

// ─── Idempotent seed-entity helpers ─────────────────────────────────────────
// The 00-config-seed spec creates nodes / product types / presets with FIXED names
// (e.g. "E2E Presenters Node") on UNIQUE columns. If the E2E environment is reused
// across runs (Playwright's reuseExistingServer keeps test-setup.py from re-running,
// and `down -v` doesn't fire on every click in the VS Code runner), a previous run's
// entity lingers and the next add trips a UniqueViolation → HTTP 500 → the misleading
// "Could not connect to X node." Vue alert. These helpers delete any pre-existing
// entity whose name matches a predicate BEFORE the seed test runs, making the spec
// idempotent regardless of whether the DB was wiped.

/**
 * Delete every node of a given kind (collectors/presenters/publishers) whose `name`
 * matches the predicate. Best-effort: missing backend / 404s are swallowed.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} token
 * @param {'collectors-nodes' | 'presenters-nodes' | 'publishers-nodes'} endpoint
 * @param {(name: string) => boolean} matches
 */
export async function deleteNodesByName(request, token, endpoint, matches) {
    const headers = authHeaders(token)
    try {
        const res = await request.get(`${CORE_API}/config/${endpoint}?search=`, { headers })
        if (!res.ok()) return
        const body = await res.json()
        const items = body?.items || []
        for (const node of items) {
            const name = String(node.name ?? '')
            if (matches(name)) {
                await request.delete(`${CORE_API}/config/${endpoint}/${node.id}`, { headers })
            }
        }
    } catch {
        // Best-effort: a missing/unreachable backend during cleanup must not fail the test.
    }
}

/**
 * Delete every OSINT source whose `name` matches the predicate. Best-effort.
 * The seed test (00-config-seed.spec.js:4) creates a manual source via the
 * GUI with a timestamped name (`E2E Manual Source_<ts>`); left over they
 * accumulate across runs and answer "first manual source" wrong in tests
 * that depend on just ONE existing.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} token
 * @param {(name: string) => boolean} matches
 */
export async function deleteOSINTSourcesByName(request, token, matches) {
    const headers = authHeaders(token)
    try {
        const res = await request.get(`${CORE_API}/config/osint-sources?search=`, { headers })
        if (!res.ok()) return
        const body = await res.json()
        const items = body?.items || []
        for (const source of items) {
            const name = String(source.name ?? '')
            if (matches(name)) {
                await request.delete(`${CORE_API}/config/osint-sources/${source.id}`, { headers })
            }
        }
    } catch {
        // Best-effort.
    }
}

/**
 * Delete every product (from /publish/products) whose `title` matches the predicate.
 * Best-effort: a missing backend or 404 is swallowed. Used by the purge step BEFORE
 * product-types are deleted — ProductType.delete raises a ForeignKeyViolation
 * ("product_product_type_id_fkey") when Products still reference the ProductType, and
 * once that happens the SQLAlchemy session enters a PendingRollback state where ALL
 * subsequent DELETEs in the same worker fail.
 * @param {import('@playwright/test').APIRequestContext} request
 * @param {string} token
 * @param {(title: string) => boolean} matches
 */
export async function deleteProductsByName(request, token, matches) {
    const headers = authHeaders(token)
    try {
        const res = await request.get(`${CORE_API}/publish/products?search=`, { headers })
        if (!res.ok()) return
        const body = await res.json()
        const items = body?.items || []
        for (const product of items) {
            const title = String(product.title ?? '')
            if (matches(title)) {
                await request.delete(`${CORE_API}/publish/products/${product.id}`, { headers })
            }
        }
    } catch {
        // Best-effort.
    }
}

/**
 * Delete every product type whose `name` matches the predicate. Best-effort.
 */
export async function deleteProductTypesByName(request, token, matches) {
    const headers = authHeaders(token)
    try {
        const res = await request.get(`${CORE_API}/config/product-types?search=`, { headers })
        if (!res.ok()) return
        const body = await res.json()
        const items = body?.items || []
        for (const pt of items) {
            const name = String(pt.name ?? pt.title ?? '')
            if (matches(name)) {
                await request.delete(`${CORE_API}/config/product-types/${pt.id}`, { headers })
            }
        }
    } catch {
        // Best-effort.
    }
}

/**
 * Delete every publisher preset whose `name` matches the predicate. Best-effort.
 */
export async function deletePublisherPresetsByName(request, token, matches) {
    const headers = authHeaders(token)
    try {
        const res = await request.get(`${CORE_API}/config/publishers-presets?search=`, { headers })
        if (!res.ok()) return
        const body = await res.json()
        const items = body?.items || []
        for (const preset of items) {
            const name = String(preset.name ?? '')
            if (matches(name)) {
                await request.delete(`${CORE_API}/config/publishers-presets/${preset.id}`, { headers })
            }
        }
    } catch {
        // Best-effort.
    }
}

/**
 * Purge the fixed-name seed entities the 00-config-seed spec creates, so each run starts
 * from a clean slate regardless of whether test-setup.py re-wiped the DB. Self-contained:
 * builds its own API request context, never throws. Call from the spec's beforeEach.
 *
 * The product-type / publisher-preset / manual-source seed tests already use
 * generateTestName() (timestamped) so they can't collide with themselves across runs;
 * only the three fixed-name node-add tests need this purge, but the extra purges are
 * harmless and keep the env tidy for downstream specs on a reused stack.
 * @param {import('@playwright/test').Playwright} playwright
 */
export async function purgeSeedEntitiesBestEffort(playwright) {
    let request
    try {
        const ctx = await createApiContext(playwright)
        request = ctx.request

        // CASCADE ORDER — dependencies MUST be deleted before their parents:
        //   1. Product types reference presenters-node-presenters (the DELETE on the presenters
        //      node raises "Presenters has mapped product types" if any product type still
        //      references one of its presenters).
        //   2. Publisher presets reference publishers-nodes (same shape — DELETE on a
        //      publishers node with mapped presets returns 400 "Could not delete").
        //   3. Only AFTER both of the above are gone can the three seed nodes be deleted.
        //
        // The product-type/preset seed tests use generateTestName() (timestamped) so the
        // purge here has to match a *prefix*, not a fixed name. The three node-add tests use
        // fixed names so they are matched exactly.
        const fixedNodeNames = ['E2E Presenters Node', 'E2E Publishers Node', 'E2E Collectors Node']
        const isFixedNode = (name) => fixedNodeNames.includes(name)
        const isE2EProductType = (name) => /^E2E Product Type/.test(name)
        const isE2EPublisherPreset = (name) => /^E2E Publisher Preset/.test(name)
        const isE2EProduct = (title) => /^E2E (Publish Confirm|Incomplete Reports) /.test(title) || /^E2E Publish Confirm/.test(title)
        const isE2EOSINTSource = (name) => /^E2E Manual Source/.test(name)

        // Step 1: delete E2E Products FIRST — ProductType.delete raises a ForeignKeyViolation
        // on `product_product_type_id_fkey` when Products still reference the ProductType, and
        // once that happens the SQLAlchemy session enters a PendingRollback state where ALL
        // subsequent DELETEs in the same worker silently fail (the publish-confirm test
        // creates Products via `Save and Publish`).
        // Step 2: delete ProductTypes (now that no Products reference them).
        // Step 3: delete PublisherPresets.
        // Step 4: delete E2E Manual OSINT Sources — the seed test creates them with timestamped
        // names (`generateTestName('E2E Manual Source')`); left over they bloat the env and
        // eventually trip UNIQUE-ish constraints via the `osint_sources` table.
        // Step 5: delete the three seed Nodes (now that no ProductType maps to their presenters).
        await deleteProductsByName(request, ctx.token, isE2EProduct)
        await deleteProductTypesByName(request, ctx.token, isE2EProductType)
        await deletePublisherPresetsByName(request, ctx.token, isE2EPublisherPreset)
        await deleteOSINTSourcesByName(request, ctx.token, isE2EOSINTSource)

        // Step 5: now the parent nodes should be deletable.
        await deleteNodesByName(request, ctx.token, 'presenters-nodes', isFixedNode)
        await deleteNodesByName(request, ctx.token, 'publishers-nodes', isFixedNode)
        await deleteNodesByName(request, ctx.token, 'collectors-nodes', isFixedNode)
    } catch (error) {
        console.warn('E2E seed-entity purge skipped:', error.message)
    } finally {
        await request?.dispose()
    }
}
