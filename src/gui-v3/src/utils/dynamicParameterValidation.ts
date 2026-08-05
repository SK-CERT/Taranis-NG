export type DynamicParameterDefinition = {
    required?: boolean
}

export type ValidationRule = (value: unknown) => true | string

/**
 * Dynamic module parameters historically predate the explicit `required` flag,
 * so an omitted flag keeps the legacy required behaviour. Module definitions can
 * opt a parameter out with `required: false` without weakening every generated
 * field.
 */
export function dynamicParameterRules(parameter: DynamicParameterDefinition, requiredMessage: string): ValidationRule[] {
    if (parameter.required === false) return []

    return [(value: unknown) => String(value ?? '').trim().length > 0 || requiredMessage]
}
