/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_APP_TARANIS_NG_CORE_API?: string
    readonly VITE_APP_TARANIS_NG_CORE_SSE?: string
    readonly VITE_APP_TARANIS_NG_LOCALE?: string
    readonly VITE_APP_TARANIS_NG_LOGIN_URL?: string
    readonly VITE_APP_TARANIS_NG_LOGOUT_URL?: string
    readonly VITE_APP_TARANIS_NG_TESTING_TOKEN?: string
    readonly VITE_APP_TARANIS_NG_LOGIN_METHOD?: string
    readonly VITE_APP_TARANIS_NG_LOGOUT_METHOD?: string
    readonly VITE_APP_TARANIS_NG_SSE_INIT_METHOD?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}

declare module '*.vue' {
    import type { DefineComponent } from 'vue'

    const component: DefineComponent<{}, {}, any>
    export default component
}
