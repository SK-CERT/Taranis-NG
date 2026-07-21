import { describe, it, expect, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import AssessItemActions from '@/components/assess/AssessItemActions.vue'
import { ICONS } from '@/config/ui-constants'

/**
 * A vote is coloured by who cast it: warning if it was you, primary if it was a colleague. The
 * item carries your own vote (me_like / me_dislike) and the team's totals (likes / dislikes), so a
 * vote that is counted but is not yours belongs to someone else.
 */

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

const mountActions = (item) =>
    mountWithPlugins(AssessItemActions, {
        props: { item, showCounts: true },
        global: { stubs: { ConfirmationDialog: true, ActionButton: true } }
    })

/** The like and dislike buttons, in template order. Vuetify renders the icon name as a class. */
const voteIcon = (wrapper, index) => wrapper.findAllComponents({ name: 'VIcon' })[index]

const likeIcon = (wrapper) => voteIcon(wrapper, 0)
const dislikeIcon = (wrapper) => voteIcon(wrapper, 1)

describe('AssessItemActions vote colours', () => {
    it('shows nobody voting as an uncoloured outline', () => {
        const wrapper = mountActions({ id: 1, likes: 0, dislikes: 0, me_like: false, me_dislike: false })

        try {
            expect(likeIcon(wrapper).props('color')).toBeUndefined()
            expect(likeIcon(wrapper).classes()).toContain(ICONS.LIKE_OUTLINE)
            expect(dislikeIcon(wrapper).props('color')).toBeUndefined()
            expect(dislikeIcon(wrapper).classes()).toContain(ICONS.UNLIKE_OUTLINE)
        } finally {
            wrapper.unmount()
        }
    })

    it('shows your own vote in warning', () => {
        const wrapper = mountActions({ id: 1, likes: 1, dislikes: 0, me_like: true, me_dislike: false })

        try {
            expect(likeIcon(wrapper).props('color')).toBe('warning')
            expect(likeIcon(wrapper).classes()).toContain(ICONS.LIKE)
        } finally {
            wrapper.unmount()
        }
    })

    it("shows a colleague's vote in primary", () => {
        // Counted, but not by us - so somebody else cast it.
        const wrapper = mountActions({ id: 1, likes: 2, dislikes: 1, me_like: false, me_dislike: false })

        try {
            expect(likeIcon(wrapper).props('color')).toBe('primary')
            expect(likeIcon(wrapper).classes()).toContain(ICONS.LIKE)
            expect(dislikeIcon(wrapper).props('color')).toBe('primary')
            expect(dislikeIcon(wrapper).classes()).toContain(ICONS.UNLIKE)
        } finally {
            wrapper.unmount()
        }
    })

    it('keeps your own colour when colleagues voted too', () => {
        const wrapper = mountActions({ id: 1, likes: 5, dislikes: 0, me_like: true, me_dislike: false })

        try {
            expect(likeIcon(wrapper).props('color')).toBe('warning')
        } finally {
            wrapper.unmount()
        }
    })
})

/**
 * The confirmation dialog's own heading asks the question ("...delete following item?"), so its
 * message has to name the item - a second generic sentence told the user nothing about what they
 * were about to delete.
 */
describe('AssessItemActions delete confirmation', () => {
    const confirmationMessage = (wrapper) => wrapper.findComponent({ name: 'ConfirmationDialog' }).props('message')

    it('names the item the user is about to delete', () => {
        const wrapper = mountActions({ id: 1, title: 'Critical vulnerability in OpenSSL' })

        try {
            expect(confirmationMessage(wrapper)).toBe('Critical vulnerability in OpenSSL')
        } finally {
            wrapper.unmount()
        }
    })

    it('falls back to the source data title when the item carries none', () => {
        const wrapper = mountActions({ id: 1, news_items: [{ news_item_data: { title: 'Reported by the collector' } }] })

        try {
            expect(confirmationMessage(wrapper)).toBe('Reported by the collector')
        } finally {
            wrapper.unmount()
        }
    })

    it('falls back to an empty message rather than rendering undefined', () => {
        const wrapper = mountActions({ id: 1 })

        try {
            expect(confirmationMessage(wrapper)).toBe('')
        } finally {
            wrapper.unmount()
        }
    })
})
