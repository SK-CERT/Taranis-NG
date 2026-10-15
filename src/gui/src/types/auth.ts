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
    // Whether passkeys exist at all on this installation.
    passkey_enabled: boolean
    // Whether a passkey may start a login on its own, which is a separate switch.
    passkey_login_enabled: boolean
}

// The authenticator a passkey lives on, as core names it from the community
// AAGUID list. Either icon may be missing; the other one stands in for it.
export interface PasskeyAuthenticatorInfo {
    name: string
    icon_light?: string | null
    icon_dark?: string | null
}

// A registered passkey, as GET /users/my-passkeys and the users list return it.
export interface PasskeySummary {
    id: number
    name: string
    created_at?: string | null
    last_used_at?: string | null
    // null for passkeys registered before the AAGUID was recorded
    aaguid?: string | null
    // null when the list does not know the AAGUID or core has no list
    authenticator?: PasskeyAuthenticatorInfo | null
    // false while the PASSKEY_AUTHENTICATOR_LOOKUP setting is off
    authenticator_lookup?: boolean
}

// Error payload returned by the login/MFA endpoints (HTTP 403)
export interface LoginErrorResponse {
    error?: string
    code?: string
    methods?: string[]
    mfa_token?: string
    enroll_token?: string
}
