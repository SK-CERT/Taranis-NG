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
