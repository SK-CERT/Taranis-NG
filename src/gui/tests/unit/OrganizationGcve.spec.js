import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import OrganizationGcve from '@/components/config/access-management/OrganizationGcve.vue'
import { checkOrganizationGcve, getOrganizationGcve, saveOrganizationGcve, testOrganizationCveServices } from '@/api/config'

// An organization's GCVE and CVE publishing: its GNA (the number gcve.eu allocated, named by the
// gcve.eu directory), what its webs register at gcve.eu, and its CNA account, whose API key is
// write-only. The organization dialog saves it with the organization.

vi.mock('@/api/config', () => ({
    getOrganizationGcve: vi.fn(),
    saveOrganizationGcve: vi.fn(),
    checkOrganizationGcve: vi.fn(),
    testOrganizationCveServices: vi.fn()
}))

const ACCOUNT = {
    environment: 'test',
    short_name: 'example',
    username: 'analyst@example.org',
    has_secret: true,
    complete: true,
    url: 'https://cveawg-test.mitre.org/api',
    updated_by: 'Example Admin',
    updated_at: '2026-11-08T12:00:00Z'
}

const GNA = {
    gna_id: 65535,
    short_name: 'TEST-GNA',
    directory: { id: 65535, short_name: 'TEST-GNA', full_name: 'Example test authority', gcve_url: 'https://advisories.example.org/' },
    directory_checked_at: '2026-11-16T12:00:00Z',
    records_license: 'CC-BY-4.0',
    conformance: { governance: { policy: 'https://example.org/policy' } },
    frozen: false
}

const URLS = [
    {
        key: 'website',
        field: 'gcve_url',
        url: 'https://advisories.example.org/',
        registered: 'https://advisories.example.org/',
        matches: true
    },
    { key: 'pull_api', field: 'gcve_pull_api', url: 'https://advisories.example.org/', registered: null, matches: false },
    {
        key: 'dumps',
        field: 'gcve_dump',
        url: 'https://advisories.example.org/dumps/',
        registered: 'https://old.example.org/',
        matches: false
    },
    { key: 'publication', field: null, url: 'https://advisories.example.org/api/gcve/publication', registered: null, matches: false }
]

const settings = (fields = {}) => ({
    organization_id: 3,
    gna: GNA,
    cve_services: ACCOUNT,
    directory: {
        url: 'https://gcve.eu/dist/gcve.json',
        enabled: true,
        verified: true,
        fetched_at: '2026-11-16T12:00:00Z',
        warning: null,
        error: null
    },
    webs: [{ id: 7, name: 'Advisories', hostname: 'advisories.example.org', enabled: true, urls: URLS }],
    ...fields
})

async function mountPanel(data = settings(), canUpdate = true) {
    vi.mocked(getOrganizationGcve).mockResolvedValue({ data })
    const wrapper = mountWithPlugins(OrganizationGcve, { props: { organizationId: 3, canUpdate } })
    await flushPromises()
    return wrapper
}

const input = (wrapper, name) => wrapper.get(`[data-test="${name}"] input, [data-test="${name}"] textarea`)

