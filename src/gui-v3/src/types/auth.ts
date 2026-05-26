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
    method?: string
    [key: string]: unknown
}

export interface TokenPayload {
    access_token: string
}
