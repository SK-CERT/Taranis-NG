/**
 * Global Vitest setup.
 *
 * happy-dom does not implement `window.visualViewport`, which Vuetify's
 * VOverlay (the base of v-dialog / v-menu / v-tooltip) reads when it positions
 * itself. Without it, mounting any component that opens a dialog throws
 * "visualViewport is not defined". Provide a minimal stand-in.
 */
if (typeof window !== 'undefined' && !window.visualViewport) {
    window.visualViewport = {
        width: window.innerWidth || 1024,
        height: window.innerHeight || 768,
        offsetLeft: 0,
        offsetTop: 0,
        pageLeft: 0,
        pageTop: 0,
        scale: 1,
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false
    }
    globalThis.visualViewport = window.visualViewport
}
