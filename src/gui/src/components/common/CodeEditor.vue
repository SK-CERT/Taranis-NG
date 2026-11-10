<template>
    <div
        ref="host"
        class="code-editor"
        :class="{ 'code-editor--dark': isDark, 'code-editor--disabled': disabled, 'code-editor--readonly': readonly }"
        :style="{ '--code-editor-min-height': minHeight, '--code-editor-max-height': maxHeight }"
    />
</template>

<script lang="ts">
    // Set up once for every editor, when the module loads.
    import type { PrismEditor } from 'prism-code-editor'
    import { registerCompletions } from 'prism-code-editor/autocomplete'
    import { setIgnoreTab } from 'prism-code-editor/commands'
    import { languages } from 'prism-code-editor/prism'
    import { jinjaCompletions, type JinjaCompletionSettings } from '@/utils/jinjaCompletions'
    // The Jinja grammar (registered as "jinja2", with HTML around it) and its editing behaviour.
    import 'prism-code-editor/prism/languages/django'
    import 'prism-code-editor/languages/django'
    import 'prism-code-editor/layout.css'
    import 'prism-code-editor/autocomplete.css'
    import 'prism-code-editor/autocomplete-icons.css'

    // Tab moves the focus on, as in any other field (Ctrl+M switches it to indenting).
    setIgnoreTab(true)

    // The grammar takes a filter only straight after the bar ("name|clean"); templates mostly
    // write "name | clean", which it would colour as a variable.
    type Pattern = { pattern?: RegExp }
    const jinja = languages['jinja2'] as unknown as { django?: { inside?: { filter?: Pattern } } } | undefined
    const filter = jinja?.django?.inside?.filter
    if (filter?.pattern) filter.pattern = /(\|\s*)\w+/

    // Completions are registered per language, for every editor at once; each editor that offers
    // them says here what it is editing (a product or an item template, and of which type).
    export const completionSettings = new WeakMap<PrismEditor, () => JinjaCompletionSettings | null>()
    registerCompletions(['jinja2', 'django', 'html', 'markup'], {
        sources: [
            (context, editor) => {
                const settings = completionSettings.get(editor)?.()
                return settings ? jinjaCompletions(context.before, settings) : null
            }
        ]
    })
</script>

<script setup lang="ts">
    /**
     * A code editor with syntax highlighting (prism-code-editor), for Jinja templates: the
     * template tags, expressions and filters as well as the HTML around them.
     *
     * A `<textarea>` with the highlighted code drawn under it, so typing, selecting, copying and
     * screen readers behave as in any other field. v-model holds the text; `readonly` shows code
     * that can be selected and copied but not changed. The colours follow the Vuetify theme.
     */
    import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
    import { useTheme } from 'vuetify'
    import { createEditor } from 'prism-code-editor'
    import { autoComplete, fuzzyFilter } from 'prism-code-editor/autocomplete'
    import { cursorPosition } from 'prism-code-editor/cursor'
    import { defaultKeymap, editHistory, editorCommands } from 'prism-code-editor/commands'
    import { matchBrackets } from 'prism-code-editor/match-brackets'
    import { highlightBracketPairs } from 'prism-code-editor/highlight-brackets'

    const props = withDefaults(
        defineProps<{
            readonly?: boolean
            disabled?: boolean
            /** The accessible name of the editing area. */
            ariaLabel?: string
            minHeight?: string
            maxHeight?: string
            /** Offer Jinja completions (Ctrl+Space, or as you type inside {{ }} and {% %}) for this kind of template. */
            completions?: JinjaCompletionSettings | null
        }>(),
        { readonly: false, disabled: false, ariaLabel: '', minHeight: '0', maxHeight: 'none', completions: null }
    )

    const model = defineModel<string>({ default: '' })

    const theme = useTheme()
    const isDark = computed(() => theme.current.value.dark)

    const host = ref<HTMLElement | null>(null)
    const editor = shallowRef<PrismEditor | null>(null)

    onMounted(() => {
        if (!host.value) return
        editor.value = createEditor(
            host.value,
            {
                language: 'jinja2',
                value: model.value ?? '',
                tabSize: 4,
                readOnly: props.readonly || props.disabled,
                onUpdate: (value) => {
                    if (value !== model.value) model.value = value
                }
            },
            editHistory(),
            editorCommands(defaultKeymap),
            matchBrackets(false),
            highlightBracketPairs(),
            // The completion list is placed at the cursor, which this extension tracks: without
            // it the list never opens.
            cursorPosition(),
            autoComplete({ filter: fuzzyFilter })
        )
        // Read when asked, so a change of kind or type in the dialog applies to the next completion.
        completionSettings.set(editor.value, () => (props.readonly || props.disabled ? null : props.completions))
        if (props.ariaLabel) editor.value.textarea.setAttribute('aria-label', props.ariaLabel)
    })

    // A new text from outside (another template opened, a starting point chosen) replaces the editor's.
    watch(model, (text) => {
        if (editor.value && editor.value.value !== (text ?? '')) editor.value.setOptions({ value: text ?? '' })
    })

    watch(
        () => props.readonly || props.disabled,
        (readOnly) => editor.value?.setOptions({ readOnly })
    )

    watch(
        () => props.ariaLabel,
        (label) => editor.value?.textarea.setAttribute('aria-label', label)
    )

    onBeforeUnmount(() => {
        editor.value?.remove()
        editor.value = null
    })

    defineExpose({ editor })
