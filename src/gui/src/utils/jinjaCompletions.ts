/**
 * Autocompletion for the public web's report templates (Jinja), in the template editor.
 *
 * Inside `{{ ... }}` and `{% ... %}` it offers what a template can use: the context variables
 * (`product`, `item`, `links`, ...), their fields after a dot (`product.max_cvss`), the
 * attribute keys of the chosen report item type after `item.attrs.`, the filters after `|`,
 * the statements after `{%`, and the built-in templates after `extends`/`import`. Outside the
 * Jinja delimiters it offers nothing: the HTML around is the author's own.
 *
 * The lists mirror what public-web gives a template (see src/public_web/README.md and
 * shared/public_web_templates); FILTERS is pinned to the shared list by a unit test.
 */
import type { Completion, CompletionContext, CompletionResult } from 'prism-code-editor/autocomplete'

export type TemplateKind = 'product' | 'item'

export type JinjaCompletionSettings = {
    /** A product template gets `render_item`, `visible_links`, ...; an item template `item`, `index`. */
    kind: TemplateKind
    /** The attribute keys of the report item type the template is for (`item.attrs.<key>`). */
    attrKeys?: string[]
}

/** Every filter public-web registers (shared/public_web_templates FILTER_NAMES). */
export const FILTERS = [
    'affected_system',
    'as_list',
    'capitalize_first',
    'clean',
    'clean_rich',
    'cvss_calculator_url',
    'cvss_score',
    'cvss_severity',
    'fix_spaces',
    'iso_date',
    'link_refs',
    'regex_replace',
    'safe_url',
    'single',
    'strfdate',
    'tlp_color',
    'truncate_on_symbol',
    'ymd_date'
] as const

// The Jinja built-in filters templates use most; the sandbox allows them all.
const JINJA_FILTERS = [
    'default',
    'first',
    'join',
    'last',
    'length',
    'list',
    'lower',
    'map',
    'reject',
    'rejectattr',
    'replace',
    'select',
    'selectattr',
    'sort',
    'string',
    'striptags',
    'trim',
    'truncate',
    'unique',
    'upper',
    'xmlattr'
]

const FILTER_DOCS: Record<string, string> = {
    clean: 'escape all HTML but the links link_refs made',
    clean_rich: 'keep basic formatting of rich text, escape the rest',
    link_refs: '[n] → link to the product’s links: link_refs(links) | clean',
    single: 'the value, or the first of several',
    as_list: 'the values as a list',
    cvss_calculator_url: 'FIRST calculator link for a CVSS 3.0/3.1/4.0 vector, else empty',
    cvss_score: 'base score of a CVSS vector or number',
    cvss_severity: 'Low/Medium/High/Critical',
    iso_date: 'ISO date → D. M. YYYY',
    safe_url: 'the URL if http(s)/mailto, else empty'
}

const STATEMENTS = [
    'if',
    'elif',
    'else',
    'endif',
    'for',
    'endfor',
    'set',
    'block',
    'endblock',
    'extends',
    'import',
    'from',
    'macro',
    'endmacro',
    'call',
    'endcall',
    'filter',
    'endfilter',
    'with',
    'endwith',
    'raw',
    'endraw'
]

const BUILTIN_TEMPLATES = [
    'builtin/product_base.html',
    'builtin/product_vulnerability.html',
    'builtin/item_vulnerability.html',
    'builtin/item_generic.html',
    'builtin/_macros.html'
]

const PRODUCT_FIELDS = [
    'id',
    'title',
    'description',
    'published',
    'created',
    'author',
    'author_username',
    'product_preset',
    'language',
    'ai_translation',
    'original_language',
    'report_items',
    'body_items',
    'links',
    'max_tlp',
    'max_cvss',
    'is_vulnerability',
    'lead'
]

const ITEM_FIELDS = [
    'name',
    'name_prefix',
    'uuid',
    'type',
    'type_label',
    'type_id',
    'type_description',
    'language',
    'ai_translation',
    'original_language',
    'created',
    'last_updated',
    'attrs',
    'attrs_display',
    'attributes',
    'fields'
]

