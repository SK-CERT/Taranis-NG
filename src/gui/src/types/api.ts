export type Primitive = string | number | boolean | null

export type JsonValue = Primitive | JsonObject | JsonArray

export interface JsonObject {
    [key: string]: JsonValue
}

export interface JsonArray extends Array<JsonValue> {}

export interface ApiEnvelope<T> {
    data: T
    meta?: Record<string, unknown>
    message?: string
}

export interface PaginatedMeta {
    page: number
    items_per_page: number
    total_items: number
    total_pages: number
}

export interface PaginatedResponse<T> {
    data: T[]
    meta: PaginatedMeta
}

export interface ApiError {
    message: string
    status?: number
    details?: unknown
}
