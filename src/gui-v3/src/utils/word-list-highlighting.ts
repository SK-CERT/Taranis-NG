export type WordListEntry = {
    value?: unknown
}

export type WordListCategory = {
    entries?: WordListEntry[]
}

export type HighlightWordList = {
    categories?: WordListCategory[]
}

export type HighlightSegment = {
    text: string
    highlighted: boolean
}

const escapeRegularExpression = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export const collectHighlightWords = (wordLists: unknown): string[] => {
    if (!Array.isArray(wordLists)) return []

    const words = new Map<string, string>()
    for (const wordList of wordLists as HighlightWordList[]) {
        if (!Array.isArray(wordList?.categories)) continue
        for (const category of wordList.categories) {
            if (!Array.isArray(category?.entries)) continue
            for (const entry of category.entries) {
                if (typeof entry?.value !== 'string') continue
                const value = entry.value.trim()
                const normalized = value.toLocaleLowerCase()
                if (value && !words.has(normalized)) words.set(normalized, value)
            }
        }
    }

    return [...words.values()].sort((left, right) => right.length - left.length)
}

export const splitHighlightedText = (text: unknown, words: string[]): HighlightSegment[] => {
    const value = typeof text === 'string' ? text : text == null ? '' : String(text)
    const patterns = words.filter(Boolean).map(escapeRegularExpression)
    if (!value || patterns.length === 0) return [{ text: value, highlighted: false }]

    const matcher = new RegExp(patterns.join('|'), 'giu')
    const segments: HighlightSegment[] = []
    let position = 0

    for (const match of value.matchAll(matcher)) {
        const matchIndex = match.index ?? position
        if (matchIndex > position) {
            segments.push({ text: value.slice(position, matchIndex), highlighted: false })
        }
        segments.push({ text: match[0], highlighted: true })
        position = matchIndex + match[0].length
    }

    if (position < value.length) {
        segments.push({ text: value.slice(position), highlighted: false })
    }

    return segments.length > 0 ? segments : [{ text: value, highlighted: false }]
}
