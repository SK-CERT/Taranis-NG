import { isStructuredType, parseStructured, serializeStructured } from '@/components/common/attribute/structuredValue'

type FieldValue = {
    value?: unknown
    binary_mime_type?: string | null
    binary_size?: number | null
}

export type FieldDefinition = {
    id?: number
    title?: string
    min_occurrence?: number | null
    max_occurrence?: number | null
    attribute?: { type?: string } | null
}

type FieldItem = {
    attribute_group_item?: FieldDefinition | null
    values?: FieldValue[] | null
}

type FieldGroup = {
    attribute_group_items?: FieldItem[] | null
}

/**
 * A field is required when its report type asks for at least one value (min occurrence 1 or
 * more). A label-only field (max occurrence 0) holds no values, so it never is.
 */
export function isRequiredField(field?: FieldDefinition | null): boolean {
    return (field?.min_occurrence ?? 0) >= 1 && (field?.max_occurrence ?? Infinity) !== 0
}

const TAGS = /<[^>]*>/g

/** Whether a value says anything: not blank, not an empty editor, not an untouched structure. */
export function hasContent(value: FieldValue | null | undefined, type?: string | null): boolean {
    if (!value) return false
    if (type === 'BOOLEAN') return true
    if (type === 'ATTACHMENT') return Boolean(value.binary_mime_type || value.binary_size || String(value.value ?? '').trim())
    const raw = value.value
    if (raw === null || raw === undefined) return false
    if (typeof raw !== 'string') return true
    if (type === 'RICH_TEXT')
        return (
            /<img\b/i.test(raw) ||
            raw
                .replace(TAGS, '')
                .replace(/&nbsp;/g, ' ')
                .trim() !== ''
        )
    if (isStructuredType(type)) return serializeStructured(parseStructured(raw)) !== ''
    return raw.trim() !== ''
}

export type MissingField = { id: number; title: string }

/** The required fields with fewer filled values than they need, in the order of the form. */
export function emptyRequiredFields(groups: readonly FieldGroup[] | null | undefined): MissingField[] {
    const missing: MissingField[] = []
    for (const group of groups ?? []) {
        for (const item of group.attribute_group_items ?? []) {
            const field = item.attribute_group_item
            if (!field || field.id === undefined || !isRequiredField(field)) continue
            const type = field.attribute?.type
            const filled = (item.values ?? []).filter((value) => hasContent(value, type)).length
            if (filled < (field.min_occurrence ?? 0)) missing.push({ id: field.id, title: field.title ?? '' })
        }
    }
    return missing
}
