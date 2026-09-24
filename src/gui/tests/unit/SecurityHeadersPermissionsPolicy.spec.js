import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * The Permissions-Policy nginx sends with this GUI must leave WebAuthn usable.
 *
 * `publickey-credentials-get=()` is an EMPTY allowlist, which disables the
 * feature for the page's own origin as well - not just for cross-origin frames.
 * With it, navigator.credentials.get() throws NotAllowedError and no passkey can
 * ever be used, to sign in or as a second factor, while registration keeps
 * working: a silent, one-token way to break half the feature that no unit or
 * component test would notice, because it lives in the deployed nginx config.
 */
const guiRoot = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const headers = readFileSync(resolve(guiRoot, 'extras/security-headers.inc'), 'utf-8')

/** The Permissions-Policy value, unwrapped from nginx's line continuations. */
const permissionsPolicy = (() => {
    const match = headers.match(/add_header\s+Permissions-Policy\s+"([\s\S]*?)"\s+always;/)
    expect(match, 'security-headers.inc must set a Permissions-Policy').toBeTruthy()
    return match[1].replace(/\s+/g, ' ').trim()
})()

const directive = (name) => permissionsPolicy.match(new RegExp(`${name}=\\(([^)]*)\\)`))?.[1]?.trim()

describe('GUI Permissions-Policy', () => {
    it.each(['publickey-credentials-get', 'publickey-credentials-create'])('allows %s for this origin', (feature) => {
        // Present and self-allowed. `()` would disable it everywhere, including here.
        expect(directive(feature), `${feature} must be listed`).toBeDefined()
        expect(directive(feature)).toBe('self')
    })

    it('still denies the features the GUI has no use for', () => {
        // Guards against someone "fixing" a future policy problem by loosening
        // everything rather than the one capability that is actually needed.
        for (const feature of ['camera', 'microphone', 'geolocation', 'payment', 'usb', 'serial']) {
            expect(directive(feature), `${feature} must stay disabled`).toBe('')
        }
    })
})
