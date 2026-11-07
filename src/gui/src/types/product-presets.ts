/**
 * A delivery of a product preset: the product in a language and a format, sent to a channel.
 * No language: the language the product is written in. No channel: the format is only previewed.
 */
export type ProductPresetDelivery = {
    id?: number | null
    language: string | null
    product_format_id: number
    publishing_channel_id: string | null
    product_format_title?: string
    publishing_channel_name?: string | null
    publisher_type?: string | null
}

/** The icon a product preset and its products show unless the preset names another. */
export const DEFAULT_PRODUCT_ICON = 'mdi-package-variant-closed'

/** The product preset whose products Publish lists (/publish/:productPresetId, picked in the sidebar); null for all. */
export function routeProductPresetId(params: Record<string, unknown>): number | null {
    return Number(params['productPresetId']) || null
}

/** What a product is published as: languages and formats, the channels they go to, and the public web. */
export type ProductPreset = {
    id: number | null
    name: string
    description: string
    /** The MDI icon it and its products show; null for the default one. */
    icon?: string | null
    deliveries: ProductPresetDelivery[]
    public_web_enabled: boolean
    public_web_ids: number[]
    public_web_names?: string[]
    updated_at?: string
    updated_by?: string | null
}

/** What a product preset can be made of. */
export type ProductPresetOptions = {
    formats: Array<{ id: number; title: string }>
    channels: Array<{ id: string; name: string; publisher_type?: string | null }>
    public_webs: Array<{ id: number; name: string }>
}

/** The row language that stands for the language the product is written in (a select cannot hold null). */
export const OWN_LANGUAGE = 'own'

/** One row of the product preset form: a language and a format, and every channel they are sent to. */
export type ProductPresetFormatRow = {
    uid: number
    language: string
    product_format_id: number | null
    channel_ids: string[]
}

let nextRowUid = 1

/** Group deliveries into one row per language and format, in the order they first appear. */
export function deliveriesToRows(deliveries: ProductPresetDelivery[]): ProductPresetFormatRow[] {
    const rows = new Map<string, ProductPresetFormatRow>()
    for (const delivery of deliveries) {
        const language = delivery.language ?? OWN_LANGUAGE
        const key = JSON.stringify([language, delivery.product_format_id])
        let row = rows.get(key)
        if (!row) {
            row = { uid: nextRowUid++, language, product_format_id: delivery.product_format_id, channel_ids: [] }
            rows.set(key, row)
        }
        if (delivery.publishing_channel_id && !row.channel_ids.includes(delivery.publishing_channel_id)) {
            row.channel_ids.push(delivery.publishing_channel_id)
        }
    }
    return [...rows.values()]
}

/** The deliveries the rows stand for: a language and format to each of its channels, or format only when it has none. */
export function rowsToDeliveries(rows: ProductPresetFormatRow[]): ProductPresetDelivery[] {
    return rows
        .filter((row) => row.product_format_id !== null)
        .flatMap((row): ProductPresetDelivery[] => {
            const language = row.language === OWN_LANGUAGE ? null : row.language
            const product_format_id = row.product_format_id as number
            return row.channel_ids.length > 0
                ? row.channel_ids.map((channelId) => ({ language, product_format_id, publishing_channel_id: channelId }))
                : [{ language, product_format_id, publishing_channel_id: null }]
        })
}

export function newFormatRow(): ProductPresetFormatRow {
    return { uid: nextRowUid++, language: OWN_LANGUAGE, product_format_id: null, channel_ids: [] }
}
