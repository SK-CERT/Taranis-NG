import { describe, expect, it } from 'vitest'
import { emptyRequiredFields, hasContent, isRequiredField } from '@/utils/requiredFields'

const field = (id: number, type: string, min = 1, max: number | null = 1) => ({
    id,
    title: `Field ${id}`,
    min_occurrence: min,
    max_occurrence: max,
    attribute: { type }
})

describe('isRequiredField', () => {
    it('is a field that needs at least one value', () => {
        expect(isRequiredField(field(1, 'STRING', 1))).toBe(true)
        expect(isRequiredField(field(1, 'STRING', 2, 5))).toBe(true)
        expect(isRequiredField(field(1, 'STRING', 0))).toBe(false)
    })

    it('is never a label without values', () => {
        expect(isRequiredField(field(1, 'STRING', 1, 0))).toBe(false)
    })
})

describe('hasContent', () => {
    it('ignores blank text and an empty editor', () => {
        expect(hasContent({ value: '  ' }, 'STRING')).toBe(false)
        expect(hasContent({ value: '<p></p>' }, 'RICH_TEXT')).toBe(false)
        expect(hasContent({ value: '<p>&nbsp;</p>' }, 'RICH_TEXT')).toBe(false)
        expect(hasContent({ value: '<p>Text</p>' }, 'RICH_TEXT')).toBe(true)
        expect(hasContent({ value: '<p><img src="x.png"></p>' }, 'RICH_TEXT')).toBe(true)
    })

    it('ignores an untouched structured value', () => {
        expect(hasContent({ value: '' }, 'AFFECTED')).toBe(false)
        expect(hasContent({ value: '{"vendor": "", "versions": []}' }, 'AFFECTED')).toBe(false)
        expect(hasContent({ value: '{"vendor": "Example"}' }, 'AFFECTED')).toBe(true)
    })

    it('takes an attachment by its file and a checkbox as always set', () => {
        expect(hasContent({ value: '', binary_mime_type: 'application/pdf' }, 'ATTACHMENT')).toBe(true)
        expect(hasContent({ value: '' }, 'ATTACHMENT')).toBe(false)
        expect(hasContent({ value: 'false' }, 'BOOLEAN')).toBe(true)
    })
})

describe('emptyRequiredFields', () => {
    it('lists the required fields with fewer filled values than they need, in form order', () => {
        const groups = [
            {
                attribute_group_items: [
                    { attribute_group_item: field(1, 'STRING'), values: [{ value: 'filled' }] },
                    { attribute_group_item: field(2, 'RICH_TEXT'), values: [{ value: '<p></p>' }] },
                    { attribute_group_item: field(3, 'STRING', 0), values: [] }
                ]
            },
            {
                attribute_group_items: [
                    { attribute_group_item: field(4, 'CVE', 2, 5), values: [{ value: 'CVE-2026-1' }, { value: '' }] },
                    { attribute_group_item: field(5, 'DATE'), values: [] }
                ]
            }
        ]

        expect(emptyRequiredFields(groups).map((missing) => missing.id)).toEqual([2, 4, 5])
    })
})
