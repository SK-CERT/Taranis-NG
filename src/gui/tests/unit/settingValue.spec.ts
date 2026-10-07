import { describe, expect, it } from 'vitest'
import { Settings } from '@/types/settings'
import { checkSettingValue } from '@/utils/settingValue'

describe('checkSettingValue', () => {
    it('keeps the tag cloud retention within 1 to 365 days', () => {
        expect(checkSettingValue(Settings.TAG_CLOUD_RETENTION_DAYS, 'I', '1')).toEqual({ value: '1' })
        expect(checkSettingValue(Settings.TAG_CLOUD_RETENTION_DAYS, 'I', ' 365 ')).toEqual({ value: '365' })
        for (const outside of ['0', '366', '-5']) {
            expect(checkSettingValue(Settings.TAG_CLOUD_RETENTION_DAYS, 'I', outside)).toEqual({
                problem: { message: 'settings.integer_range_error', min: 1, max: 365 }
            })
        }
    })

    it('accepts only integers written as integers, as core reads them', () => {
        for (const notAnInteger of ['abc', '', '5.0', '1e2', '7 days']) {
            expect(checkSettingValue(Settings.TAG_CLOUD_RETENTION_DAYS, 'I', notAnInteger)).toEqual({
                problem: { message: 'settings.integer_error' }
            })
        }
        expect(checkSettingValue(Settings.TAG_CLOUD_RETENTION_DAYS, 'I', '+07')).toEqual({ value: '7' })
    })

    it('checks booleans and decimals as before', () => {
        expect(checkSettingValue(Settings.SPELLCHECK, 'B', ' TRUE ')).toEqual({ value: 'true' })
        expect(checkSettingValue(Settings.SPELLCHECK, 'B', 'yes')).toEqual({ problem: { message: 'settings.boolean_error' } })
        expect(checkSettingValue(Settings.DATE_FORMAT, 'N', '1.5')).toEqual({ value: '1.5' })
        expect(checkSettingValue(Settings.DATE_FORMAT, 'N', 'x')).toEqual({ problem: { message: 'settings.decimal_error' } })
    })

    it('leaves text settings as typed, trimmed', () => {
        expect(checkSettingValue(Settings.DATE_FORMAT, 'S', ' dd.MM.yyyy ')).toEqual({ value: 'dd.MM.yyyy' })
    })
})
