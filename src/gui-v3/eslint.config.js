import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import pluginVueI18n from '@intlify/eslint-plugin-vue-i18n'
import tsParser from '@typescript-eslint/parser'
import vueParser from 'vue-eslint-parser'

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
            singleline: 3,
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
            '@intlify/vue-i18n/no-unused-keys': [
                'warn',
                {
                    extensions: ['.js', '.ts', '.vue'],
                    ignores: ['validations', 'cvss_calculator', 'cvss_calculator_tooltip']
                }
            ],
            '@intlify/vue-i18n/no-missing-keys': 'warn'
        }
    },
    {
        ignores: ['dist/**', 'node_modules/**', 'coverage/**', 'playwright-report/**', 'test-results/**', '*.min.js']
    }
]
