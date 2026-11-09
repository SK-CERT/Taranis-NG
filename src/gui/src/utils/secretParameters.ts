/**
 * Module parameters that hold credentials (passwords, tokens, API keys, the SSH private key).
 *
 * Core never sends their values back to the GUI: a stored one arrives empty with `value_set`,
 * and saving it empty keeps it (core managers/stored_secrets.py, same pattern).
 */
const SECRET_PARAMETER = /(PASSWORD|TOKEN|SECRET|API_KEY|SSH_KEY)$/

export function isSecretParameter(key: unknown): boolean {
    return typeof key === 'string' && SECRET_PARAMETER.test(key)
}

type StoredParameterValue = {
    value_set?: boolean
    parameter?: { key?: string | null } | null
}

/** The keys of the secret parameters that have a stored value. */
export function storedSecretKeys(values: readonly StoredParameterValue[] | null | undefined): Set<string> {
    const keys = new Set<string>()
    for (const value of values ?? []) {
        const key = value.parameter?.key
        if (value.value_set === true && typeof key === 'string' && isSecretParameter(key)) keys.add(key)
    }
    return keys
}
