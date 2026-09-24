import { describe, expect, it } from 'vitest'
import { dynamicParameterRules } from '@/utils/dynamicParameterValidation'

describe('dynamic parameter validation', () => {
    it('leaves parameters carrying no explicit flag optional', () => {
        // param_type, the Parameter model and ParameterSchema all lack a `required`
        // field, so this is what EVERY parameter the API returns looks like. Requiring
        // them made any parameter without a default_value block Save outright.
        expect(dynamicParameterRules({}, 'Required')).toEqual([])
    })

    it('keeps explicitly optional parameters optional', () => {
        expect(dynamicParameterRules({ required: false }, 'Required')).toEqual([])
    })

    it('enforces parameters explicitly flagged required', () => {
        const [rule] = dynamicParameterRules({ required: true }, 'Required')
        if (!rule) throw new Error('Expected a required-field validation rule')

        expect(rule('')).toBe('Required')
        expect(rule('   ')).toBe('Required')
        expect(rule('configured')).toBe(true)
    })
})
