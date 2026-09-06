/**
 * Option handling shared by the attribute types that pick from a fixed list
 * (ENUM, RADIO, MULTI_CHOICE).
 *
 * The backend ships the choices as `attribute.attribute_enums`, an array of
 * `{ id, index, value, description }` objects (see AttributeEnumSchema). The
 * `enum_items`/`enum_values` fallbacks exist because older fixtures and remote
 * payloads use those names, and plain scalars are accepted so a caller can pass
 * a hand-written list.
 */

export type EnumOptionObject = {
    value?: string | number
    title?: string
    name?: string
    id?: string | number
    [key: string]: unknown
}

export type EnumOption = string | number | EnumOptionObject

export type EnumAttributeGroup = {
    attribute?: {
        attribute_enums?: EnumOption[]
        enum_items?: EnumOption[]
        enum_values?: EnumOption[]
    } | null
    [key: string]: unknown
}

/** The choices an attribute offers, whichever key the payload used. */
export function enumOptionsOf(attributeGroup?: EnumAttributeGroup | null): EnumOption[] {
    return attributeGroup?.attribute?.attribute_enums || attributeGroup?.attribute?.enum_items || attributeGroup?.attribute?.enum_values || []
}

/** What the user reads for an option. */
export function enumOptionLabel(option: EnumOption): string {
    if (option && typeof option === 'object') {
        return String(option.value ?? option.title ?? option.name ?? option.id ?? '')
    }
    return String(option ?? '')
}

/** What gets stored when an option is picked. */
export function enumOptionValue(option: EnumOption): unknown {
    if (option && typeof option === 'object') {
        return option.value ?? option.id ?? option.title ?? option.name
    }
    return option
}
