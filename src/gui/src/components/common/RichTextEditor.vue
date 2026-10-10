<template>
    <div
        class="rich-text-editor"
        :class="{ 'rich-text-editor--readonly': readonly }"
    >
        <!-- mousedown.prevent keeps the focus (and the selection) in the text while a button is used -->
        <div
            v-if="editor && !readonly"
            class="rich-text-editor__toolbar"
            role="toolbar"
            :aria-label="t('rich_text_editor.toolbar')"
            @mousedown.prevent
        >
            <template
                v-for="(group, groupIndex) in toolGroups"
                :key="groupIndex"
            >
                <v-divider
                    v-if="groupIndex > 0"
                    vertical
                    class="mx-1 my-1"
                />
                <template
                    v-for="tool in group"
                    :key="tool.name"
                >
                    <!-- Before the link menu, not a v-else after it: vue-tsc 3.3.12 loses the v-for
                         variable in whatever follows a component with a scoped slot. -->
                    <v-btn
                        v-if="tool.name !== 'link'"
                        :icon="tool.icon"
                        :title="t(tool.label)"
                        :aria-label="t(tool.label)"
                        :active="isActive(tool)"
                        :disabled="!isEnabled(tool)"
                        :data-test="`rich-text-${tool.name}`"
                        size="small"
                        variant="text"
                        density="comfortable"
                        @click="tool.run?.()"
                    />
                    <v-menu
                        v-else
                        v-model="linkMenu"
                        :close-on-content-click="false"
                        location="bottom start"
                    >
                        <template #activator="{ props: menuProps }">
                            <v-btn
                                v-bind="menuProps"
                                :icon="tool.icon"
                                :title="t(tool.label)"
                                :aria-label="t(tool.label)"
                                :active="isActive(tool)"
                                :data-test="`rich-text-${tool.name}`"
                                size="small"
                                variant="text"
                                density="comfortable"
                            />
                        </template>
                        <v-card min-width="320">
                            <v-card-text class="pb-0">
                                <v-text-field
                                    v-model="linkUrl"
                                    :label="t('rich_text_editor.link_url')"
                                    :error-messages="linkError"
                                    :spellcheck="false"
                                    placeholder="https://"
                                    density="compact"
                                    variant="outlined"
                                    hide-details="auto"
                                    autofocus
                                    data-test="rich-text-link-url"
                                    @keydown.enter.prevent="applyLink"
                                >
                                    <template #append-inner>
                                        <v-btn
                                            icon="mdi-open-in-new"
                                            :title="t('rich_text_editor.open_link')"
                                            :aria-label="t('rich_text_editor.open_link')"
                                            :disabled="!normalizeLink(linkUrl)"
                                            size="x-small"
                                            variant="text"
                                            data-test="rich-text-link-open"
                                            @click="openLink(normalizeLink(linkUrl))"
                                        />
                                    </template>
                                </v-text-field>
                            </v-card-text>
                            <v-card-actions>
                                <v-btn
                                    v-if="editor.isActive('link')"
                                    data-test="rich-text-link-remove"
                                    @click="removeLink"
                                >
                                    {{ t('rich_text_editor.remove_link') }}
                                </v-btn>
                                <v-spacer />
                                <v-btn @click="linkMenu = false">
                                    {{ t('common.cancel') }}
                                </v-btn>
                                <v-btn
                                    color="primary"
                                    variant="flat"
                                    data-test="rich-text-link-apply"
                                    @click="applyLink"
                                >
                                    {{ t('rich_text_editor.apply_link') }}
                                </v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-menu>
                </template>
            </template>
            <template v-if="$slots['toolbar-append']">
                <v-divider
                    vertical
                    class="mx-1 my-1"
                />
                <slot name="toolbar-append" />
            </template>
        </div>
        <div
            class="rich-text-editor__content"
            :style="{ height }"
        >
            <EditorContent
                v-if="editor"
                :editor="editor"
                class="rich-text-editor__document"
            />
        </div>
    </div>
