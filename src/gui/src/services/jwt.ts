import type { JwtClaims } from '@/types/auth'

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

const toJwtClaims = (value: unknown): JwtClaims | null => {
    if (!isRecord(value) || typeof value['exp'] !== 'number') {
        return null
    }

    const claims: JwtClaims = {
        exp: value['exp']
    }

    if (typeof value['sub'] === 'string') {
        claims.sub = value['sub']
    }

    if (isRecord(value['user_claims'])) {
        const userClaims = value['user_claims']
        if (
            (typeof userClaims['id'] === 'string' || typeof userClaims['id'] === 'number') &&
            typeof userClaims['name'] === 'string' &&
            typeof userClaims['organization_name'] === 'string' &&
            (Array.isArray(userClaims['permissions']) || userClaims['permissions'] === undefined)
        ) {
            claims.user_claims = {
                id: userClaims['id'],
                name: userClaims['name'],
                organization_name: userClaims['organization_name'],
                permissions: Array.isArray(userClaims['permissions']) ? userClaims['permissions'] : []
            }
        }
    }

    return claims
}

const decodeBase64Url = (value: string): string => {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/')
    const paddingLength = (4 - (normalized.length % 4)) % 4
    const padded = normalized + '='.repeat(paddingLength)
    return atob(padded)
}

export const parseJwtClaims = (jwt: string): JwtClaims | null => {
    if (!jwt) {
        return null
    }

    const parts = jwt.split('.')
    if (parts.length < 3 || !parts[1]) {
        return null
    }

    try {
        const parsed = JSON.parse(decodeBase64Url(parts[1])) as unknown
        return toJwtClaims(parsed)
    } catch {
        return null
    }
}
