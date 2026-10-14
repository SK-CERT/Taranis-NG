<template>
    <span class="passkey-authenticator">
        <img
            v-if="iconSrc"
            :src="iconSrc"
            alt=""
            width="20"
            height="20"
            class="passkey-authenticator__icon"
            data-test="passkey-authenticator-icon"
            @error="iconFailed = true"
        />
        <v-icon
            v-else
            size="20"
            class="passkey-authenticator__icon"
            data-test="passkey-authenticator-generic-icon"
            >mdi-key-variant</v-icon
        >
        <span class="passkey-authenticator__text">
            <bdi
                v-if="label"
                dir="auto"
                data-test="passkey-authenticator-name"
                >{{ label }}</bdi
            >
            <span
                v-if="aaguid"
                class="passkey-authenticator__aaguid text-caption"
                dir="ltr"
                data-test="passkey-authenticator-aaguid"
                >{{ t('security.passkey_aaguid') }} {{ aaguid }}</span
            >
        </span>
    </span>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useTheme } from 'vuetify'
    import type { PasskeyAuthenticatorInfo } from '@/types/auth'

    // What an authenticator reports when it does not disclose its model.
    const ZERO_AAGUID = '00000000-0000-0000-0000-000000000000'

    const props = withDefaults(
        defineProps<{
            aaguid?: string | null | undefined
            authenticator?: PasskeyAuthenticatorInfo | null | undefined
            // false while core does not name authenticators (the setting is off): an
            // authenticator without a name is then not "unknown", just not looked up
            lookup?: boolean | undefined
        }>(),
        {
            aaguid: null,
            authenticator: null,
            lookup: true
        }
    )

    const { t } = useI18n()
    // Called here rather than inside the computed: Vuetify asserts a setup context.
    const { global: themeGlobal } = useTheme()

    // An icon that fails to load gives way to the generic one.
    const iconFailed = ref(false)
    watch(
        () => props.authenticator,
        () => {
            iconFailed.value = false
        }
    )

    // The icon follows the app's dark/light mode; when the list has only one
    // variant, that one stands in.
    const iconSrc = computed((): string | null => {
        if (iconFailed.value || !props.authenticator) return null
        const { icon_light: light, icon_dark: dark } = props.authenticator
        return (themeGlobal.current.value.dark ? dark || light : light || dark) || null
    })

    // null leaves the AAGUID as the only line.
    const label = computed((): string | null => {
        if (props.authenticator?.name) return props.authenticator.name
        if (!props.aaguid) return t('security.authenticator_not_recorded')
        if (props.aaguid.toLowerCase() === ZERO_AAGUID) return t('security.authenticator_not_disclosed')
        return props.lookup ? t('security.authenticator_unknown') : null
    })
</script>

<style scoped>
    .passkey-authenticator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }

    .passkey-authenticator__icon {
        flex: none;
        width: 20px;
        height: 20px;
        object-fit: contain;
    }

    .passkey-authenticator__text {
        display: flex;
        flex-direction: column;
        min-width: 0;
        line-height: 1.3;
    }

    .passkey-authenticator__aaguid {
        font-family: ui-monospace, 'SFMono-Regular', monospace;
        opacity: 0.75;
        white-space: nowrap;
    }
</style>
