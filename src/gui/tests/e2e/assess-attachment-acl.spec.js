import { test, expect } from '@playwright/test'
import { createApiContext, getFirstOSINTSourceId } from '../helpers/api-seed'

/**
 * Attachment download authorization (api/assess.py DownloadAttachment).
 *
 * The endpoint used to resolve `NewsItemAttribute.find(attribute_id)` globally
 * and ignore the item_data_id in the URL entirely, so any user with
 * ASSESS_ACCESS could read any group's attachment by guessing attribute IDs.
 *
 * The unit suite monkeypatches `allowed_with_acl`, so no test anywhere exercises
 * the real ACL query. That is what this spec adds — plus the regression test for
 * the unguarded db.session.get() that turned an unknown ID into a 500.
 */

const CORE_API = process.env.E2E_CORE_API || `http://127.0.0.1:${process.env.E2E_CORE_PORT || '8090'}/api/v1`

test.describe('Attachment download authorization', () => {
    let request
    let token

    test.beforeAll(async ({ playwright }) => {
        ;({ request, token } = await createApiContext(playwright))
    })

    test.afterAll(async () => {
        await request?.dispose()
    })

    const download = (itemDataId, attributeId) =>
        request.post(`${CORE_API}/assess/news-item-data/${itemDataId}/attributes/${attributeId}/file`, {
            headers: { Authorization: `Bearer ${token}` }
        })

    test('an unknown item-data id is refused, not a server error', async () => {
        // allowed_with_acl dereferenced db.session.get() without a None check, so
        // this raised AttributeError and the endpoint answered 500.
        const response = await download('no-such-news-item-data', 1)
        expect(response.status(), 'must not be a 5xx').toBeLessThan(500)
        expect([401, 404]).toContain(response.status())
    })

    test('a bare attribute id does not yield a file on its own', async () => {
        // The IDOR: an attribute that exists but does not belong to the named
        // news item data must not be served.
        const sourceId = await getFirstOSINTSourceId(request, token)
        test.skip(!sourceId, 'no OSINT source available in this environment')

        for (const attributeId of [1, 2, 3]) {
            const response = await download('not-the-owning-item-data', attributeId)
            expect(response.status(), `attribute ${attributeId} must not be served`).not.toBe(200)
            expect(response.status()).toBeLessThan(500)
        }
    })

    test('the endpoint still requires authentication', async ({ request: anonymous }) => {
        const response = await anonymous.post(`${CORE_API}/assess/news-item-data/whatever/attributes/1/file`)
        expect([401, 403, 422]).toContain(response.status())
    })
})
