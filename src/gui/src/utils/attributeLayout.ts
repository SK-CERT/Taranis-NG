/** Compact attribute types: a narrow field is enough, so two of them can share a row. */
export const HALF_WIDTH_TYPES: readonly string[] = ['DATE', 'CWE', 'CVE']

type GroupItem = {
    attribute_group_item?: {
        id?: number
        attribute?: { type?: string } | null
    } | null
}

type AttributeGroup = {
    attribute_group_items?: GroupItem[] | null
}

/**
 * The attribute group items shown at half width: neighbouring compact attributes, two by two.
 * One without a compact neighbour to pair with takes the whole width, rather than leaving the
 * other half of its row empty.
 */
export function halfWidthItemIds(groups: readonly AttributeGroup[]): Set<number> {
    const ids = new Set<number>()
    for (const group of groups) {
        let run: number[] = []
        const pairUp = (): void => {
            run.slice(0, run.length - (run.length % 2)).forEach((id) => ids.add(id))
            run = []
        }
        for (const item of group.attribute_group_items ?? []) {
            const groupItem = item?.attribute_group_item
            if (groupItem?.id !== undefined && HALF_WIDTH_TYPES.includes(groupItem.attribute?.type ?? '')) {
                run.push(groupItem.id)
            } else {
                pairUp()
            }
        }
        pairUp()
    }
    return ids
}
