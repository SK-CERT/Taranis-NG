import { describe, expect, it } from 'vitest'
import { halfWidthItemIds } from '@/utils/attributeLayout'

const item = (id: number, type: string) => ({ attribute_group_item: { id, attribute: { type } } })

describe('halfWidthItemIds', () => {
    it('pairs neighbouring compact attributes', () => {
        const groups = [{ attribute_group_items: [item(1, 'DATE'), item(2, 'DATE'), item(3, 'TEXT')] }]
        expect([...halfWidthItemIds(groups)]).toEqual([1, 2])
    })

    // A compact attribute alone would leave the other half of its row empty.
    it('gives a compact attribute without a neighbour the whole width', () => {
        const groups = [{ attribute_group_items: [item(1, 'CVE'), item(2, 'RELATIONSHIP'), item(3, 'CWE'), item(4, 'STRING')] }]
        expect(halfWidthItemIds(groups).size).toBe(0)
    })

    it('leaves the odd one out of a run full width', () => {
        const groups = [{ attribute_group_items: [item(1, 'DATE'), item(2, 'CVE'), item(3, 'CWE')] }]
        expect([...halfWidthItemIds(groups)]).toEqual([1, 2])
    })

    it('never pairs across groups', () => {
        const groups = [{ attribute_group_items: [item(1, 'DATE')] }, { attribute_group_items: [item(2, 'DATE')] }]
        expect(halfWidthItemIds(groups).size).toBe(0)
    })
})
