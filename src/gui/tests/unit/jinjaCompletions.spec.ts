import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { FILTERS, insideJinja, jinjaCompletions } from '@/utils/jinjaCompletions'

const product = { kind: 'product' as const }
const item = { kind: 'item' as const, attrKeys: ['cve', 'cvss', 'affected_systems'] }
const labels = (result: ReturnType<typeof jinjaCompletions>) => result?.options.map((option) => option.label) ?? null

describe('jinjaCompletions', () => {
    it('offers nothing in the HTML around the Jinja', () => {
        expect(insideJinja('<p class="x">')).toBe(false)
        expect(insideJinja('{{ product.title }} <p>')).toBe(false)
        expect(jinjaCompletions('<div class="pro', product)).toBeNull()
    })

    it('offers the context variables of the kind of template', () => {
        expect(labels(jinjaCompletions('{{ ', product))).toEqual(expect.arrayContaining(['product', 'render_item', 'visible_links']))
        expect(labels(jinjaCompletions('{{ ', product))).not.toContain('item')
        expect(labels(jinjaCompletions('{%- if it', item))).toEqual(expect.arrayContaining(['item', 'index', 'product']))
        expect(jinjaCompletions('{%- if it', item)?.from).toBe('{%- if '.length)
    })

    it('offers the fields after a dot, and the type’s attribute keys after attrs', () => {
        const fields = jinjaCompletions('{{ product.max_c', product)
        expect(labels(fields)).toEqual(expect.arrayContaining(['max_cvss', 'max_tlp', 'report_items']))
        expect(fields?.from).toBe('{{ product.'.length)
        expect(labels(jinjaCompletions('{{ product.product_preset.', product))).toEqual(['id', 'title'])
        expect(labels(jinjaCompletions('{{ item.attrs.', item))).toEqual(['cve', 'cvss', 'affected_systems'])
        expect(labels(jinjaCompletions('{{ item.attrs_display.cv', item))).toEqual(['cve', 'cvss', 'affected_systems'])
        expect(jinjaCompletions('{{ item.attrs.', { kind: 'item' })).toBeNull()
        expect(jinjaCompletions('{{ unknown.', product)).toBeNull()
    })

    it('offers the filters after a bar, with or without a space', () => {
        for (const before of ['{{ item.name | ', '{{ item.name|cl']) {
            const names = labels(jinjaCompletions(before, item))
            expect(names).toEqual(expect.arrayContaining(['clean', 'link_refs', 'join', 'default']))
        }
        expect(jinjaCompletions('{{ x | link_r', item)?.options.find((option) => option.label === 'link_refs')?.detail).toContain(
            'link_refs(links)'
        )
    })

    it('offers the statements after {%, and the built-ins to extend or import', () => {
        expect(labels(jinjaCompletions('{%- ', product))).toEqual(expect.arrayContaining(['if', 'for', 'block', 'extends', 'endblock']))
        expect(labels(jinjaCompletions('{% extends "builtin/pr', product))).toEqual(expect.arrayContaining(['builtin/product_base.html']))
        expect(jinjaCompletions('{% extends "builtin/pr', product)?.from).toBe('{% extends "'.length)
        expect(labels(jinjaCompletions("{%- import '", item))).toContain('builtin/_macros.html')
    })

    it('stays quiet inside a word or a string within the expression', () => {
        expect(jinjaCompletions('{{ t("vulner', item)).toBeNull()
    })

    it('knows exactly the filters public-web registers', () => {
        const shared = readFileSync(resolve(__dirname, '../../../shared/shared/public_web_templates/__init__.py'), 'utf-8')
        const block = /FILTER_NAMES = \(([\s\S]*?)\)/.exec(shared)?.[1] ?? ''
        const names = [...block.matchAll(/"([a-z_]+)"/g)].map((match) => match[1])
        expect(names.length).toBeGreaterThan(10)
        expect([...FILTERS]).toEqual(names)
    })
})
