/** A report template of the public web, for one product preset or one report item type. */
export type PublicWebTemplate = {
    id: number | null
    name: string
    product_preset_id: number | null
    report_item_type_id: number | null
    source: string
    /** Product templates only: whether a product without any TLP stays hidden. */
    require_tlp_clear: boolean
    /** The webs it applies to; none: every web. */
    public_web_ids: number[]
    web_names?: string[]
    target_title?: string
    updated_at?: string
    updated_by?: string | null
}

/** A built-in report template: never deleted, but those public-web falls back on can be switched off. */
export type PublicWebBuiltinTemplate = {
    /** What `extends` and `import` refer to: `builtin/<file>`. */
    name: string
    source: string
    /** False for the base layout and the macros, which custom templates build on. */
    can_disable: boolean
    enabled: boolean
    updated_at?: string | null
    updated_by?: string | null
}

/** A web a template can be previewed on; `unavailable` says why its node cannot render (null: it can). */
export type PreviewWeb = {
    id: number
    name: string
    node: string
    unavailable: string | null
    languages: string[]
    default_language: string | null
}

export type PreviewProduct = { id: number; title: string; created: string | null }

export type PreviewOptions = { webs: PreviewWeb[]; web_id: number | null; products: PreviewProduct[] }

export type PreviewView = 'detail' | 'summary' | 'rss'

/** A template that failed while rendering; the built-in one was shown in its place. */
export type PreviewTemplateError = { template: string; line: number | null; message: string }

export type PreviewResult = {
    view: PreviewView
    /** The rendered page (report page, homepage): core's URL of it, under the API base, good for a few views. */
    page_url?: string
    rss?: { title: string; link: string; description: string }
    xml?: string
    errors: PreviewTemplateError[]
    warnings: string[]
    language?: string
    web_id?: number
    product_id?: number
}
