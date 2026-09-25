/**
 * Contract for translation keys that travel as component props.
 *
 * `@intlify/vue-i18n/no-missing-keys` only sees keys written directly into a
 * `t()` / `$t()` / `<i18n-t keypath>` call. A component like AddNewButton instead
 * takes the key as a prop and translates it internally:
 *
 *     <AddNewButton label="asset.add" />        →  t(props.label)
 *
 * To eslint that is an ordinary string attribute, so a typo there reaches runtime,
 * where vue-i18n renders the key verbatim. This spec closes that gap by resolving
 * every literal key prop against the English catalogue.
 *
 * The components and prop names are derived from the source rather than listed, so
 * a new key prop is covered the day it is written.
 */
import { describe, expect, it } from 'vitest'
import en from '@/i18n/en.json'

// Vite resolves this at transform time, so the suite reads the same sources the app
// builds from without depending on the process working directory.
const vueSources = import.meta.glob('/src/**/*.vue', { query: '?raw', import: 'default', eager: true })

const vueFiles = Object.entries(vueSources).map(([path, source]) => ({
    name: path.split('/').pop().replace('.vue', ''),
    path,
    source
}))

const toKebabCase = (value) => value.replace(/[A-Z]/gu, (letter) => `-${letter.toLowerCase()}`)

const resolvesInEnglish = (key) => typeof key.split('.').reduce((value, segment) => value?.[segment], en) === 'string'

// Vue's own special attributes are never translation keys. `key` matters most: it sits
// on virtually every v-for, and an index signature such as `[key: string]: unknown` in a
// props type is enough to make it look like a declared prop.
const RESERVED_ATTRIBUTES = new Set(['key', 'ref', 'is', 'slot'])

/** The `defineProps` region of a component, used to confirm an identifier really is a prop. */
const propsRegion = (source) => {
    const start = source.indexOf('defineProps')
    return start === -1 ? '' : source.slice(start, start + 1200)
}

/**
 * Props whose value is handed straight to `t()`, i.e. `t(props.label)` or `{{ t(titleKey) }}`.
 *
 * The leading lookbehind keeps the call distinct from any identifier that merely ends
 * in `t` — without it `setTimeout(searchTimer)` and `clearTimeout(...)` read as `t(...)`
 * calls and turn ordinary props into supposed translation keys. Requiring the
 * identifier to appear in `defineProps` then keeps local variables out.
 */
const keyPropsOf = ({ source }) => {
    const region = propsRegion(source)
    const names = new Set()
    for (const [, identifier] of source.matchAll(/(?<![\w$])\$?t\(\s*(?:props\.)?([A-Za-z_$][\w$]*)\s*\)/gu)) {
        if (RESERVED_ATTRIBUTES.has(identifier)) continue
        if (new RegExp(`\\b${identifier}\\b`, 'u').test(region)) names.add(identifier)
    }
    return names
}

/** Open tags for `component` in `source`, returning each tag's attribute text. */
const openTagsFor = (source, component) => {
    const pattern = new RegExp(`<${component}(\\s(?:[^>"']|"[^"]*"|'[^']*')*)?/?>`, 'gu')
    return [...source.matchAll(pattern)].map((match) => match[1] ?? '')
}

/** A literal value for `prop`, from either `prop="x"` or `:prop="'x'"`. Dynamic bindings yield null. */
const literalAttributeValue = (attributes, prop) => {
    for (const name of new Set([prop, toKebabCase(prop)])) {
        const staticMatch = attributes.match(new RegExp(`(?:^|\\s)${name}\\s*=\\s*"([^"]*)"`, 'u'))
        if (staticMatch) return staticMatch[1]

        const boundMatch = attributes.match(new RegExp(`(?:^|\\s)(?::|v-bind:)${name}\\s*=\\s*"\\s*'([^']*)'\\s*"`, 'u'))
        if (boundMatch) return boundMatch[1]
    }
    return null
}

