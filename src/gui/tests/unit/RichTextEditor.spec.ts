import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'
import type { Editor } from '@tiptap/vue-3'
import { mountWithPlugins } from '../helpers/mount-helpers'
import RichTextEditor from '@/components/common/RichTextEditor.vue'
import { useSettingsStore } from '@/stores/settings'

type EditorElement = HTMLElement & { editor: Editor }

let wrapper: VueWrapper | null = null

const mountEditor = async (props: Record<string, unknown> = {}): Promise<VueWrapper> => {
    wrapper = mountWithPlugins(RichTextEditor, { props: { modelValue: '<p>Hello</p>', ...props }, attachTo: document.body })
    await flushPromises()
    return wrapper
}

const editorOf = (target: VueWrapper): Editor => (target.find('.ProseMirror').element as EditorElement).editor

afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    vi.restoreAllMocks()
})

describe('RichTextEditor', () => {
    it('renders the model value', async () => {
        const target = await mountEditor({ modelValue: '<p><strong>Hello</strong> world</p>' })

        expect(target.find('.ProseMirror').html()).toContain('<strong>Hello</strong> world')
    })

    it('emits HTML as the text changes, and an empty string once it is empty', async () => {
        const target = await mountEditor()
        const editor = editorOf(target)

        editor.commands.insertContentAt(editor.state.doc.content.size - 1, ' there')
        expect(target.emitted('update:modelValue')?.at(-1)).toEqual(['<p>Hello there</p>'])

        editor.commands.clearContent(true)
        expect(target.emitted('update:modelValue')?.at(-1)).toEqual([''])
    })

    it('loads a new model value without reporting it back as a change', async () => {
        const target = await mountEditor()

        await target.setProps({ modelValue: '<ul><li><p>Item</p></li></ul>' })

        expect(editorOf(target).getHTML()).toBe('<ul><li><p>Item</p></li></ul>')
        expect(target.emitted('update:modelValue')).toBeUndefined()
    })

    it('turns the non-breaking spaces Quill stored into ordinary ones', async () => {
        const target = await mountEditor({ modelValue: '<p>First&nbsp;part</p>' })

        expect(editorOf(target).getHTML()).toBe('<p>First part</p>')
    })

    it('keeps what the user is typing over a model value that arrives meanwhile, and loads it on blur', async () => {
        const target = await mountEditor()
        const editor = editorOf(target)
        editor.view.focus()
        expect(editor.isFocused).toBe(true)

        await target.setProps({ modelValue: '<p>Refreshed</p>' })
        expect(editor.getHTML()).toBe('<p>Hello</p>')

        editor.view.dom.blur()
        await flushPromises()
        expect(target.emitted('blur')).toHaveLength(1)
        expect(editor.getHTML()).toBe('<p>Refreshed</p>')
    })

    it('hides the toolbar and stops editing when read-only', async () => {
        const target = await mountEditor({ readonly: true })

        expect(target.find('[role="toolbar"]').exists()).toBe(false)
        expect(target.find('.ProseMirror').attributes('contenteditable')).toBe('false')

        await target.setProps({ readonly: false })
        expect(target.find('[role="toolbar"]').exists()).toBe(true)
        expect(target.find('.ProseMirror').attributes('contenteditable')).toBe('true')
        expect(target.emitted('update:modelValue')).toBeUndefined()
    })

    it('applies a formatting button to the selection', async () => {
        const target = await mountEditor()
        editorOf(target).commands.selectAll()

        await target.find('[data-test="rich-text-bold"]').trigger('click')

        expect(target.emitted('update:modelValue')?.at(-1)).toEqual(['<p><strong>Hello</strong></p>'])
    })

    it('only links to web and mail addresses', async () => {
        const target = await mountEditor()
        const vm = target.vm as unknown as { linkUrl: string; linkError: string; applyLink: () => void }
        editorOf(target).commands.selectAll()

        vm.linkUrl = 'javascript:alert(1)'
        vm.applyLink()
        expect(vm.linkError).toBe('Enter a web (http, https) or mailto: address')
        expect(target.emitted('update:modelValue')).toBeUndefined()

        vm.linkUrl = 'example.com'
        vm.applyLink()
        expect(target.emitted('update:modelValue')?.at(-1)?.[0]).toContain('href="https://example.com"')
    })

    it('follows the spellcheck setting', async () => {
        const target = await mountEditor()
        expect(target.find('.ProseMirror').attributes('spellcheck')).toBe('true')

        useSettingsStore().spellcheck = false
        await flushPromises()
        expect(target.find('.ProseMirror').attributes('spellcheck')).toBe('false')
    })
})

describe('RichTextEditor links', () => {
    const LINKED = '<p>See <a href="https://example.com/advisory">the advisory</a></p>'

    const clickLink = (target: VueWrapper, init: MouseEventInit = {}): MouseEvent => {
        const event = new MouseEvent('click', { bubbles: true, cancelable: true, button: 0, ...init })
        target.find('.ProseMirror a').element.dispatchEvent(event)
        return event
    }

    it('opens a link on Ctrl+click while the text is editable, and leaves a plain click to the cursor', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null)
        const target = await mountEditor({ modelValue: LINKED })

        expect(clickLink(target).defaultPrevented).toBe(false)
        expect(open).not.toHaveBeenCalled()

        expect(clickLink(target, { ctrlKey: true }).defaultPrevented).toBe(true)
        expect(open).toHaveBeenCalledWith('https://example.com/advisory', '_blank', 'noopener,noreferrer')
    })

    it('opens a link on a plain click in read-only text', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null)
        const target = await mountEditor({ modelValue: LINKED, readonly: true })

        expect(clickLink(target).defaultPrevented).toBe(true)
        expect(open).toHaveBeenCalledWith('https://example.com/advisory', '_blank', 'noopener,noreferrer')
    })

    it('does not open a link to anything but a web or mail address', async () => {
        const open = vi.spyOn(window, 'open').mockReturnValue(null)
        const target = await mountEditor({ modelValue: '<p><a href="/config/users">relative</a></p>', readonly: true })

        clickLink(target)

        expect(open).not.toHaveBeenCalled()
    })

    it('tells how to open a link only while the text is editable', async () => {
        const target = await mountEditor({ modelValue: LINKED })

        expect(target.find('.ProseMirror a [title]').attributes('title')).toBe('Ctrl+click to open the link')

        await target.setProps({ readonly: true })
        expect(target.find('.ProseMirror a [title]').exists()).toBe(false)
    })
})
