import type { ThemeFamily } from './types'

/**
 * SK-CERT - #0057ad, #d4351c, #343a40, #bcbdc0, #fff, matched against
 * https://www.sk-cert.sk/sk/aktuality/index.html.
 *
 * The site's structure is what this reproduces: a #0057AD navigation bar in
 * white uppercase, underlined by a heavy #D4351C rule, over white content laid
 * on #EEEEEE panels with #0B0C0C body text and #343A40 for the government
 * strip. #2C93DE is the site's lighter blue, used for links on dark ground, so
 * it takes `primary` in the dark variant where #0057AD would be too dark.
 *
 * Every seed is verbatim in both variants; the blue bar carries white text at
 * 7.08:1, so it needs no darkening.
 */
export const skcert: ThemeFamily = {
    id: 'skcert',
    label: 'SK-CERT',
    light: {
        background: '#EEEEEE',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#F5F5F5',
        surfaceVariant: '#EAEAEA',
        onSurface: '#0B0C0C',
        onSurfaceVariant: '#0B0C0C',
        outline: '#BCBDC0',
        primary: '#0057AD',
        secondary: '#343A40',
        tertiary: '#2C93DE',
        error: '#D4351C',
        info: '#2C93DE',
        success: '#2E7D32',
        warning: '#A66300',
        accent: '#D4351C',
        menuBg: '#0057AD',
        onMenuBg: '#FFFFFF',
        menuBorder: '3px solid #D4351C',
        drawerBg: '#EEEEEE',
        onDrawerBg: '#0B0C0C',
        workspace: '#EAEAEA',
        listRow: '#FFFFFF',
        listRowSelected: '#FBDDD8',
        listBorder: 'rgba(52, 58, 64, 0.30)',
        panelBorder: 'rgba(52, 58, 64, 0.52)',
        filterControlsBg: '#EAEAEA',
        menuItemActive: 'rgba(255, 255, 255, 0.20)'
    },
    dark: {
        background: '#0B0C0C',
        surface: '#16181A',
        surfaceBright: '#2A2E32',
        surfaceLight: '#1D2124',
        surfaceVariant: '#212528',
        onSurface: '#EEEEEE',
        onSurfaceVariant: '#EEEEEE',
        outline: '#5B636B',
        primary: '#2C93DE',
        secondary: '#BCBDC0',
        tertiary: '#6FB6E8',
        error: '#F0705C',
        info: '#2C93DE',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#D4351C',
        menuBg: '#0057AD',
        onMenuBg: '#FFFFFF',
        menuBorder: '3px solid #D4351C',
        drawerBg: '#1D2124',
        onDrawerBg: '#FFFFFF',
        workspace: '#0A0B0C',
        listRow: '#15181A',
        listRowSelected: 'rgba(212, 53, 28, 0.26)',
        listBorder: 'rgba(188, 189, 192, 0.30)',
        panelBorder: 'rgba(188, 189, 192, 0.48)',
        filterControlsBg: '#0F1113',
        menuItemActive: 'rgba(255, 255, 255, 0.20)'
    }
}
