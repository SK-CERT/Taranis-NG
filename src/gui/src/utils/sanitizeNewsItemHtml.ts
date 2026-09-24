import DOMPurify, { type Config } from 'dompurify'

const NEWS_ITEM_HTML_CONFIG: Config = {
    ALLOWED_TAGS: [
        'p',
        'h1',
        'h2',
        'h3',
        'h4',
        'ul',
        'ol',
        'li',
        'b',
        'strong',
        'i',
        'em',
        'a',
        'pre',
        'code',
        'br',
        'div',
        'span',
        'blockquote',
        'mark',
        'small',
        'del',
        'ins',
        'sup',
        'sub',
        'u',
        's'
    ],
    ALLOWED_ATTR: ['href'],
    ALLOW_ARIA_ATTR: false,
    ALLOW_DATA_ATTR: false,
    // Allow HTTP(S), email, and scheme-free relative links. Reject protocol-relative
    // URLs and every other scheme, including control-character-obfuscated variants.
    ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto):|(?!(?:\s*[a-z](?:[a-z0-9+.-]|\s)*:|\s*[/\\]{2})))/i
}

export function sanitizeNewsItemHtml(content: string | null | undefined): string {
    return DOMPurify.sanitize(content ?? '', NEWS_ITEM_HTML_CONFIG)
}
