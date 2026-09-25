export type WordListEntry = {
    value: string
    description: string
}

const countDelimiters = (input: string, delimiter: string): number => {
    let count = 0
    let quoted = false
    for (let index = 0; index < input.length; index += 1) {
        const character = input[index]
        if (character === '"') {
            if (quoted && input[index + 1] === '"') index += 1
            else quoted = !quoted
        } else if (!quoted && (character === '\n' || character === '\r')) {
            break
        } else if (!quoted && character === delimiter) {
            count += 1
        }
    }
    return count
}

const detectDelimiter = (input: string): string => {
    const delimiters = [';', ',', '\t']
    return delimiters.reduce((best, candidate) => (countDelimiters(input, candidate) > countDelimiters(input, best) ? candidate : best))
}

export const parseDelimitedRecords = (input: string): string[][] => {
    const records: string[][] = []
    let record: string[] = []
    let field = ''
    let quoted = false
    const text = input.replace(/^\uFEFF/, '')
    const delimiter = detectDelimiter(text)

    for (let index = 0; index < text.length; index += 1) {
        const character = text[index]
        if (character === '"') {
            if (quoted && text[index + 1] === '"') {
                field += '"'
                index += 1
            } else {
                quoted = !quoted
            }
        } else if (character === delimiter && !quoted) {
            record.push(field)
            field = ''
        } else if ((character === '\n' || character === '\r') && !quoted) {
            record.push(field)
            if (record.some((value) => value.length)) records.push(record)
            record = []
            field = ''
            if (character === '\r' && text[index + 1] === '\n') index += 1
        } else {
            field += character
        }
    }

    if (quoted) throw new Error('Unterminated quoted CSV field')
    record.push(field)
    if (record.some((value) => value.length)) records.push(record)
    return records
}

export const parseWordListCsv = (input: string, hasHeader = true): WordListEntry[] => {
    const records = parseDelimitedRecords(input)
    if (!records.length) return []

    let valueIndex = 0
    let descriptionIndex = 1
    if (hasHeader) {
        const header = records.shift()?.map((value) => value.trim().toLowerCase()) || []
        const matchedValueIndex = header.indexOf('value')
        const matchedDescriptionIndex = header.indexOf('description')
        if (matchedValueIndex !== -1) valueIndex = matchedValueIndex
        descriptionIndex = matchedDescriptionIndex
    }

    const unique = new Map<string, WordListEntry>()
    for (const record of records) {
        const value = (record[valueIndex] || '').trim()
        if (!value) continue
        unique.set(value, {
            value,
            description: descriptionIndex === -1 ? '' : (record[descriptionIndex] || '').trim()
        })
    }
    return [...unique.values()]
}

export const mergeWordListEntries = (existing: WordListEntry[], incoming: WordListEntry[], replaceExisting = false): WordListEntry[] => {
    const unique = new Map<string, WordListEntry>()
    for (const entry of replaceExisting ? incoming : [...existing, ...incoming]) {
        unique.set(entry.value, { ...entry })
    }
    return [...unique.values()]
}