const COMMON_VARIABLES = ['product', 'links', 'lang', 'site', 't', 'data', 'view']
const PRODUCT_VARIABLES = ['render_item', 'visible_links', 'selected_items', 'loop', 'macros']
const ITEM_VARIABLES = ['item', 'index', 'macros']

const NESTED_FIELDS: Record<string, string[]> = {
    'product': PRODUCT_FIELDS,
    'item': ITEM_FIELDS,
    'product.product_preset': ['id', 'title'],
    'site': ['content', 'metadata', 'hostname', 'language'],
    'data': ['product', 'report_items'],
    'loop': ['index', 'index0', 'first', 'last', 'length'],
    'macros': ['content_lang', 'severity_badge']
}

/** Whether the cursor sits inside `{{ ... }}`, `{% ... %}` (true) or in the HTML around (false). */
export function insideJinja(before: string): boolean {
    const open = Math.max(before.lastIndexOf('{{'), before.lastIndexOf('{%'))
    if (open < 0) return false
    const close = Math.max(before.lastIndexOf('}}'), before.lastIndexOf('%}'))
    return close < open
}

function options(labels: readonly string[], icon: NonNullable<Completion['icon']>, docs: Record<string, string> = {}): Completion[] {
    return labels.map((label) => ({ label, icon, ...(docs[label] ? { detail: docs[label] } : {}) }))
}

/** The completions for the text before the cursor; null where there is nothing to offer. */
export function jinjaCompletions(before: string, settings: JinjaCompletionSettings): { from: number; options: Completion[] } | null {
    if (!insideJinja(before)) return null
    const end = before.length

    // A built-in to extend or import: {% extends "builtin/pr|
    const quoted = /\{%-?\s*(?:extends|import|from|include)\s+["']([^"']*)$/.exec(before)
    if (quoted) {
        return { from: end - quoted[1]!.length, options: options(BUILTIN_TEMPLATES, 'constant') }
    }

    // A statement right after {%
    const statement = /\{%-?\s*(\w*)$/.exec(before)
    if (statement) {
        return { from: end - statement[1]!.length, options: options(STATEMENTS, 'keyword') }
    }

    // A filter after |
    const filter = /\|\s*(\w*)$/.exec(before)
    if (filter) {
        return {
            from: end - filter[1]!.length,
            options: [...options(FILTERS, 'function', FILTER_DOCS), ...options(JINJA_FILTERS, 'function')]
        }
    }

    // A name, or a field after a dot: product.max_c|, item.attrs.cv|
    const path = /([A-Za-z_][\w.]*)$/.exec(before)
    const typed = path ? path[1]! : ''
    const dot = typed.lastIndexOf('.')
    if (dot < 0) {
        // Only after a character that can start an expression; not inside a word or a string.
        if (!/(^|[\s({[,=!<>+\-*/%~]|\{\{-?|\{%-?)$/.test(before.slice(0, end - typed.length))) return null
        const variables = [...COMMON_VARIABLES, ...(settings.kind === 'product' ? PRODUCT_VARIABLES : ITEM_VARIABLES)]
        return { from: end - typed.length, options: options(variables, 'variable') }
    }
    const owner = typed.slice(0, dot)
    const partial = typed.slice(dot + 1)
    const keys = /(^|\.)attrs(_display)?$/.test(owner)
        ? (settings.attrKeys ?? [])
        : (NESTED_FIELDS[owner] ?? NESTED_FIELDS[owner.split('.').pop() ?? ''])
    if (!keys || keys.length === 0) return null
    return { from: end - partial.length, options: options(keys, 'property') }
}

/** A prism-code-editor completion source reading the settings of the editor it is asked for. */
export function jinjaCompletionSource(
    settings: () => JinjaCompletionSettings | null
): (context: CompletionContext) => CompletionResult | null {
    return (context) => {
        const current = settings()
        return current ? jinjaCompletions(context.before, current) : null
    }
}