// component name -> Set of props that carry a translation key
const keyPropsByComponent = new Map()
for (const file of vueFiles) {
    const props = keyPropsOf(file)
    if (props.size > 0) keyPropsByComponent.set(file.name, props)
}

// A prop forwarded verbatim into another component's key prop (`:label="addButtonLabel"`)
// is a key prop too. Repeat to a fixpoint so a chain of wrappers is covered.
for (let changed = true; changed;) {
    changed = false
    for (const file of vueFiles) {
        const region = propsRegion(file.source)
        for (const [component, props] of keyPropsByComponent) {
            if (component === file.name) continue
            for (const attributes of openTagsFor(file.source, component)) {
                for (const prop of props) {
                    for (const name of new Set([prop, toKebabCase(prop)])) {
                        const forwarded = attributes.match(
                            new RegExp(`(?:^|\\s)(?::|v-bind:)${name}\\s*=\\s*"\\s*([A-Za-z_$][\\w$]*)\\s*"`, 'u')
                        )
                        if (!forwarded || !new RegExp(`\\b${forwarded[1]}\\b`, 'u').test(region)) continue

                        const existing = keyPropsByComponent.get(file.name) ?? new Set()
                        if (existing.has(forwarded[1])) continue
                        existing.add(forwarded[1])
                        keyPropsByComponent.set(file.name, existing)
                        changed = true
                    }
                }
            }
        }
    }
}

describe('translation keys passed as component props', () => {
    it('discovers the components that translate a prop', () => {
        // Canary: if the derivation above silently stops matching, every other
        // assertion here would pass vacuously.
        const discovered = Object.fromEntries([...keyPropsByComponent].map(([name, props]) => [name, [...props].sort()]))

        expect(discovered.AddNewButton).toContain('label')
        expect(discovered.ConfirmationDialog).toEqual(expect.arrayContaining(['confirmLabelKey', 'titleKey']))
        expect(discovered.GroupNavList).toContain('titleKey')
        // Reached only through the forwarding pass, so it also proves that ran.
        expect(discovered.BaseToolbarFilter).toContain('addButtonLabel')
    })

    it('resolves every literal key prop at its usage site', () => {
        const unresolved = []

        for (const file of vueFiles) {
            for (const [component, props] of keyPropsByComponent) {
                for (const attributes of openTagsFor(file.source, component)) {
                    for (const prop of props) {
                        const key = literalAttributeValue(attributes, prop)
                        if (key !== null && !resolvesInEnglish(key)) {
                            unresolved.push(`${file.name}.vue: <${component} ${toKebabCase(prop)}="${key}">`)
                        }
                    }
                }
            }
        }

        expect(
            unresolved,
            `Key props with no message in en.json (${unresolved.length}):\n${unresolved.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })

    it('resolves the default value of every key prop', () => {
        const unresolved = []

        for (const file of vueFiles) {
            const props = keyPropsByComponent.get(file.name)
            if (!props) continue

            const region = propsRegion(file.source)
            for (const prop of props) {
                // `default: 'x'` for the object form, `{ titleKey: 'x' }` for withDefaults.
                const declared =
                    region.match(new RegExp(`${prop}\\s*:\\s*\\{[^}]*default\\s*:\\s*'([^']*)'`, 'u')) ??
                    region.match(new RegExp(`${prop}\\s*:\\s*'([^']*)'`, 'u'))

                // An empty default is the "no value supplied" sentinel (BaseToolbarFilter
                // renders no heading for it), not a key that should resolve.
                if (declared && declared[1] !== '' && !resolvesInEnglish(declared[1])) {
                    unresolved.push(`${file.name}.vue: ${prop} defaults to "${declared[1]}"`)
                }
            }
        }

        expect(
            unresolved,
            `Key prop defaults with no message in en.json (${unresolved.length}):\n${unresolved.map((entry) => `  - ${entry}`).join('\n')}`
        ).toEqual([])
    })
})
