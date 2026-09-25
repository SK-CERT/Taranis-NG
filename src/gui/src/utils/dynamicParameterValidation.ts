export type DynamicParameterDefinition = {
    required?: boolean
}

export type ValidationRule = (value: unknown) => true | string

/**
 * Module parameters are declared in `src/shared/shared/config_*.py` via `param_type`,
 * which has no `required` field. Neither the Parameter model nor ParameterSchema carries
 * one, so the API never sends it and every parameter reaches the GUI with `required`
 * undefined.
 *
 * Treating an omitted flag as "required" therefore made EVERY generated field mandatory,
 * blocking Save on any parameter that renders empty — i.e. any parameter declared without
 * a `default_value` (PROXY_SERVER, USER_AGENT, the EMAIL_PUBLISHER credentials, …) — even
 * when the operator had no reason to set it.
 *
 * A parameter is required only when explicitly flagged `required: true`. Nothing sends
 * that today, so no generated field is currently mandatory; the check is kept so the GUI
 * honours the flag as soon as the backend grows one, with no further change here.
 */
export function dynamicParameterRules(parameter: DynamicParameterDefinition, requiredMessage: string): ValidationRule[] {
    if (parameter.required !== true) return []

    return [(value: unknown) => String(value ?? '').trim().length > 0 || requiredMessage]
}
