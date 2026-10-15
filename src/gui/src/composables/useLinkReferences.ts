import { computed, inject, provide, type ComputedRef, type InjectionKey } from 'vue'
import { citedKeys, type CitableLink } from '@/utils/linkReferences'

/**
 * What a form shares with its link list and its citing fields: which links can be cited, and
 * how often each is. The report item dialog provides it; outside one (e.g. a read-only
 * vulnerability detail) `useLinkReferences()` returns a disabled context, so the fields show
 * no cite controls.
 */
export type LinkReferenceContext = {
    /** False when no form provides links: cite controls are hidden. */
    enabled: boolean
    /** The links the form's text can cite, numbered. */
    links: ComputedRef<CitableLink[]>
    /** The link a key stands for, if it still exists. */
    resolve: (key: string) => CitableLink | undefined
    /** How many citations of the key the form's text holds. */
    citationCount: (key: string) => number
    /** Source URLs of the news items attached to the form, offered as new links. */
    newsItemLinks: ComputedRef<string[]>
}

const LINK_REFERENCES: InjectionKey<LinkReferenceContext> = Symbol('link-references')

const DISABLED: LinkReferenceContext = {
    enabled: false,
    links: computed(() => []),
    resolve: () => undefined,
    citationCount: () => 0,
    newsItemLinks: computed(() => [])
}

/**
 * Build a context from the form's links and the texts that may cite them.
 *
 * @param links The citable links, numbered (see numberLinks).
 * @param texts Every citing text of the form.
 * @param newsItemLinks Source URLs of attached news items.
 */
export function createLinkReferences(
    links: ComputedRef<CitableLink[]>,
    texts: ComputedRef<unknown[]>,
    newsItemLinks: ComputedRef<string[]> = computed(() => [])
): LinkReferenceContext {
    const byKey = computed(() => new Map(links.value.map((link) => [link.key, link])))
    const counts = computed(() => {
        const result = new Map<string, number>()
        for (const text of texts.value) {
            for (const key of citedKeys(text)) {
                result.set(key, (result.get(key) ?? 0) + 1)
            }
        }
        return result
    })
    return {
        enabled: true,
        links,
        resolve: (key) => byKey.value.get(key),
        citationCount: (key) => counts.value.get(key) ?? 0,
        newsItemLinks
    }
}

export function provideLinkReferences(context: LinkReferenceContext): void {
    provide(LINK_REFERENCES, context)
}

export function useLinkReferences(): LinkReferenceContext {
    return inject(LINK_REFERENCES, DISABLED)
}