</template>

<script setup lang="ts">
    import { ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { EditorContent, Extension, useEditor } from '@tiptap/vue-3'
    import { Plugin, PluginKey } from '@tiptap/pm/state'
    import { Decoration, DecorationSet } from '@tiptap/pm/view'
    import StarterKit from '@tiptap/starter-kit'
    import { Placeholder } from '@tiptap/extensions'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import { LINK_TOKEN_RE } from '@/utils/linkReferences'

    type Tool = {
        name: string
        icon: string
        label: string
        run?: () => void
        active?: () => boolean
        enabled?: () => boolean
    }

    const props = withDefaults(
        defineProps<{
            modelValue?: string | null
            readonly?: boolean
            placeholder?: string
            height?: string
            /** Links that citations in the text resolve to; null leaves citations unmarked. */
            citations?: Map<string, { number: number; url: string }> | null
        }>(),
        {
            modelValue: '',
            readonly: false,
            placeholder: '',
            height: '250px',
            citations: null
        }
    )

    const emit = defineEmits<{
        (e: 'update:modelValue', value: string): void
        (e: 'focus', event: FocusEvent): void
        (e: 'blur', event: FocusEvent): void
    }>()

    const { t } = useI18n()
    const spellcheck = useSpellcheck()

    // Links are limited to what sanitizeRichTextHtml lets through when the text is displayed.
    const SAFE_LINK = /^(?:https?:\/\/|mailto:)\S+$/i
    const HAS_SCHEME = /^[a-z][a-z0-9+.-]*:/i

    // Quill (the previous editor) stored every space as &nbsp;, which stops the text from ever
    // wrapping. Ordinary spaces render the same, so clean that up as the text is loaded.
    const prepareContent = (html: string | null | undefined): string => (html || '').replace(/&nbsp;|\u00a0/g, ' ')

    const toModelValue = (instance: { isEmpty: boolean; getHTML: () => string }): string => (instance.isEmpty ? '' : instance.getHTML())

    const contentAttributes = (): Record<string, string> => ({ spellcheck: String(spellcheck.value) })

    /** Open a link in a new tab, if it is one the displayed text would allow. */
    const openLink = (href: string | null | undefined): void => {
        if (href && SAFE_LINK.test(href)) {
            window.open(href, '_blank', 'noopener,noreferrer')
        }
    }

    const modifierKey = /Mac|iPhone|iPad/.test(navigator.userAgent) ? '⌘' : 'Ctrl'

    /**
     * Follow links: a plain click in editable text has to place the cursor, so there a link opens
     * on Ctrl/Cmd+click - which its hover title says - and in read-only text on a plain click.
     */
    const LinkOpening = Extension.create({
        name: 'linkOpening',
        addProseMirrorPlugins() {
            const instance = this.editor
            return [
                new Plugin({
                    key: new PluginKey('linkOpening'),
                    props: {
                        handleDOMEvents: {
                            click: (view, event) => {
                                const link = (event.target as Element | null)?.closest('a[href]')
                                if (event.button !== 0 || !link || !view.dom.contains(link)) {
                                    return false
                                }
                                if (view.editable && !event.ctrlKey && !event.metaKey) {
                                    return false
                                }
                                event.preventDefault()
                                openLink(link.getAttribute('href'))
                                return true
                            }
                        },
                        decorations: (state) => {
                            if (!instance.isEditable) {
                                return null
                            }
                            const title = t('rich_text_editor.open_link_hint', { key: modifierKey })
                            const hints: Decoration[] = []
                            state.doc.descendants((node, pos) => {
                                if (node.isText && node.marks.some((mark) => mark.type.name === 'link')) {
                                    hints.push(Decoration.inline(pos, pos + node.nodeSize, { title }))
                                }
                            })
                            return DecorationSet.create(state.doc, hints)
                        }
                    }
                })
            ]
        }
    })

    /**
     * Mark link citations ("[#k3f9a2]"): the number the cited link has follows the token, and its
     * title shows the URL. A citation of a link that no longer exists is flagged.
     */
    const CitationMarks = Extension.create({
        name: 'citationMarks',
        addProseMirrorPlugins() {
            return [
                new Plugin({
                    key: new PluginKey('citationMarks'),
                    props: {
                        decorations: (state) => {
                            const citations = props.citations
                            if (!citations) {
                                return null
                            }
                            const marks: Decoration[] = []
                            state.doc.descendants((node, pos) => {
                                if (!node.isText || !node.text) {
                                    return
                                }
                                for (const match of node.text.matchAll(LINK_TOKEN_RE)) {
                                    const from = pos + (match.index ?? 0)
                                    const to = from + match[0].length
                                    const link = citations.get(match[1] as string)
                                    const number = link ? `[${link.number}]` : '[?]'
                                    marks.push(
                                        Decoration.inline(from, to, {
                                            class: link ? 'rich-text-citation' : 'rich-text-citation rich-text-citation--missing',
                                            title: link ? link.url : t('links.missing_hint')
                                        }),
                                        Decoration.widget(
                                            to,
                                            () => {
                                                const label = document.createElement('span')
                                                label.className = 'rich-text-citation__number'
                                                label.textContent = number
                                                return label
                                            },
                                            { side: 1, key: `${match[1]}:${number}` }
                                        )
                                    )
                                }
                            })
                            return DecorationSet.create(state.doc, marks)
                        }
                    }
                })
            ]
        }
    })

    // The last value this editor emitted or loaded, so its own echo is not taken for a change.
    let knownValue = props.modelValue || ''

    const editor = useEditor({
        content: prepareContent(props.modelValue),
        editable: !props.readonly,
        extensions: [
            StarterKit.configure({
                heading: { levels: [1, 2, 3] },
                // A rule would not survive sanitizeRichTextHtml, and the trailing node appends an
                // empty paragraph to loaded content the user has not touched.
                horizontalRule: false,
                trailingNode: false,
                link: {
                    openOnClick: false,
                    autolink: true,
                    defaultProtocol: 'https'
                }
            }),
            Placeholder.configure({ placeholder: () => props.placeholder }),
            LinkOpening,
            CitationMarks
        ],
        editorProps: { attributes: contentAttributes() },
        // The editor is only created on mount, so pick up a value that changed before then.
        onCreate: () => syncFromModel(),
        onUpdate: ({ editor: instance }) => {
            knownValue = toModelValue(instance)
            emit('update:modelValue', knownValue)
        },
        onFocus: ({ event }) => emit('focus', event),
        onBlur: ({ event }) => {
            emit('blur', event)
            syncFromModel()
        }
    })

    /**
     * Load a value the parent changed. Never while the editor has focus: the parent's value can be
     * a refresh that is older than what the user has typed since. It is applied on blur instead.
     */
    const syncFromModel = (): void => {
        const instance = editor.value
        const value = props.modelValue || ''
        if (!instance || instance.isFocused || value === knownValue) {
            return
        }
        knownValue = value
        instance.commands.setContent(prepareContent(value), { emitUpdate: false })
    }

    watch(() => props.modelValue, syncFromModel)

    watch(
        () => props.readonly,
        (readonly) => editor.value?.setEditable(!readonly, false)
    )

    watch(spellcheck, () => editor.value?.setOptions({ editorProps: { attributes: contentAttributes() } }))

    // Decorations are only recomputed on a transaction; an empty one redraws them for new links.
    watch(
        () => props.citations,
        () => {
            const instance = editor.value
            if (instance && !instance.isDestroyed) {
                instance.view.dispatch(instance.state.tr.setMeta('citationMarks', true))
            }
        }
    )

    /**
     * Insert plain text at the cursor (or in place of the selection), separated from a preceding
     * word by a space - as a citation follows the word it supports.
     */
    const insertText = (text: string): void => {
        const instance = editor.value
        if (!instance || props.readonly) {
            return
        }
        const { from } = instance.state.selection
        const before = from > 1 ? instance.state.doc.textBetween(from - 1, from, '\n', '\n') : ''
        const spacer = before && !/\s/.test(before) ? ' ' : ''
        instance
            .chain()
            .focus()
            .insertContent({ type: 'text', text: `${spacer}${text}` })
            .run()
    }

    defineExpose({ insertText })

    // ---- Toolbar ----
    const chain = () => editor.value!.chain().focus()

    const toolGroups: Tool[][] = [
        [
            {
                name: 'bold',
                icon: 'mdi-format-bold',
                label: 'rich_text_editor.bold',
                run: () => chain().toggleBold().run(),
                active: () => editor.value!.isActive('bold')
            },
            {
                name: 'italic',
                icon: 'mdi-format-italic',
                label: 'rich_text_editor.italic',
                run: () => chain().toggleItalic().run(),
                active: () => editor.value!.isActive('italic')
            },
            {
                name: 'underline',
                icon: 'mdi-format-underline',
                label: 'rich_text_editor.underline',
                run: () => chain().toggleUnderline().run(),
                active: () => editor.value!.isActive('underline')
            },
            {
                name: 'strike',
                icon: 'mdi-format-strikethrough-variant',
                label: 'rich_text_editor.strike',
                run: () => chain().toggleStrike().run(),
                active: () => editor.value!.isActive('strike')
            }
        ],
        ([1, 2, 3] as const).map((level) => ({
            name: `heading-${level}`,
            icon: `mdi-format-header-${level}`,
            label: `rich_text_editor.heading_${level}`,
            run: () => chain().toggleHeading({ level }).run(),
            active: () => editor.value!.isActive('heading', { level })
        })),
        [
            {
                name: 'bullet-list',
                icon: 'mdi-format-list-bulleted',
                label: 'rich_text_editor.bullet_list',
                run: () => chain().toggleBulletList().run(),
                active: () => editor.value!.isActive('bulletList')
            },
            {
                name: 'ordered-list',
                icon: 'mdi-format-list-numbered',
                label: 'rich_text_editor.ordered_list',
                run: () => chain().toggleOrderedList().run(),
                active: () => editor.value!.isActive('orderedList')
            },
            {
                name: 'blockquote',
                icon: 'mdi-format-quote-close',
                label: 'rich_text_editor.blockquote',
                run: () => chain().toggleBlockquote().run(),
                active: () => editor.value!.isActive('blockquote')
            },
            {
                name: 'code-block',
                icon: 'mdi-code-braces',
                label: 'rich_text_editor.code_block',
                run: () => chain().toggleCodeBlock().run(),
                active: () => editor.value!.isActive('codeBlock')
            },
            {
                // Opens the link menu (see the template) rather than running a command.
                name: 'link',
                icon: 'mdi-link-variant',
                label: 'rich_text_editor.link',
                active: () => editor.value!.isActive('link')
            }
        ],
        [
            {
                name: 'clear',
                icon: 'mdi-format-clear',
                label: 'rich_text_editor.clear_formatting',
                run: () => chain().unsetAllMarks().clearNodes().run()
            },
            {
                name: 'undo',
                icon: 'mdi-undo',
                label: 'rich_text_editor.undo',
                run: () => chain().undo().run(),
                enabled: () => editor.value!.can().undo()
            },
            {
                name: 'redo',
                icon: 'mdi-redo',
                label: 'rich_text_editor.redo',
                run: () => chain().redo().run(),
                enabled: () => editor.value!.can().redo()
            }
        ]
    ]

    const isActive = (tool: Tool): boolean => tool.active?.() ?? false
    const isEnabled = (tool: Tool): boolean => tool.enabled?.() ?? true

    // ---- Link menu ----
    const linkMenu = ref(false)
    const linkUrl = ref('')
    const linkError = ref('')

    watch(linkMenu, (open) => {
        if (open && editor.value) {
            linkUrl.value = (editor.value.getAttributes('link')['href'] as string | undefined) || ''
            linkError.value = ''
        }
    })

    /** The URL to link to, with https:// assumed for a bare host, or null when it is not allowed. */
    const normalizeLink = (raw: string): string | null => {
        const url = raw.trim()
        const candidate = HAS_SCHEME.test(url) ? url : `https://${url}`
        return url && SAFE_LINK.test(candidate) ? candidate : null
    }

    const applyLink = (): void => {
        const href = normalizeLink(linkUrl.value)
        if (!href) {
            linkError.value = t('rich_text_editor.link_invalid')
            return
        }
        const instance = editor.value!
        if (instance.state.selection.empty && !instance.isActive('link')) {
            // Nothing selected to turn into a link: insert the address itself.
            chain()
                .insertContent({ type: 'text', text: href, marks: [{ type: 'link', attrs: { href } }] })
                .run()
        } else {
            chain().extendMarkRange('link').setLink({ href }).run()
        }
        linkMenu.value = false
    }

    const removeLink = (): void => {
        chain().extendMarkRange('link').unsetLink().run()
        linkMenu.value = false
    }
</script>

<style scoped>
    .rich-text-editor {
        border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
        border-radius: 4px;
        background: rgb(var(--v-theme-surface));
        color: rgb(var(--v-theme-on-surface));
    }

    .rich-text-editor:focus-within:not(.rich-text-editor--readonly) {
        border-color: rgb(var(--v-theme-primary));
    }

    .rich-text-editor__toolbar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 2px;
        padding: 4px;
        border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    }

    .rich-text-editor__content {
        overflow-y: auto;
        font-size: 16px;
    }

    /* Fill the scroll area, so a click anywhere in it lands in the text. */
    .rich-text-editor__document {
        display: flex;
        flex-direction: column;
        min-height: 100%;
    }

    .rich-text-editor__content :deep(.ProseMirror) {
        flex: 1;
        padding: 12px 16px;
        outline: none;
        overflow-wrap: anywhere;
    }

    /* Even spacing between the blocks, and none inside lists and quotes. */
    .rich-text-editor__content :deep(.ProseMirror :is(p, h1, h2, h3, ul, ol, blockquote, pre)) {
        margin: 0;
    }

    .rich-text-editor__content :deep(.ProseMirror > :is(p, h1, h2, h3, ul, ol, blockquote, pre) + *) {
        margin-top: 0.75em;
    }

    .rich-text-editor__content :deep(.ProseMirror ul),
    .rich-text-editor__content :deep(.ProseMirror ol) {
        padding-inline-start: 1.5em;
    }

    .rich-text-editor__content :deep(.ProseMirror blockquote) {
        padding-inline-start: 1em;
        border-inline-start: 3px solid rgba(var(--v-border-color), var(--v-border-opacity));
        color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
    }

    .rich-text-editor__content :deep(.ProseMirror pre) {
        padding: 8px 12px;
        border-radius: 4px;
        background: rgba(var(--v-theme-on-surface), 0.06);
        font-family: monospace;
        white-space: pre-wrap;
    }

    .rich-text-editor__content :deep(.ProseMirror a) {
        color: rgb(var(--v-theme-primary));
    }

    .rich-text-editor__content :deep(.rich-text-citation) {
        color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
        font-size: 0.85em;
    }

    .rich-text-editor__content :deep(.rich-text-citation--missing) {
        color: rgb(var(--v-theme-warning));
        text-decoration: line-through;
    }

    .rich-text-editor__content :deep(.rich-text-citation__number) {
        margin-inline-start: 2px;
        color: rgb(var(--v-theme-primary));
        font-weight: 600;
        user-select: none;
    }

    .rich-text-editor__content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
        content: attr(data-placeholder);
        float: inline-start;
        height: 0;
        pointer-events: none;
        color: rgba(var(--v-theme-on-surface), var(--v-disabled-opacity));
    }
</style>