describe('OrganizationGcve', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it("shows the GNA as the gcve.eu directory names it, and the organization's account without its key", async () => {
        const wrapper = await mountPanel()

        expect(getOrganizationGcve).toHaveBeenCalledWith(3)
        expect(input(wrapper, 'organization-gna-id').element.value).toBe('65535')
        expect(wrapper.get('[data-test="organization-gna-confirmed"]').text()).toContain('The gcve.eu directory lists GNA 65535 as TEST-GNA')
        expect(wrapper.get('[data-test="organization-gna-confirmed"]').text()).toContain('Example test authority')
        expect(JSON.parse(input(wrapper, 'organization-gna-conformance').element.value)).toEqual(GNA.conformance)
        expect(input(wrapper, 'cve-short-name').element.value).toBe('example')
        expect(input(wrapper, 'cve-api-key').element.value).toBe('')
        expect(wrapper.text()).toContain('An API key is stored. Leave this empty to keep it.')
        expect(wrapper.vm.dirty).toBe(false)
    })

    it('says when the directory does not list the number, and when the number is fixed', async () => {
        const wrapper = await mountPanel(settings({ gna: { ...GNA, short_name: null, directory: null, frozen: true } }))

        expect(wrapper.get('[data-test="organization-gna-unknown"]').text()).toContain('does not list GNA 65535')
        expect(input(wrapper, 'organization-gna-id').attributes('disabled')).toBeDefined()
        expect(wrapper.text()).toContain('it cannot change any more')
    })

    it('compares what the web registers at gcve.eu with the directory', async () => {
        const wrapper = await mountPanel()

        expect(wrapper.get('[data-test="organization-gcve-status-7-website"]').text()).toContain('Registered')
        expect(wrapper.get('[data-test="organization-gcve-status-7-pull_api"]').text()).toContain('Not registered yet')
        expect(wrapper.get('[data-test="organization-gcve-status-7-dumps"]').text()).toContain('gcve.eu has https://old.example.org/')
    })

    it('says when no web publishes the records', async () => {
        const wrapper = await mountPanel(settings({ webs: [] }))

        expect(wrapper.find('[data-test="organization-gcve-no-webs"]').exists()).toBe(true)
    })

    it('checks the directory and the endpoints, and shows what each answered', async () => {
        vi.mocked(checkOrganizationGcve).mockResolvedValue({
            data: settings({
                checks: [
                    {
                        web_id: 7,
                        hostname: 'advisories.example.org',
                        results: [{ key: 'publication', url: URLS[3].url, ok: true, status: 200, detail: '2 records on the first page' }]
                    }
                ]
            })
        })
        const wrapper = await mountPanel()

        await wrapper.get('[data-test="organization-gcve-check"]').trigger('click')
        await flushPromises()

        expect(checkOrganizationGcve).toHaveBeenCalledWith(3)
        expect(wrapper.get('[data-test="organization-gcve-status-7-publication"]').text()).toContain('2 records on the first page')
    })

    it('saves the GNA and keeps the stored key while the field is empty', async () => {
        vi.mocked(saveOrganizationGcve).mockResolvedValue({ data: settings({ gna: { ...GNA, records_license: 'CC0-1.0' } }) })
        const wrapper = await mountPanel()

        await input(wrapper, 'organization-gna-license').setValue('CC0-1.0')
        expect(wrapper.vm.dirty).toBe(true)
        expect(await wrapper.vm.save()).toBe(true)

        expect(vi.mocked(saveOrganizationGcve).mock.calls[0]).toEqual([
            3,
            {
                gna: { gna_id: '65535', records_license: 'CC0-1.0', conformance: GNA.conformance },
                cve_services: { environment: 'test', short_name: 'example', username: 'analyst@example.org' }
            }
        ])
        expect(wrapper.vm.dirty).toBe(false)
    })

    it('sends a new key once, and refuses a conformance that is no JSON object', async () => {
        vi.mocked(saveOrganizationGcve).mockResolvedValue({ data: settings() })
        const wrapper = await mountPanel()

        await input(wrapper, 'cve-api-key').setValue('new-key')
        await wrapper.vm.save()
        expect(vi.mocked(saveOrganizationGcve).mock.calls[0][1].cve_services).toMatchObject({ api_key: 'new-key' })
        expect(input(wrapper, 'cve-api-key').element.value).toBe('')

        await input(wrapper, 'organization-gna-conformance').setValue('[1]')
        expect(await wrapper.vm.save()).toBe(false)
        expect(saveOrganizationGcve).toHaveBeenCalledTimes(1)
    })

    it('needs a key before one is stored, once the account is filled in', async () => {
        const wrapper = await mountPanel(
            settings({ gna: null, cve_services: { environment: 'test', short_name: '', username: '', has_secret: false } })
        )

        await input(wrapper, 'cve-short-name').setValue('example')
        await input(wrapper, 'cve-username').setValue('ann')

        expect(await wrapper.vm.save()).toBe(false)
        expect(saveOrganizationGcve).not.toHaveBeenCalled()
    })

    it('says why the settings were refused', async () => {
        vi.mocked(saveOrganizationGcve).mockRejectedValue({
            response: { data: { error: 'The GNA number 65535 is the one of the organization CERT' } }
        })
        const wrapper = await mountPanel(settings({ gna: null }))

        await input(wrapper, 'organization-gna-id').setValue('65535')
        expect(await wrapper.vm.save()).toBe(false)
        expect(wrapper.get('[data-test="organization-gcve-error"]').text()).toContain('is the one of the organization CERT')
    })

    it('tries the account out and says what CVE Services answered', async () => {
        vi.mocked(testOrganizationCveServices).mockResolvedValueOnce({ data: { name: 'Example CERT', id_quota: 1000, available: 988 } })
        const wrapper = await mountPanel()

        await wrapper.get('[data-test="cve-test"]').trigger('click')
        await flushPromises()
        expect(vi.mocked(testOrganizationCveServices).mock.calls[0]).toEqual([
            3,
            { environment: 'test', short_name: 'example', username: 'analyst@example.org' }
        ])
        expect(wrapper.get('[data-test="cve-test-result"]').text()).toBe(
            'Connected as Example CERT: 988 of 1000 CVE ID reservations available.'
        )

        vi.mocked(testOrganizationCveServices).mockRejectedValueOnce({
            response: { data: { error: 'CVE Services refused the credentials (check the CNA short name, the user and the API key)' } }
        })
        await wrapper.get('[data-test="cve-test"]').trigger('click')
        await flushPromises()
        expect(wrapper.get('[data-test="cve-test-result"]').text()).toContain('CVE Services refused the credentials')
    })
})
