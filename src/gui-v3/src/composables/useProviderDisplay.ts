import { useI18n } from 'vue-i18n'

/**
 * Display helpers for authentication providers.
 *
 * The built-in "local" provider is a singleton whose identity is fixed by the
 * system: it cannot be created a second time, deleted, or renamed. Its name is
 * seeded in English ("Local accounts") in the database, so the UI shows a
 * translated label instead of that stored value. Every other kind keeps its
 * admin-set name verbatim.
 */
export function useProviderDisplay() {
    const { t } = useI18n()

    const isLocal = (provider?: { kind?: string } | null): boolean => provider?.kind === 'local'

    const providerName = (provider?: { kind?: string; name?: string } | null): string =>
        isLocal(provider) ? t('auth_provider.local_name') : (provider?.name ?? '')

    return { isLocal, providerName }
}
