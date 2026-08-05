import { beforeEach, describe, expect, it, vi } from 'vitest'
import { addAttributeEnum, reloadDictionaries } from '@/api/config'
import ApiService from '@/services/api_service'

vi.mock('@/services/api_service', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn()
    }
}))

describe('configuration API', () => {
    beforeEach(() => vi.clearAllMocks())

    it('reloads the requested vulnerability dictionary through the protected configuration route', () => {
        reloadDictionaries('cwe')
        expect(ApiService.get).toHaveBeenCalledWith('/config/reload-enum-dictionaries/cwe')
    })

    it('sends imported attribute constants and replace mode unchanged', () => {
        const payload = {
            items: [{ value: 'CWE-79', description: 'Cross-site scripting' }],
            delete_existing: true
        }
        addAttributeEnum(42, payload)
        expect(ApiService.post).toHaveBeenCalledWith('/config/attributes/42/enums', payload)
    })
})
