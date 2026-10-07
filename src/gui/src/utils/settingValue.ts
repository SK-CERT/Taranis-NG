import { Settings, type SettingKey } from '@/types/settings'

export type SettingType = 'B' | 'I' | 'N' | 'S'

/**
 * Integer settings that only make sense within bounds. The settings API stores any text, so
 * core keeps the value it reads inside the same range; checking here says so before saving.
 */
export const INTEGER_SETTING_RANGES: Partial<Record<SettingKey, readonly [number, number]>> = {
    [Settings.TAG_CLOUD_RETENTION_DAYS]: [1, 365]
}

export type SettingValueProblem =
    | { message: 'settings.boolean_error' }
    | { message: 'settings.integer_error' }
    | { message: 'settings.decimal_error' }
    | { message: 'settings.integer_range_error'; min: number; max: number }

export type SettingValueCheck = { value: string; problem?: undefined } | { value?: undefined; problem: SettingValueProblem }

/**
 * Normalize a value typed for a setting, or say why it cannot be stored.
 *
 * Integers must be written as integers: core reads them with `int()`, which refuses `1e2`
 * or `5.0` although JavaScript's `Number` takes them.
 */
export function checkSettingValue(key: SettingKey, type: SettingType | undefined, input: string): SettingValueCheck {
    const value = input.trim()

    if (type === 'B') {
        const lowered = value.toLowerCase()
        return lowered === 'true' || lowered === 'false' ? { value: lowered } : { problem: { message: 'settings.boolean_error' } }
    }
    if (type === 'I') {
        if (!/^[+-]?\d+$/.test(value)) return { problem: { message: 'settings.integer_error' } }
        const number = Number(value)
        const range = INTEGER_SETTING_RANGES[key]
        if (range && (number < range[0] || number > range[1])) {
            return { problem: { message: 'settings.integer_range_error', min: range[0], max: range[1] } }
        }
        return { value: String(number) }
    }
    if (type === 'N') {
        return Number.isFinite(Number(value)) ? { value } : { problem: { message: 'settings.decimal_error' } }
    }
    return { value }
}
