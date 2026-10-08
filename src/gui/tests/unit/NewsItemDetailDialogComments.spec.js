import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'
import { Action } from '@/types/actions'

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({ checkPermission: () => true })
}))

/**
 * The comment of an aggregate saves itself once the user stops typing (issue #1753). The save
 * makes the list refresh, and that refresh hands the dialog the comment as it was saved - older
 * than what may have been typed since - so the dialog must keep the draft, and nothing may be
 * lost when the editor is left, the dialog closed or another item opened in between.
 */

const VDialogStub = {
    name: 'VDialog',
    template: '<div><slot /></div>'
}

const EditorStub = {
    name: 'RichTextEditor',
    props: ['modelValue', 'readonly'],
    emits: ['update:modelValue', 'blur'],
    template: '<div class="editor" />'
}

const aggregate = (id, comments = '') => ({ id, title: `Item ${id}`, comments, news_items: [{ id: id * 10 }] })

let wrapper = null

const openDialog = async (item) => {
    wrapper = mountWithPlugins(NewsItemDetailDialog, {
        global: {
            stubs: {
                VDialog: VDialogStub,
                RichTextEditor: EditorStub,
                AssessItemActions: true,
                NewsItemAttribute: true,
                NewsItemSourcePane: true
            }
        }
    })
    await wrapper.setProps({ modelValue: true, newsItem: item })
    return wrapper
}

const editor = () => wrapper.findComponent({ name: 'RichTextEditor' })
const type = (html) => editor().vm.$emit('update:modelValue', html)
const commentActions = () =>
    (wrapper.emitted('action') || []).map(([payload]) => payload).filter((payload) => payload.action === Action.COMMENT)

beforeEach(() => {
    vi.useFakeTimers()
})

afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    vi.useRealTimers()
})

describe('NewsItemDetailDialog comment auto-save', () => {
    it('saves once, after the user stops typing', async () => {
        await openDialog(aggregate(8, '<p>Old</p>'))
        expect(editor().props('modelValue')).toBe('<p>Old</p>')

        type('<p>Old a</p>')
        vi.advanceTimersByTime(1000)
        type('<p>Old ab</p>')
        vi.advanceTimersByTime(1999)
        expect(commentActions()).toHaveLength(0)

        vi.advanceTimersByTime(1)
        expect(commentActions()).toHaveLength(1)
        expect(commentActions()[0]).toMatchObject({ comment: '<p>Old ab</p>', newsItem: { id: 8 } })
    })

    it('keeps a draft typed after the save when the refresh brings the saved comment back', async () => {
        await openDialog(aggregate(8))

        type('<p>First</p>')
        vi.advanceTimersByTime(2000)
        type('<p>First second</p>')
        await wrapper.setProps({ newsItem: aggregate(8, '<p>First</p>') })

        expect(editor().props('modelValue')).toBe('<p>First second</p>')
        vi.advanceTimersByTime(2000)
        expect(commentActions().map((payload) => payload.comment)).toEqual(['<p>First</p>', '<p>First second</p>'])
    })

    it('takes a changed comment from the server while there is no draft', async () => {
        await openDialog(aggregate(8, '<p>Old</p>'))

        await wrapper.setProps({ newsItem: aggregate(8, '<p>Changed elsewhere</p>') })

        expect(editor().props('modelValue')).toBe('<p>Changed elsewhere</p>')
    })

    it('saves at once when the editor loses focus, and only once', async () => {
        await openDialog(aggregate(8))

        type('<p>Typed</p>')
        editor().vm.$emit('blur')
        expect(commentActions()).toHaveLength(1)

        vi.advanceTimersByTime(5000)
        editor().vm.$emit('blur')
        expect(commentActions()).toHaveLength(1)
    })

    it('saves at once when the dialog is closed', async () => {
        await openDialog(aggregate(8))

        type('<p>Typed</p>')
        await wrapper.setProps({ modelValue: false })

        expect(commentActions()).toHaveLength(1)
        expect(commentActions()[0]).toMatchObject({ comment: '<p>Typed</p>', newsItem: { id: 8 } })
    })

    it('saves the draft to its own item when another item is opened', async () => {
        await openDialog(aggregate(8))

        type('<p>For item 8</p>')
        await wrapper.setProps({ newsItem: aggregate(9, '<p>Item 9 comment</p>') })

        expect(commentActions()).toHaveLength(1)
        expect(commentActions()[0]).toMatchObject({ comment: '<p>For item 8</p>', newsItem: { id: 8 } })
        expect(editor().props('modelValue')).toBe('<p>Item 9 comment</p>')
        vi.advanceTimersByTime(5000)
        expect(commentActions()).toHaveLength(1)
    })
})
