import type { ThemeFamily } from './types'

/**
 * Retro Dynasty - https://www.schemecolor.com/retro-dynasty-2.php
 * Manhattan Red #AD2800, Yellow Leather #E5A638, Comfort Yellow #ECD27E,
 * Elm #217C83.
 *
 * All four are used verbatim in the light variant, on the surfaces that show
 * them: Manhattan Red is the top bar and the panel borders, Comfort Yellow the
 * sidebar, the table headers and the selected row, Yellow Leather the accent
 * and the warning, and Elm - which clears AA as text at 4.91:1 - is `primary`.
 *
 * The dark variant keeps the red bar and both yellows exactly; only Elm is
 * lightened, because #217C83 against a dark surface is 3.56:1.
 */
export const retro: ThemeFamily = {
    id: 'retro',
    label: 'Retro',
    light: {
        background: '#FBF4E4',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#F9F0DC',
        surfaceVariant: '#ECD27E',
        onSurface: '#2A1A08',
        onSurfaceVariant: '#2A1A08',
        outline: '#D3B87C',
        primary: '#217C83',
        secondary: '#AD2800',
        tertiary: '#E5A638',
        error: '#C62828',
        info: '#217C83',
        success: '#2E7D32',
        warning: '#E5A638',
        accent: '#E5A638',
        menuBg: '#AD2800',
        onMenuBg: '#FFFFFF',
        drawerBg: '#ECD27E',
        onDrawerBg: '#2A1A08',
        workspace: '#F2E6C8',
        listRow: '#FFFFFF',
        listRowSelected: '#ECD27E',
        listBorder: 'rgba(173, 40, 0, 0.30)',
        panelBorder: 'rgba(173, 40, 0, 0.52)',
        filterControlsBg: '#F3E7C9',
        drawerIcon: '#2A1A08',
        drawerDivider: 'rgba(42, 26, 8, 0.22)',
        menuItemActive: 'rgba(229, 166, 56, 0.45)'
    },
    dark: {
        background: '#17100A',
        surface: '#21180F',
        surfaceBright: '#38291A',
        surfaceLight: '#2A1F14',
        surfaceVariant: '#2F2416',
        onSurface: '#F6E9CE',
        onSurfaceVariant: '#F6E9CE',
        outline: '#6F5C3C',
        primary: '#4FB3B8',
        secondary: '#E5A638',
        tertiary: '#ECD27E',
        error: '#F0705C',
        info: '#4FB3B8',
        success: '#7FC796',
        warning: '#E5A638',
        accent: '#E5A638',
        menuBg: '#AD2800',
        onMenuBg: '#FFFFFF',
        drawerBg: '#2A1F14',
        onDrawerBg: '#FFFFFF',
        workspace: '#130D08',
        listRow: '#1F170E',
        listRowSelected: 'rgba(236, 210, 126, 0.22)',
        listBorder: 'rgba(236, 210, 126, 0.32)',
        panelBorder: 'rgba(236, 210, 126, 0.50)',
        filterControlsBg: '#180F09',
        menuItemActive: 'rgba(236, 210, 126, 0.38)'
    }
}
