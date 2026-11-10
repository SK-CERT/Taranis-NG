import { describe, it, expect, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { mountWithPlugins } from '../helpers/mount-helpers'
import CodeEditor from '@/components/common/CodeEditor.vue'

const mounted = []

function mountEditor(props = {}) {
    const wrapper = mountWithPlugins(CodeEditor, {
        props: { 'modelValue': '', 'onUpdate:modelValue': (value) => wrapper.setProps({ modelValue: value }), ...props },
        attachTo: document.body
    })
    mounted.push(wrapper)
    return wrapper
}

/** Every highlighted token with its classes, in order. */
const tokens = (wrapper) => wrapper.findAll('.pce-line .token').map((token) => [token.text(), token.classes()])
const classesOf = (wrapper, text) =>
    tokens(wrapper)
        .filter(([token]) => token === text)
        .map(([, classes]) => classes)

describe('CodeEditor', () => {
    afterEach(() => {
        while (mounted.length) mounted.pop().unmount()
    })

    it('highlights the Jinja tags, expressions and filters, and the HTML around them', () => {
        const wrapper = mountEditor({
            modelValue: '{% for item in product.body_items %}<p class="x">{{ item.name | clean }}</p>{% endfor %}{# note #}'
        })

        expect(classesOf(wrapper, 'for')[0]).toContain('keyword')
        expect(classesOf(wrapper, 'endfor')[0]).toContain('keyword')
        expect(classesOf(wrapper, 'clean')[0]).toContain('filter')
        expect(classesOf(wrapper, 'item')[0]).toContain('variable')
        expect(classesOf(wrapper, '{{')[0]).toContain('delimiter')
        expect(classesOf(wrapper, '{%')[0]).toContain('delimiter')
        expect(classesOf(wrapper, '{# note #}').some((classes) => classes.includes('comment'))).toBe(true)
        expect(wrapper.findAll('.token.tag').length).toBeGreaterThan(0)
        expect(wrapper.findAll('.token.attr-name').map((name) => name.text())).toEqual(['class'])
        // The Jinja parts are marked as such, so they keep their colours inside HTML too.
        expect(wrapper.findAll('.language-django').length).toBe(4)
    })

    it('highlights an expression that trims whitespace ({{- ... -}}) as any other', () => {
        const wrapper = mountEditor({ modelValue: '<p>{{- product.lead | clean -}}</p>\n<a href="{{ link | safe_url }}">x</a>' })

        expect(classesOf(wrapper, '{{-')[0]).toContain('delimiter')
        expect(classesOf(wrapper, '-}}')[0]).toContain('delimiter')
        expect(classesOf(wrapper, 'product')[0]).toContain('variable')
        expect(classesOf(wrapper, 'clean')[0]).toContain('filter')
        // Inside an attribute value as well.
        expect(classesOf(wrapper, 'safe_url')[0]).toContain('filter')
    })

    it('reports what is typed, and shows a text set from outside', async () => {
        const wrapper = mountEditor({ modelValue: '<p></p>', ariaLabel: 'Template (Jinja)' })
        const textarea = wrapper.find('textarea')

        textarea.element.value = '<p>{{ product.title }}</p>'
        await textarea.trigger('input')
        expect(wrapper.props('modelValue')).toBe('<p>{{ product.title }}</p>')

        await wrapper.setProps({ modelValue: '{% extends "builtin/product_base.html" %}' })
        expect(textarea.element.value).toBe('{% extends "builtin/product_base.html" %}')
        expect(classesOf(wrapper, 'extends')[0]).toContain('keyword')
        expect(textarea.attributes('aria-label')).toBe('Template (Jinja)')
    })

    it('cannot be changed while read-only or disabled', async () => {
        const wrapper = mountEditor({ modelValue: '<p></p>', readonly: true })
        const textarea = wrapper.find('textarea')
        const typing = () => {
            const event = new window.InputEvent('beforeinput', { cancelable: true, inputType: 'insertText', data: 'x' })
            textarea.element.dispatchEvent(event)
            return event.defaultPrevented
        }
        expect(textarea.attributes('aria-readonly')).toBe('true')
        expect(typing()).toBe(true)

        await wrapper.setProps({ readonly: false })
        await nextTick()
        expect(textarea.attributes('aria-readonly')).toBe('false')
        expect(typing()).toBe(false)

        await wrapper.setProps({ disabled: true })
        await nextTick()
        expect(textarea.attributes('aria-readonly')).toBe('true')
        expect(wrapper.classes()).toContain('code-editor--disabled')
    })
})
