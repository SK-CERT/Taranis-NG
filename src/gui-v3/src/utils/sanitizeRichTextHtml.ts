import DOMPurify from 'dompurify'

const ALLOWED_TAGS = [
    'p',
    'br',
    'b',
    'i',
    'u',
    's',
    'em',
    'strong',
    'span',
    'div',
    'ul',
    'ol',
    'li',
    'a',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'blockquote',
    'pre',
    'code'
]

const ALLOWED_URI = /^(?:(?:https?|mailto):|(?!(?:\s*[a-z](?:[a-z0-9+.-]|\s)*:|\s*[/\\]{2})))/i

export function sanitizeRichTextHtml(html: string | null | undefined): string {
    if (!html) return ''
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS,
        ALLOWED_ATTR: ['class', 'href'],
        ALLOWED_URI_REGEXP: ALLOWED_URI,
        ALLOW_ARIA_ATTR: false,
        ALLOW_DATA_ATTR: false
    })
}
