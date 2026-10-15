import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import { createTestI18n } from '../helpers/mount-helpers'
import PasskeyAuthenticator from '@/components/common/PasskeyAuthenticator.vue'

const LIGHT = 'data:image/svg+xml;base64,TElHSFQ='
const DARK = 'data:image/svg+xml;base64,REFSSw=='
const YUBIKEY = 'cb69481e-8ff7-4039-93ec-0a2729a154a8'
const ZERO = '00000000-0000-0000-0000-000000000000'

/** Mount with its own Vuetify, so each test picks the theme it runs under. */
function mountAuthenticator(props, { theme = 'light' } = {}) {
    const vuetify = createVuetify({ components, theme: { defaultTheme: theme } })
    const wrapper = mount(PasskeyAuthenticator, { props, global: { plugins: [vuetify, createTestI18n()] } })
    return { wrapper, vuetify }
}

const icon = (wrapper) => wrapper.find('[data-test="passkey-authenticator-icon"]')
const genericIcon = (wrapper) => wrapper.find('[data-test="passkey-authenticator-generic-icon"]')
const name = (wrapper) => wrapper.get('[data-test="passkey-authenticator-name"]').text()
const aaguidLine = (wrapper) => wrapper.find('[data-test="passkey-authenticator-aaguid"]')
// The browser's own tooltip: the title attribute of the icon and name.
const aaguidTitle = (wrapper) => wrapper.get('[data-test="passkey-authenticator"]').attributes('title')

