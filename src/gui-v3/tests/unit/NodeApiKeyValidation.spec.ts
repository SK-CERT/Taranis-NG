import { describe, expect, it } from 'vitest'
import { isNonBlankNodeApiKey, NODE_TYPES } from '@/components/common/nodes/nodeTypes'

describe('service node API-key contract', () => {
    it('requires an API key for every authenticated service node', () => {
        expect(Object.values(NODE_TYPES).map(({ apiKeyRequired }) => apiKeyRequired)).toEqual([true, true, true, true])
    })

    it('rejects empty and whitespace-only API keys', () => {
        expect(isNonBlankNodeApiKey(undefined)).toBe(false)
        expect(isNonBlankNodeApiKey('')).toBe(false)
        expect(isNonBlankNodeApiKey('   ')).toBe(false)
        expect(isNonBlankNodeApiKey(' existing-key ')).toBe(true)
    })
})
