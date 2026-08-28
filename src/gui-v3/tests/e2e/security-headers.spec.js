import { test, expect } from '@playwright/test'

/**
 * Response headers the core API attaches to every reply.
 *
 * These are cheap to add and easy to lose in a refactor, and nothing else in the
 * suite looks at them. Asserted against the real backend rather than a Flask test
 * client, because gunicorn and Traefik both sit in the path in production.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

test.describe('Core API security headers', () => {
    test('every response carries the hardening headers', async ({ request }) => {
        const response = await request.get(`${CORE_API}/isalive`)
        expect(response.ok()).toBeTruthy()

        const headers = response.headers()
        expect(headers['x-content-type-options']).toBe('nosniff')
        expect(headers['x-frame-options']).toBe('DENY')
        expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin')
        expect(headers['content-security-policy']).toBe("default-src 'none'; frame-ancestors 'none'")
    })

    test('a foreign origin gets no CORS grant', async ({ request }) => {
        // The API used to run flask-cors with supports_credentials and no origin
        // list, which reflects whatever Origin is sent — so any site a logged-in
        // analyst visited could call the API as them. Nothing may come back now.
        const response = await request.get(`${CORE_API}/isalive`, {
            headers: { Origin: 'https://evil.example' }
        })

        const headers = response.headers()
        expect(headers['access-control-allow-origin']).toBeUndefined()
        expect(headers['access-control-allow-credentials']).toBeUndefined()
    })

    test('a preflight from a foreign origin is not granted either', async ({ request }) => {
        const response = await request.fetch(`${CORE_API}/assess/news-items`, {
            method: 'OPTIONS',
            headers: {
                'Origin': 'https://evil.example',
                'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'authorization'
            }
        })

        expect(response.headers()['access-control-allow-origin']).toBeUndefined()
    })
})