describe('PasskeyAuthenticator', () => {
    describe('icon follows the dark/light mode', () => {
        it('shows the light icon in a light theme', () => {
            const { wrapper } = mountAuthenticator({
                aaguid: YUBIKEY,
                authenticator: { name: 'YubiKey', icon_light: LIGHT, icon_dark: DARK }
            })
            expect(icon(wrapper).attributes('src')).toBe(LIGHT)
        })

        it('shows the dark icon in a dark theme', () => {
            const { wrapper } = mountAuthenticator(
                { aaguid: YUBIKEY, authenticator: { name: 'YubiKey', icon_light: LIGHT, icon_dark: DARK } },
                { theme: 'dark' }
            )
            expect(icon(wrapper).attributes('src')).toBe(DARK)
        })

        it('swaps the icon when the theme changes', async () => {
            const { wrapper, vuetify } = mountAuthenticator({
                aaguid: YUBIKEY,
                authenticator: { name: 'YubiKey', icon_light: LIGHT, icon_dark: DARK }
            })
            await vuetify.theme.change('dark')
            await wrapper.vm.$nextTick()
            expect(icon(wrapper).attributes('src')).toBe(DARK)
        })

        it('uses the only variant the list has, whatever the mode', () => {
            // Core sends no dark icon when it would be identical to the light one.
            const lightOnly = mountAuthenticator(
                { aaguid: YUBIKEY, authenticator: { name: 'Bitwarden', icon_light: LIGHT, icon_dark: null } },
                { theme: 'dark' }
            )
            const darkOnly = mountAuthenticator({ aaguid: YUBIKEY, authenticator: { name: 'Other', icon_light: null, icon_dark: DARK } })
            expect(icon(lightOnly.wrapper).attributes('src')).toBe(LIGHT)
            expect(icon(darkOnly.wrapper).attributes('src')).toBe(DARK)
        })

        it('is decorative: the name next to it is what gets read out', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: { name: 'YubiKey', icon_light: LIGHT } })
            expect(icon(wrapper).attributes('alt')).toBe('')
        })
    })

    describe('fallbacks', () => {
        it('names a known authenticator and shows its AAGUID', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: { name: 'YubiKey 5 Series', icon_light: LIGHT } })
            expect(name(wrapper)).toBe('YubiKey 5 Series')
            expect(aaguidLine(wrapper).text()).toBe(`AAGUID ${YUBIKEY}`)
            expect(aaguidLine(wrapper).attributes('dir')).toBe('ltr')
        })

        it('shows a generic icon for a known authenticator the list has no icon for', () => {
            const { wrapper } = mountAuthenticator({
                aaguid: YUBIKEY,
                authenticator: { name: 'Plain Key', icon_light: null, icon_dark: null }
            })
            expect(icon(wrapper).exists()).toBe(false)
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Plain Key')
            expect(aaguidLine(wrapper).text()).toContain(YUBIKEY)
        })

        it('says the authenticator is unknown when core could not name it, and keeps the AAGUID', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null })
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Unknown authenticator')
            expect(aaguidLine(wrapper).text()).toContain(YUBIKEY)
        })

        it('says "not identified", not "unknown", while the lookup is switched off', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null, lookup: false })
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Not identified')
            expect(wrapper.text()).not.toContain('Unknown authenticator')
            expect(aaguidLine(wrapper).text()).toBe(`AAGUID ${YUBIKEY}`)
        })

        it('says so when the authenticator did not disclose its model', () => {
            const { wrapper } = mountAuthenticator({ aaguid: ZERO, authenticator: null })
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Not disclosed by the authenticator')
            expect(aaguidLine(wrapper).text()).toContain(ZERO)
        })

        it('says the AAGUID was not recorded for a passkey registered before it was', () => {
            const { wrapper } = mountAuthenticator({ aaguid: null, authenticator: null })
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Not recorded')
            expect(aaguidLine(wrapper).exists()).toBe(false)
        })

        it('falls back to the generic icon when the vendor icon fails to load', async () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: { name: 'YubiKey', icon_light: LIGHT } })
            await icon(wrapper).trigger('error')
            expect(icon(wrapper).exists()).toBe(false)
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('YubiKey')
        })
    })

    describe('AAGUID in a tooltip', () => {
        it('shows the icon and the name, and the AAGUID only in the browser tooltip', () => {
            const { wrapper } = mountAuthenticator({
                aaguid: YUBIKEY,
                authenticator: { name: 'YubiKey 5 Series', icon_light: LIGHT },
                aaguidTooltip: true
            })
            expect(icon(wrapper).attributes('src')).toBe(LIGHT)
            expect(name(wrapper)).toBe('YubiKey 5 Series')
            expect(aaguidLine(wrapper).exists()).toBe(false)
            expect(aaguidTitle(wrapper)).toBe(`AAGUID ${YUBIKEY}`)
        })

        it('keeps the fallback labels and puts their AAGUID in the tooltip', () => {
            const unknown = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null, aaguidTooltip: true })
            const undisclosed = mountAuthenticator({ aaguid: ZERO, authenticator: null, aaguidTooltip: true })
            expect(name(unknown.wrapper)).toBe('Unknown authenticator')
            expect(aaguidTitle(unknown.wrapper)).toBe(`AAGUID ${YUBIKEY}`)
            expect(name(undisclosed.wrapper)).toBe('Not disclosed by the authenticator')
            expect(aaguidTitle(undisclosed.wrapper)).toBe(`AAGUID ${ZERO}`)
        })

        it('says "not identified" while the lookup is off, with the AAGUID in the tooltip', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null, lookup: false, aaguidTooltip: true })
            expect(genericIcon(wrapper).exists()).toBe(true)
            expect(name(wrapper)).toBe('Not identified')
            expect(aaguidLine(wrapper).exists()).toBe(false)
            expect(aaguidTitle(wrapper)).toBe(`AAGUID ${YUBIKEY}`)
        })

        it('has no tooltip when no AAGUID was recorded', () => {
            const { wrapper } = mountAuthenticator({ aaguid: null, authenticator: null, aaguidTooltip: true })
            expect(name(wrapper)).toBe('Not recorded')
            expect(aaguidTitle(wrapper)).toBeUndefined()
        })

        it('leaves the AAGUID on its own line, without a tooltip, by default', () => {
            const { wrapper } = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null })
            expect(aaguidLine(wrapper).exists()).toBe(true)
            expect(aaguidTitle(wrapper)).toBeUndefined()
        })
    })

    describe('icon only', () => {
        it('names the authenticator in the tooltip and to screen readers, and writes nothing out', () => {
            const { wrapper } = mountAuthenticator({
                aaguid: YUBIKEY,
                authenticator: { name: 'YubiKey 5 Series', icon_light: LIGHT },
                iconOnly: true
            })
            expect(icon(wrapper).attributes('src')).toBe(LIGHT)
            expect(aaguidTitle(wrapper)).toBe('YubiKey 5 Series')
            expect(wrapper.get('[data-test="passkey-authenticator"]').attributes('aria-label')).toBe('YubiKey 5 Series')
            expect(wrapper.get('[data-test="passkey-authenticator"]').attributes('role')).toBe('img')
            expect(wrapper.text()).toBe('')
        })

        it('gives the AAGUID when the authenticator has no name', () => {
            const unknown = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null, iconOnly: true })
            const off = mountAuthenticator({ aaguid: YUBIKEY, authenticator: null, lookup: false, iconOnly: true })
            expect(genericIcon(unknown.wrapper).exists()).toBe(true)
            expect(aaguidTitle(unknown.wrapper)).toBe(`AAGUID ${YUBIKEY}`)
            expect(aaguidTitle(off.wrapper)).toBe(`AAGUID ${YUBIKEY}`)
        })

        it('says "not recorded" when there is no AAGUID either', () => {
            const { wrapper } = mountAuthenticator({ aaguid: null, authenticator: null, iconOnly: true })
            expect(aaguidTitle(wrapper)).toBe('Not recorded')
        })

        it('follows the dark/light mode like the full display', () => {
            const { wrapper } = mountAuthenticator(
                { aaguid: YUBIKEY, authenticator: { name: 'YubiKey', icon_light: LIGHT, icon_dark: DARK }, iconOnly: true },
                { theme: 'dark' }
            )
            expect(icon(wrapper).attributes('src')).toBe(DARK)
        })
    })
})