</script>

<style scoped>
    .code-editor {
        --code-text: rgb(var(--v-theme-on-surface));
        /* Light: every colour keeps a contrast of 4.5:1 or more on white. */
        --code-delimiter: #0e7490;
        --code-keyword: #a626a4;
        --code-variable: #c2410c;
        --code-filter: #2563eb;
        --code-string: #15803d;
        --code-number: #a16207;
        --code-comment: #6b7280;
        --code-tag: #be123c;
        --code-attribute: #a16207;

        border: 1px solid rgba(var(--v-border-color), 0.38);
        border-radius: 4px;
        overflow: hidden;
        background-color: rgb(var(--v-theme-surface));
    }

    .code-editor--dark {
        --code-delimiter: #56b6c2;
        --code-keyword: #c678dd;
        --code-variable: #d19a66;
        --code-filter: #61afef;
        --code-string: #98c379;
        --code-number: #e5c07b;
        --code-comment: #8b929e;
        --code-tag: #e06c75;
        --code-attribute: #e5c07b;
    }

    .code-editor:focus-within {
        border-color: rgb(var(--v-theme-primary));
        box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
    }

    .code-editor--readonly {
        background-color: rgba(var(--v-theme-on-surface), 0.03);
    }

    .code-editor--readonly:focus-within {
        border-color: rgba(var(--v-border-color), 0.38);
        box-shadow: none;
    }

    .code-editor--disabled {
        opacity: 0.6;
    }

    .code-editor :deep(.prism-code-editor) {
        --pce-bg: transparent;
        --pce-cursor: var(--code-text);
        --pce-selection: rgba(var(--v-theme-primary), 0.22);
        --pce-selection-match: rgba(var(--v-theme-primary), 0.12);
        --pce-line-number: rgba(var(--v-theme-on-surface), 0.45);
        --pce-bg-highlight: rgba(var(--v-theme-on-surface), 0.04);
        --pce-border-highlight: none;
        --padding-inline: 0.75em;
        /* The completion list. */
        --pce-widget-bg: rgb(var(--v-theme-surface));
        --pce-widget-border: rgba(var(--v-border-color), 0.38);
        --pce-widget-color: var(--code-text);
        --pce-widget-bg-active: rgba(var(--v-theme-primary), 0.16);
        --pce-widget-color-active: var(--code-text);
        --pce-widget-bg-hover: rgba(var(--v-theme-on-surface), 0.06);
        --pce-ac-match: rgb(var(--v-theme-primary));
        --pce-tabstop: rgba(var(--v-theme-primary), 0.2);
        --pce-ac-icon-variable: var(--code-variable);
        --pce-ac-icon-property: var(--code-variable);
        --pce-ac-icon-function: var(--code-filter);
        --pce-ac-icon-keyword: var(--code-keyword);
        --pce-ac-icon-constant: var(--code-string);

        min-height: var(--code-editor-min-height);
        max-height: var(--code-editor-max-height);
        color: var(--code-text);
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.85rem;
        line-height: 1.45;
    }

    /* Nothing is edited in a read-only editor: no line under the cursor to mark. */
    .code-editor--readonly :deep(.active-line:after) {
        background: none;
    }

    .code-editor :deep(.pce-line:before) {
        border-right: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    }

    .code-editor :deep(.active-bracket) {
        background-color: rgba(var(--v-theme-primary), 0.2);
        border-radius: 2px;
    }

    /* HTML */
    .code-editor :deep(.token.tag),
    .code-editor :deep(.token.tag > .token.punctuation) {
        color: var(--code-tag);
    }

    .code-editor :deep(.token.attr-name) {
        color: var(--code-attribute);
    }

    .code-editor :deep(.token.attr-value),
    .code-editor :deep(.token.attr-value > .token.punctuation) {
        color: var(--code-string);
    }

    .code-editor :deep(.token.comment) {
        color: var(--code-comment);
        font-style: italic;
    }

    .code-editor :deep(.token.entity) {
        color: var(--code-number);
    }

    /* Jinja: {{ ... }}, {% ... %} and {# ... #}, also inside HTML attribute values */
    .code-editor :deep(.language-django) {
        color: var(--code-variable);
        font-style: normal;
    }

    .code-editor :deep(.language-django .token.delimiter) {
        color: var(--code-delimiter);
        font-weight: 600;
    }

    .code-editor :deep(.language-django .token.keyword) {
        color: var(--code-keyword);
    }

    .code-editor :deep(.language-django .token.filter),
    .code-editor :deep(.language-django .token.function),
    .code-editor :deep(.language-django .token.test) {
        color: var(--code-filter);
    }

    .code-editor :deep(.language-django .token.string) {
        color: var(--code-string);
    }

    .code-editor :deep(.language-django .token.number),
    .code-editor :deep(.language-django .token.boolean) {
        color: var(--code-number);
    }

    .code-editor :deep(.language-django .token.operator),
    .code-editor :deep(.language-django .token.punctuation:not(.delimiter)) {
        color: var(--code-text);
    }

    .code-editor :deep(.language-django .token.comment) {
        color: var(--code-comment);
        font-style: italic;
    }
</style>
