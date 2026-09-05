import type { ThemeFamily } from './types'

/** The two pastel seeds play off each other: #f0cac8 carries the surfaces,
 *  #b0f9fa the accent and the selected row. `primary` is a deep teal drawn
 *  from the cyan so controls stay legible against the pale pink ground.
 *
 *  The dark variant swaps the two seeds over: the mint tints the surfaces and
 *  the pink becomes the accent - `primary`, the borders, the selected row and
 *  the active nav item. Holding the pink in `secondary`/`accent` alone is not
 *  enough, because this app barely renders either role. */
export const bubblegum: ThemeFamily = {
    id: 'bubblegum',
    label: 'Bubblegum',
    light: {
        background: '#FDF4F3',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#FBEDEC',
        surfaceVariant: '#F0CAC8',
        onSurface: '#322226',
        onSurfaceVariant: '#322226',
        outline: '#DCAFAD',
        primary: '#0E7C8A',
        secondary: '#C2596B',
        tertiary: '#7A5AA8',
        error: '#C62828',
        info: '#0E7C8A',
        success: '#2E7D32',
        warning: '#B26B00',
        accent: '#B0F9FA',
        menuBg: '#12454B',
        onMenuBg: '#DFFDFD',
        drawerBg: '#F5DBDA',
        onDrawerBg: '#322226',
        workspace: '#F2DEDD',
        listRow: '#FFFFFF',
        listRowSelected: '#B0F9FA',
        listBorder: 'rgba(120, 74, 78, 0.34)',
        panelBorder: 'rgba(120, 74, 78, 0.58)',
        filterControlsBg: '#F3DFDE',
        menuItemActive: 'rgba(176, 249, 250, 0.30)'
    },
    dark: {
        background: '#101A1A',
        surface: '#162325',
        surfaceBright: '#27383A',
        surfaceLight: '#1D2C2E',
        surfaceVariant: '#213033',
        onSurface: '#E6F5F3',
        onSurfaceVariant: '#E6F5F3',
        outline: '#4E6A6B',
        primary: '#F0CAC8',
        secondary: '#B0F9FA',
        tertiary: '#C9A7E8',
        error: '#FF7B72',
        info: '#B0F9FA',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#F0CAC8',
        menuBg: '#0A1516',
        onMenuBg: '#E6F5F3',
        drawerBg: '#1B2A2C',
        onDrawerBg: '#FFFFFF',
        workspace: '#0C1516',
        listRow: '#152224',
        listRowSelected: 'rgba(240, 202, 200, 0.24)',
        listBorder: 'rgba(240, 202, 200, 0.32)',
        panelBorder: 'rgba(240, 202, 200, 0.50)',
        filterControlsBg: '#0F1B1C',
        menuItemActive: 'rgba(240, 202, 200, 0.30)'
    }
}
