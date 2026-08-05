// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { sanitizeRichTextHtml } from '@/utils/sanitizeRichTextHtml'

const parse = (html: string): HTMLDivElement => {
    const container = document.createElement('div')
    container.innerHTML = html
    return container
}

describe('sanitizeRichTextHtml', () => {
    it.each([null, undefined, ''])('returns empty HTML for %j', (html) => {
        expect(sanitizeRichTextHtml(html)).toBe('')
    })

    it.each(['JaVaScRiPt:alert(1)', '  javascript:alert(1)', '\njavascript:alert(1)'])('removes unsafe link URL %j', (href) => {
        const link = parse(sanitizeRichTextHtml(`<a href="${href}">unsafe</a>`)).querySelector('a')
        expect(link?.hasAttribute('href')).toBe(false)
    })

    it('sanitizes children retained from a rejected element', () => {
        const result = parse(
            sanitizeRichTextHtml(
                '<unsupported><a href="javascript:alert(1)"><span onclick="alert(2)" style="color:red">Keep me</span></a></unsupported>'
            )
        )
        const link = result.querySelector('a')
        const span = result.querySelector('span')

        expect(result.textContent).toContain('Keep me')
        expect(result.querySelector('unsupported')).toBeNull()
        expect(link?.hasAttribute('href')).toBe(false)
        expect(span?.hasAttribute('onclick')).toBe(false)
        expect(span?.hasAttribute('style')).toBe(false)
    })

    it('allows only HTTP, HTTPS, mailto, and relative links', () => {
        const result = parse(
            sanitizeRichTextHtml(
                '<a href="https://example.com">https</a><a href="mailto:user@example.com">mail</a><a href="/relative">root-relative</a><a href="reports/123.html">plain-relative</a><a href="ftp://example.com/file">ftp</a><a href="//evil.example">protocol-relative</a><a href="java&#x09;script:alert(1)">obfuscated-script</a>'
            )
        )
        const links = result.querySelectorAll('a')

        expect(links[0]?.getAttribute('href')).toBe('https://example.com')
        expect(links[1]?.getAttribute('href')).toBe('mailto:user@example.com')
        expect(links[2]?.getAttribute('href')).toBe('/relative')
        expect(links[3]?.getAttribute('href')).toBe('reports/123.html')
        expect(links[4]?.hasAttribute('href')).toBe(false)
        expect(links[5]?.hasAttribute('href')).toBe(false)
        expect(links[6]?.hasAttribute('href')).toBe(false)
    })

    it('removes browsing-context attributes from supplied links', () => {
        const link = parse(sanitizeRichTextHtml('<a href="https://example.com" target="_blank" rel="opener">external</a>')).querySelector('a')

        expect(link?.hasAttribute('target')).toBe(false)
        expect(link?.hasAttribute('rel')).toBe(false)
    })

    it('preserves editor classes while removing inline styles', () => {
        const paragraph = parse(sanitizeRichTextHtml('<p class="ql-align-center" style="position:fixed">Text</p>')).querySelector('p')

        expect(paragraph?.getAttribute('class')).toBe('ql-align-center')
        expect(paragraph?.hasAttribute('style')).toBe(false)
    })
})
