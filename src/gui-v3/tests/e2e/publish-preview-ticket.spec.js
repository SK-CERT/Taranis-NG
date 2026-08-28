import { test, expect } from '@playwright/test'
import { createApiContext } from '../helpers/api-seed'

/**
 * Product preview tickets and the CSP the preview is served under.
 *
 * The preview endpoint mints a uuid4 ticket in Redis and serves the rendered
 * report from a GET with no re-authentication. Two properties matter and neither
 * can be checked without a real backend:
 *
 *  - the ticket is single use, so a URL that leaks (proxy logs, browser history,
 *    a shared link) cannot serve the report again. The code claimed this in a
 *    comment long before it did it.
 *  - an HTML preview must be able to run the inline script its own template
 *    ships (template_osint.html inlines Chart.js), while still being denied
 *    everything it does not need.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

async function mintTicket(request, token) {
    // product types are a config resource, not a publish one
    const types = await request.get(`${CORE_API}/config/product-types`, {
        headers: { Authorization: `Bearer ${token}` }
    })
    if (!types.ok()) return null
    const body = await types.json()
    const productType = (body.items || []).find(Boolean)
    if (!productType) return null

    const response = await request.post(`${CORE_API}/publish/products/preview-ticket`, {
        data: { jwt: token, product: { product_type_id: productType.id, title: 'E2E preview', description: 'E2E' } }
    })
    if (!response.ok()) return null
    return (await response.json()).token
}

test.describe('Product preview ticket', () => {
    let request
    let token

    test.beforeAll(async ({ playwright }) => {
        ;({ request, token } = await createApiContext(playwright))
    })

    test.afterAll(async () => {
        await request?.dispose()
    })

    test('a preview ticket may be redeemed exactly once', async () => {
        const ticket = await mintTicket(request, token)
        test.skip(!ticket, 'no product type available to preview in this environment')

        const first = await request.get(`${CORE_API}/publish/products/preview/${ticket}`)
        expect(first.status(), 'the first redemption serves the report').toBe(200)

        // Before the fix this returned the report again, for an hour.
        const second = await request.get(`${CORE_API}/publish/products/preview/${ticket}`)
        expect(second.status(), 'a redeemed ticket must be spent').toBe(404)
    })

    test('an unknown ticket is not found', async () => {
        const response = await request.get(`${CORE_API}/publish/products/preview/00000000-0000-0000-0000-000000000000`)
        expect(response.status()).toBe(404)
    })

    test('the preview CSP matches what the rendered format needs', async () => {
        const ticket = await mintTicket(request, token)
        test.skip(!ticket, 'no product type available to preview in this environment')

        const response = await request.get(`${CORE_API}/publish/products/preview/${ticket}`)
        expect(response.status()).toBe(200)

        const contentType = response.headers()['content-type'] || ''
        const csp = response.headers()['content-security-policy']

        // Whatever the format, the non-CSP hardening always applies.
        expect(response.headers()['x-content-type-options']).toBe('nosniff')

        if (contentType.includes('text/html')) {
            // template_osint.html builds its charts from an inlined Chart.js; a
            // policy without script-src would ship the report with no charts.
            expect(csp).toContain("script-src 'unsafe-inline'")
            expect(csp).toContain("default-src 'none'") // still no network loads
            expect(csp).toContain("frame-ancestors 'none'")
        } else {
            // A PDF (or any non-HTML preview) goes to the browser's built-in
            // viewer. `default-src 'none'` also zeroes object-src, which has
            // historically stopped those viewers rendering, so these carry no
            // CSP at all rather than one that might silently blank the page.
            expect(csp, `${contentType} preview must not carry a CSP`).toBeUndefined()
        }
    })
})
