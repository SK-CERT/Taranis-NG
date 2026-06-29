/** ACL item types shared by the New ACL dialog and the ACL table. */
export type ACLItemType = 'COLLECTOR' | 'OSINT_SOURCE' | 'OSINT_SOURCE_GROUP' | 'REPORT_ITEM_TYPE' | 'PRODUCT_TYPE' | 'WORD_LIST'

export type ACLItemTypeOption = {
    title: string
    value: ACLItemType
}

export const ACL_ITEM_TYPES: ACLItemTypeOption[] = [
    { title: 'Collector', value: 'COLLECTOR' },
    { title: 'OSINT Source', value: 'OSINT_SOURCE' },
    { title: 'OSINT Source Group', value: 'OSINT_SOURCE_GROUP' },
    { title: 'Report Item Type', value: 'REPORT_ITEM_TYPE' },
    { title: 'Product Type', value: 'PRODUCT_TYPE' },
    { title: 'Word List', value: 'WORD_LIST' }
]

/** Human-readable label for an ACL item type value (falls back to the raw value). */
export function aclItemTypeLabel(value?: string): string {
    return ACL_ITEM_TYPES.find((t) => t.value === value)?.title ?? value ?? ''
}
