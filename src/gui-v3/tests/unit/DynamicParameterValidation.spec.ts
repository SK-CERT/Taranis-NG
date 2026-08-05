import { describe, expect, it } from 'vitest'
import { dynamicParameterRules } from '@/utils/dynamicParameterValidation'

describe('dynamic parameter validation', () => {
    it('keeps legacy parameter definitions required', () => {
        const [rule] = dynamicParameterRules({}, 'Required')
        if (!rule) throw new Error('Expected a required-field validation rule')

        expect(rule('')).toBe('Required')
        expect(rule('   ')).toBe('Required')
        expect(rule('configured')).toBe(true)
    })

    it('keeps explicitly optional parameters optional', () => {
        expect(dynamicParameterRules({ required: false }, 'Required')).toEqual([])
    })
})
