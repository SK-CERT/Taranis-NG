import type { ThemeFamily } from './types'

/**
 * Lavender - #cdc6ef and #d9e0e0.
 *
 * Both seeds are pale, so in the light variant they do the work a pale colour
 * can: #cdc6ef the table-header surface and the accent, #d9e0e0 the sidebar
 * and the selected row. `primary` is a deepened lavender, since neither seed
 * can carry text. The dark variant inverts that - there the two seeds are the
 * brightest things on screen, so they become primary and secondary.
 */
export const lavender: ThemeFamily = {
    id: 'lavender',
    label: 'Lavender',
    light: {
        background: '#F6F4FC',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#F2EFFA',
        surfaceVariant: '#CDC6EF',
        onSurface: '#241F38',
        onSurfaceVariant: '#241F38',
        outline: '#BDB5E0',
        primary: '#5B4CA8',
        secondary: '#4E7C74',
        tertiary: '#8A6BA8',
        error: '#C62828',
        info: '#4A6FA5',
        success: '#3F7D53',
        warning: '#A66300',
        accent: '#CDC6EF',
        menuBg: '#322A52',
        onMenuBg: '#EDE9FA',
        drawerBg: '#D9E0E0',
        onDrawerBg: '#241F38',
        workspace: '#E8E4F4',
        listRow: '#FFFFFF',
        listRowSelected: '#D9E0E0',
        listBorder: 'rgba(70, 60, 110, 0.30)',
        panelBorder: 'rgba(70, 60, 110, 0.52)',
        filterControlsBg: '#E6E2F2',
        menuItemActive: 'rgba(205, 198, 239, 0.32)'
    },
    dark: {
        background: '#14121C',
        surface: '#1C1926',
        surfaceBright: '#2E2A3D',
        surfaceLight: '#232030',
        surfaceVariant: '#272335',
        onSurface: '#E9E5F6',
        onSurfaceVariant: '#E9E5F6',
        outline: '#5A5470',
        primary: '#CDC6EF',
        secondary: '#D9E0E0',
        tertiary: '#A98FD6',
        error: '#EF8A8A',
        info: '#9FB6E8',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#CDC6EF',
        menuBg: '#100E17',
        onMenuBg: '#E9E5F6',
        drawerBg: '#221E2E',
        onDrawerBg: '#FFFFFF',
        workspace: '#100E16',
        listRow: '#1A1724',
        listRowSelected: 'rgba(205, 198, 239, 0.22)',
        listBorder: 'rgba(205, 198, 239, 0.28)',
        panelBorder: 'rgba(205, 198, 239, 0.46)',
        filterControlsBg: '#15121D',
        menuItemActive: 'rgba(205, 198, 239, 0.30)'
    }
}
