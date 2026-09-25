import type { ThemeFamily } from './types'

/**
 * Sunny Summer - https://www.schemecolor.com/sunny-summer.php
 * Naughty Blue #067EE9, Vivid Mint #0DD085, Tangy Yellow #FFE62D,
 * Chilean Fire #F97904, Maraschino #E41312.
 *
 * The source palette is five equal vivid blocks with no neutrals, so all five
 * are used verbatim on the roles that actually render them - the semantic
 * quartet, the accent, the sidebar and the selected row - and the neutrals are
 * warm sunlight rather than the usual cool grey.
 *
 * The single exception is the light variant's `primary`: this app paints
 * `primary` as small text in ~30 places, and #067EE9 on white is 4.06:1, just
 * under AA. #0674D6 is the smallest darkening that clears it. Every other role
 * keeps the seed exactly, including `info`, which is the same blue as a fill.
 */
export const summer: ThemeFamily = {
    id: 'summer',
    label: 'Summer',
    light: {
        background: '#FFFCF2',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#FFF9E6',
        surfaceVariant: '#FFF3C4',
        onSurface: '#1A2733',
        onSurfaceVariant: '#1A2733',
        outline: '#E3D08F',
        primary: '#0674D6',
        secondary: '#0DD085',
        tertiary: '#F97904',
        error: '#E41312',
        info: '#067EE9',
        success: '#0DD085',
        warning: '#F97904',
        accent: '#FFE62D',
        menuBg: '#04406F',
        onMenuBg: '#FFFFFF',
        drawerBg: '#FFE62D',
        onDrawerBg: '#1A2733',
        workspace: '#FFF6DC',
        listRow: '#FFFFFF',
        listRowSelected: '#FFF3A0',
        listBorder: 'rgba(26, 39, 51, 0.28)',
        panelBorder: 'rgba(26, 39, 51, 0.50)',
        filterControlsBg: '#FFF6D4',
        drawerIcon: '#1A2733',
        drawerDivider: 'rgba(26, 39, 51, 0.22)',
        menuItemActive: 'rgba(255, 230, 45, 0.35)'
    },
    dark: {
        background: '#0A1420',
        surface: '#10202E',
        surfaceBright: '#1F3547',
        surfaceLight: '#162838',
        surfaceVariant: '#1A2F42',
        onSurface: '#EAF3FB',
        onSurfaceVariant: '#EAF3FB',
        outline: '#4A6379',
        primary: '#3FA3F5',
        secondary: '#0DD085',
        tertiary: '#F97904',
        error: '#FF4B4A',
        info: '#3FA3F5',
        success: '#0DD085',
        warning: '#F97904',
        accent: '#FFE62D',
        menuBg: '#041A2B',
        onMenuBg: '#EAF3FB',
        drawerBg: '#16283A',
        onDrawerBg: '#FFFFFF',
        workspace: '#071018',
        listRow: '#0F1E2B',
        listRowSelected: 'rgba(255, 230, 45, 0.22)',
        listBorder: 'rgba(255, 230, 45, 0.28)',
        panelBorder: 'rgba(255, 230, 45, 0.44)',
        filterControlsBg: '#08141F',
        menuItemActive: 'rgba(255, 230, 45, 0.28)'
    }
}
