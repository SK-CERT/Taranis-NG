import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import ToolbarFilterAssess from '@/components/assess/ToolbarFilterAssess.vue'

vi.mock('vue-router', () => ({
    useRoute: () => ({ query: {} })
}))

const BaseToolbarFilterStub = {
    name: 'BaseToolbarFilter',
    props: ['initialFilter'],
    emits: ['update-filter', 'add-new'],
    template: `
        <div>
            <slot name="custom-filters" :filter="initialFilter" />
            <slot name="sort-buttons" :filter="initialFilter" :toggle-date-sort="() => {}" />
            <slot name="addbutton" />
        </div>
    `
}

const mountToolbar = (): VueWrapper =>
    mountWithPlugins(ToolbarFilterAssess, {
        global: {
            stubs: {
                BaseToolbarFilter: BaseToolbarFilterStub,
                ToolbarGroup: true
            }
        }
    })

const latestFilter = (wrapper: VueWrapper): Record<string, unknown> => {
    const filters = wrapper.emitted('update-filter')
    expect(filters).toBeDefined()
    return filters!.at(-1)![0] as Record<string, unknown>
}

const clickPreference = async (wrapper: VueWrapper, title: string): Promise<void> => {
    const button = wrapper.find(`[title="${title}"]`)
    expect(button.exists()).toBe(true)
    await button.trigger('click')
}

describe('ToolbarFilterAssess display preferences', () => {
    beforeEach(() => {
        localStorage.clear()
    })

    it('restores legacy visibility keys and the Vue 3 compact preference on mount', () => {
        localStorage.setItem('review-hide', 'true')
        localStorage.setItem('source-link-hide', 'true')
        localStorage.setItem('word-list-hide', 'true')
        localStorage.setItem('taranis.assess.compact-mode', 'true')

        const filter = latestFilter(mountToolbar())

        expect(filter).toMatchObject({
            hide_reviews: true,
            hide_source_links: true,
            highlight_wordlist: false,
            compact_mode: true
        })
    })

    it('retains the legacy default of visible word-list highlighting', () => {
        const filter = latestFilter(mountToolbar())

        expect(filter).toMatchObject({
            hide_reviews: false,
            hide_source_links: false,
            highlight_wordlist: true,
            compact_mode: false
        })
    })

    it('persists each change immediately using backward-compatible keys', async () => {
        const wrapper = mountToolbar()

        await clickPreference(wrapper, 'Hide reviews on news items')
        await clickPreference(wrapper, 'Hide source links on news items')
        await clickPreference(wrapper, 'Highlight words using word lists')
        await clickPreference(wrapper, 'Toggle compact mode')

        expect(localStorage.getItem('review-hide')).toBe('true')
        expect(localStorage.getItem('source-link-hide')).toBe('true')
        expect(localStorage.getItem('word-list-hide')).toBe('true')
        expect(localStorage.getItem('taranis.assess.compact-mode')).toBe('true')
        expect(latestFilter(wrapper)).toMatchObject({
            hide_reviews: true,
            hide_source_links: true,
            highlight_wordlist: false,
            compact_mode: true
        })
    })

    it('restores changes after the toolbar is remounted', async () => {
        const firstMount = mountToolbar()
        await clickPreference(firstMount, 'Hide reviews on news items')
        await clickPreference(firstMount, 'Toggle compact mode')
        firstMount.unmount()

        expect(latestFilter(mountToolbar())).toMatchObject({
            hide_reviews: true,
            compact_mode: true
        })
    })

    it('falls back safely when stored values are malformed', () => {
        localStorage.setItem('review-hide', 'yes')
        localStorage.setItem('source-link-hide', '1')
        localStorage.setItem('word-list-hide', 'hidden')
        localStorage.setItem('taranis.assess.compact-mode', '{bad json')

        expect(latestFilter(mountToolbar())).toMatchObject({
            hide_reviews: false,
            hide_source_links: false,
            highlight_wordlist: true,
            compact_mode: false
        })
    })
})
