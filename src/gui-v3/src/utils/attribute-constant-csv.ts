import { parseDelimitedRecords } from '@/utils/word-list-csv'

export type AttributeConstantImport = {
    value: string
    description: string
}

export type AttributeConstantCsv = {
    headers: string[]
    records: string[][]
}

export const readAttributeConstantCsv = (input: string, hasHeader: boolean): AttributeConstantCsv => {
    const records = parseDelimitedRecords(input)
    if (records.length === 0) return { headers: [], records: [] }

    const columnCount = Math.max(...records.map((record) => record.length))
    const generatedHeaders = Array.from({ length: columnCount }, (_, index) => `#${index + 1}`)
    if (!hasHeader) return { headers: generatedHeaders, records }

    const headerRecord = records.shift() ?? []
    return {
        headers: generatedHeaders.map((fallback, index) => headerRecord[index]?.trim() || fallback),
        records
    }
}

export const mapAttributeConstantRows = (
    records: string[][],
    valueColumn: number | null,
    descriptionColumn: number | null
): AttributeConstantImport[] => {
    if (valueColumn === null || valueColumn < 0) return []

    const unique = new Map<string, AttributeConstantImport>()
    for (const record of records) {
        const value = (record[valueColumn] ?? '').trim()
        if (!value) continue
        const description = descriptionColumn === null ? '' : (record[descriptionColumn] ?? '').trim()
        unique.set(value.toLocaleLowerCase(), { value, description })
    }
    return [...unique.values()]
}

export const mergeAttributeConstants = <T extends AttributeConstantImport>(
    existing: T[],
    incoming: AttributeConstantImport[],
    replaceExisting: boolean
): AttributeConstantImport[] => {
    const unique = new Map<string, AttributeConstantImport>()
    const entries = replaceExisting ? incoming : [...existing, ...incoming]
    for (const entry of entries) {
        unique.set(entry.value.toLocaleLowerCase(), { value: entry.value, description: entry.description })
    }
    return [...unique.values()]
}
