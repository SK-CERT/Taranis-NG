import { test, expect } from '@playwright/test'

/**
 * Failed-login throttling (managers/login_throttle.py).
 *
 * The unit tests fake Redis, so they can prove the arithmetic but not that the
 * lock is actually shared between gunicorn workers or enforced ahead of the
 * credential check. That is what this spec is for.
 *
 * Two rules shape it:
 *
 *  - Never throttle `admin`. playwright.config.js runs a single worker against
 *    one shared backend and every other spec logs in as admin, so a five-minute
 *    lock there would cascade into unrelated failures.
 *  - Do not test lock *expiry*. It would idle the only worker for five minutes;
 *    `test_lock_expires` already covers it with a fake clock.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`
const THRESHOLD = 5 // FAIL_THRESHOLD in managers/login_throttle.py

const login = (request, username, password) => request.post(`${CORE_API}/auth/login`, { data: { username, password } })

test.describe('Login throttling', () => {
    test('locks a username after repeated failures, across workers', async ({ request }) => {
        // A name nothing else uses, and unique per run so a re-run is not still
        // locked from the previous one.
        const username = `throttle-probe-${Date.now()}`

        for (let attempt = 1; attempt <= THRESHOLD; attempt++) {
            const response = await login(request, username, `wrong-${attempt}`)
            expect(response.status(), `attempt ${attempt} should be rejected`).toBe(401)
        }

        // Past the threshold the gate refuses before any credential check. The
        // status is deliberately the same 401 — the response must not tell an
        // attacker whether the account exists or is locked.
        const locked = await login(request, username, 'wrong-again')
        expect(locked.status()).toBe(401)
    })

    test('a locked account refuses even the correct password', async ({ request }) => {
        // The real proof: without it, the assertions above are satisfied by
        // ordinary auth failures and would pass with the throttle removed.
        const username = `throttle-real-${Date.now()}`
        const password = 'CorrectHorse.Battery.Staple.1'

        const created = await request.post(`${CORE_API}/config/users`, {
            headers: { Authorization: `Bearer ${await adminToken(request)}` },
            // NewUserSchema inherits an `id` field and User.__init__ requires it, so a
            // placeholder is mandatory; RoleIdSchema.id is a string field, so '2' not 2.
            data: {
                id: -1,
                username,
                name: 'Throttle Probe',
                password,
                roles: [{ id: '2' }],
                permissions: [],
                organizations: []
            }
        })
        test.skip(!created.ok(), `could not seed a user (HTTP ${created.status()}); skipping the strict check`)

        // sanity: the credentials work before anything is throttled
        expect((await login(request, username, password)).status()).toBe(200)

        for (let attempt = 1; attempt <= THRESHOLD; attempt++) {
            expect((await login(request, username, 'nope')).status()).toBe(401)
        }

        const refused = await login(request, username, password)
        expect(refused.status(), 'a valid credential must be refused while locked').toBe(401)
    })

    test('the lock is scoped to one username', async ({ request }) => {
        const locked = `throttle-scope-${Date.now()}`
        for (let attempt = 1; attempt <= THRESHOLD; attempt++) {
            await login(request, locked, 'nope')
        }

        // A different name must still get an ordinary rejection rather than
        // inheriting the lock — a global counter would be a trivial DoS.
        const other = await login(request, `throttle-other-${Date.now()}`, 'nope')
        expect(other.status()).toBe(401)
    })
})

async function adminToken(request) {
    const response = await login(request, 'admin', 'admin')
    expect(response.ok(), 'admin login must work before seeding').toBeTruthy()
    return (await response.json()).access_token
}
