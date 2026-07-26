import type { PermissionKey } from './permissions'

export interface UserClaims {
    id: string | number
    name: string
    organization_name: string
    permissions: PermissionKey[]
}

export interface JwtClaims {
    exp: number
    sub?: string
    user_claims?: UserClaims
    [key: string]: unknown
}

export interface AuthStoreState {
    jwt: string
}

export interface AuthTokenResponse {
    access_token: string
}

export interface LoginPayload {
    username?: string
    password?: string
    provider_id?: number | null
    method?: string
    [key: string]: unknown
}

export interface TokenPayload {
    access_token: string
}

export interface LoginMethod {
    id: number
    name: string
    kind: 'local' | 'oidc' | 'oauth2' | 'saml' | 'ldap'
    form: boolean
    login_url: string | null
}

// GET /auth/methods: the enabled providers plus site-wide capabilities.
// Passkeys are not a provider - they are credentials owned by users, gated by
// a security setting.
export interface LoginMethodsResponse {
    items: LoginMethod[]
    passkey_enabled: boolean
}

// Error payload returned by the login/MFA endpoints (HTTP 403)
export interface LoginErrorResponse {
    error?: string
    code?: string
    methods?: string[]
    mfa_token?: string
    enroll_token?: string
}
