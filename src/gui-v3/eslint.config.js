import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginVueI18n from '@intlify/eslint-plugin-vue-i18n'
import eslintConfigPrettier from 'eslint-config-prettier'
import tsParser from '@typescript-eslint/parser'
import vueParser from 'vue-eslint-parser'
import * as jsoncParser from 'jsonc-eslint-parser'

const sharedGlobals = {
    // Browser globals
    window: 'readonly',
    document: 'readonly',
    navigator: 'readonly',
    console: 'readonly',
    alert: 'readonly',
    confirm: 'readonly',
    atob: 'readonly',
    btoa: 'readonly',
    CustomEvent: 'readonly',
    Event: 'readonly',
    EventListener: 'readonly',
    EventSource: 'readonly',
    HTMLElement: 'readonly',
    Element: 'readonly',
    Node: 'readonly',
    MouseEvent: 'readonly',
    KeyboardEvent: 'readonly',
    DragEvent: 'readonly',
    IntersectionObserver: 'readonly',
    IntersectionObserverEntry: 'readonly',
    AbortSignal: 'readonly',
    AbortController: 'readonly',
    requestAnimationFrame: 'readonly',
    cancelAnimationFrame: 'readonly',
    setInterval: 'readonly',
    clearInterval: 'readonly',
    setTimeout: 'readonly',
    clearTimeout: 'readonly',
    localStorage: 'readonly',
    sessionStorage: 'readonly',
    Storage: 'readonly',
    URL: 'readonly',
    Blob: 'readonly',
    File: 'readonly',
    FileReader: 'readonly',
    FormData: 'readonly',
    fetch: 'readonly',
    // Node globals
    process: 'readonly',
    global: 'readonly',
    __dirname: 'readonly',
    require: 'readonly',
    // Vue/Vite specific
    defineProps: 'readonly',
    defineEmits: 'readonly',
    defineExpose: 'readonly',
    withDefaults: 'readonly'
}

const generalRules = {
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-unused-vars': 'off',
    'prefer-const': 'warn',
    'no-var': 'error'
}

const vueRules = {
    'vue/multi-word-component-names': 'off',
    'vue/no-v-html': 'off',
    'vue/require-default-prop': 'off',
    'vue/require-prop-types': 'off',
    'vue/valid-v-slot': 'off',
    'vue/no-mutating-props': 'off',
    'vue/no-template-shadow': 'off',
    'vue/prop-name-casing': 'off',
    'vue/no-required-prop-with-default': 'off',
    'vue/singleline-html-element-content-newline': 'off',
    'vue/multiline-html-element-content-newline': 'off',
    'vue/max-attributes-per-line': [
        'warn',
        {
            singleline: 1,
            multiline: 1
        }
    ],
    'vue/html-indent': [
        'warn',
        4,
        {
            attribute: 1,
            baseIndent: 1,
            closeBracket: 0
        }
    ]
}

export default [
    js.configs.recommended,
    ...pluginVue.configs['flat/recommended'],
    {
        files: ['**/*.{js,mjs,cjs}'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'module',
            globals: sharedGlobals
        },
        rules: generalRules
    },
    {
        files: ['**/*.vue'],
        languageOptions: {
            parser: vueParser,
            parserOptions: {
                parser: tsParser,
                ecmaVersion: 'latest',
                sourceType: 'module',
                extraFileExtensions: ['.vue']
            },
            globals: sharedGlobals
        },
        rules: {
            ...generalRules,
            ...vueRules
        }
    },
    {
        files: ['**/*.{ts,mts,cts}'],
        languageOptions: {
            parser: tsParser,
            ecmaVersion: 'latest',
            sourceType: 'module',
            parserOptions: {
                project: './tsconfig.json'
            },
            globals: sharedGlobals
        },
        rules: generalRules
    },
    {
        files: ['**/*.{js,ts,vue}'],
        plugins: {
            '@intlify/vue-i18n': pluginVueI18n
        },
        languageOptions: {
            globals: {
                t: 'readonly'
            }
        },
        settings: {
            'vue-i18n': {
                localeDir: './src/i18n/*.json'
            }
        },
        rules: {
            // Every key handed to t() must exist in the locale files.
            '@intlify/vue-i18n/no-missing-keys': 'error',
            // ignorePattern covers markup that only
            // looks like copy: mdi icon names passed as slot content, punctuation-only nodes
            // (":", "(", ")"), secret masks and the Jinja snippets in the product-type help.
            '@intlify/vue-i18n/no-raw-text': [
                'error',
                {
                    ignorePattern: '^(mdi-[a-z0-9-]+|\\{%.*%\\}|[\\s\\d\\-–—:;,.()\\[\\]{}<>/\\\\|+*&#@!?%•·…"\'`]*)$',
                    ignoreText: ['Taranis NG']
                }
            ],
            // vue-i18n v11: flag APIs removed/renamed since v8 so they can't creep back in.
            '@intlify/vue-i18n/no-deprecated-i18n-component': 'error',
            '@intlify/vue-i18n/no-deprecated-i18n-place-attr': 'error',
            '@intlify/vue-i18n/no-deprecated-i18n-places-prop': 'error',
            '@intlify/vue-i18n/no-deprecated-modulo-syntax': 'error',
            '@intlify/vue-i18n/no-deprecated-tc': 'error',
            '@intlify/vue-i18n/no-deprecated-v-t': 'error',
            '@intlify/vue-i18n/no-i18n-t-path-prop': 'error'
        }
    },
    {
        // The locale files themselves. They need the JSON parser to be inspectable, and the
        // block is scoped to src/i18n so `eslint .` doesn't start parsing package.json,
        // tsconfig.json and friends.
        files: ['src/i18n/*.json'],
        plugins: {
            '@intlify/vue-i18n': pluginVueI18n
        },
        languageOptions: {
            parser: jsoncParser
        },
        settings: {
            'vue-i18n': {
                localeDir: './src/i18n/*.json'
            }
        },
        rules: {
            // A key added to en.json but not to cs.json/sk.json silently falls back to English
            // in the UI. This is the check that keeps the three files in lockstep.
            '@intlify/vue-i18n/no-missing-keys-in-other-locales': 'error',
            '@intlify/vue-i18n/no-duplicate-keys-in-locale': 'error',
            '@intlify/vue-i18n/valid-message-syntax': 'error',
            '@intlify/vue-i18n/no-html-messages': 'error'
            // no-unused-keys is deliberately NOT enabled: the app builds many keys at runtime
            // (t('settings.' + key), notification `loc:` strings, total-count-title props), and
            // the rule reports all ~700 of them as unused. Run it ad hoc if you want to prune.
        }
    },
    {
        ignores: ['dist/**', 'node_modules/**', 'coverage/**', 'playwright-report/**', 'test-results/**', '*.min.js']
    },
    // Prettier owns formatting (self-closing tags, indentation, attribute layout,
    // quotes, etc.); ESLint owns logic (no-unused-vars, no-mutating-props,
    // vue-i18n/no-missing-keys, ...). config-prettier disables the formatting-side
    // ESLint rules so the two tools never fight. It MUST be the last entry: it only
    // turns rules off, so anything earlier in the array can still set logic rules.
    eslintConfigPrettier
]
