// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { sanitizeNewsItemHtml } from '@/utils/sanitizeNewsItemHtml'

describe('sanitizeNewsItemHtml', () => {
    it.each([null, undefined, ''])('returns empty HTML for %j', (content) => {
        expect(sanitizeNewsItemHtml(content)).toBe('')
    })

    it('removes executable URLs, event handlers and unsupported elements', () => {
        const dirty = `
            <p onclick="alert(1)">
                News <a href="JaVaScRiPt:alert(2)" onmouseover="alert(3)">details</a>
                <img src=x onerror="alert(4)">
                <script>alert(5)</script>
            </p>
        `

        const clean = sanitizeNewsItemHtml(dirty)
        const document = new DOMParser().parseFromString(clean, 'text/html')
        const link = document.querySelector('a')

        expect(document.querySelector('p')?.hasAttribute('onclick')).toBe(false)
        expect(link?.hasAttribute('href')).toBe(false)
        expect(link?.hasAttribute('onmouseover')).toBe(false)
        expect(document.querySelector('img')).toBeNull()
        expect(document.querySelector('script')).toBeNull()
        expect(clean).not.toContain('alert(5)')
    })

    it('keeps the supported article structure and safe links', () => {
        const clean = sanitizeNewsItemHtml(`
            <h2>Security update</h2>
            <p>Install the <strong>latest version</strong>.</p>
            <ul><li><code>apt update</code></li></ul>
            <a href="https://example.com/advisory">Advisory</a>
            <a href="mailto:security@example.com">Contact</a>
            <a href="/local/advisory">Local copy</a>
            <a href="advisories/123.html">Relative copy</a>
        `)
        const document = new DOMParser().parseFromString(clean, 'text/html')

        expect(document.querySelector('h2')?.textContent).toBe('Security update')
        expect(document.querySelector('strong')?.textContent).toBe('latest version')
        expect(document.querySelector('code')?.textContent).toBe('apt update')
        expect(Array.from(document.querySelectorAll('a'), (link) => link.getAttribute('href'))).toEqual([
            'https://example.com/advisory',
            'mailto:security@example.com',
            '/local/advisory',
            'advisories/123.html'
        ])
    })

    it('rejects data and protocol-relative links', () => {
        const clean = sanitizeNewsItemHtml(`
            <a href="data:text/html,alert(1)">data</a>
            <a href="//evil.example/phishing">protocol relative</a>
            <a href="&#92;&#92;evil.example/phishing">backslash protocol relative</a>
            <a href="java&#x09;script:alert(1)">control-obfuscated script</a>
        `)
        const document = new DOMParser().parseFromString(clean, 'text/html')

        expect(Array.from(document.querySelectorAll('a'), (link) => link.hasAttribute('href'))).toEqual([false, false, false, false])
    })
})
