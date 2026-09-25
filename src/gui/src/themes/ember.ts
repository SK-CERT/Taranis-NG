import type { ThemeFamily } from './types'

/**
 * Ember - dusk over banked coals: warm ash surfaces, a horizon sweep across the
 * top bar and a low glow under the workspace.
 *
 * Same rule as Aurora: each gradient stays within a tone or two of the base
 * colour it sits on, so the contrast the theme contract measures against that
 * base still describes what the text actually sits on. The strongest colour -
 * the ember orange - appears as translucent glow on the workspace, which no
 * text touches directly, and as the accent everywhere else.
 */
export const ember: ThemeFamily = {
    id: 'ember',
    label: 'Ember',
    light: {
        background: '#FAF3EC',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#FDF7F1',
        surfaceVariant: '#F2E3D6',
        onSurface: '#2E1C12',
        onSurfaceVariant: '#2E1C12',
        outline: '#D6BCA6',
        primary: '#A34418',
        secondary: '#7A4A2C',
        tertiary: '#8A6A1F',
        error: '#B3261E',
        info: '#2A6099',
        success: '#3F7D3A',
        warning: '#A66300',
        accent: '#E2712C',
        menuBg: '#2B1710',
        onMenuBg: '#F7E6D8',
        menuGradient: 'linear-gradient(100deg, #2B1710 0%, #45241A 58%, #35201B 100%)',
        drawerBg: '#F1E4D7',
        onDrawerBg: '#2E1C12',
        drawerGradient: 'linear-gradient(180deg, #F6EBE0 0%, #EDDFD0 100%)',
        workspace: '#F0E3D6',
        workspaceGradient:
            'radial-gradient(circle at 22% -10%, rgba(226, 113, 44, 0.22), transparent 56%), radial-gradient(circle at 84% 8%, rgba(163, 68, 24, 0.14), transparent 50%)',
        listRow: '#FFFFFF',
        listRowSelected: '#FBDDBF',
        listBorder: 'rgba(46, 28, 18, 0.24)',
        panelBorder: 'rgba(46, 28, 18, 0.46)',
        filterControlsBg: '#F3E6DA',
        menuItemActive: 'rgba(226, 113, 44, 0.40)'
    },
    dark: {
        background: '#150E0B',
        surface: '#1F1611',
        surfaceBright: '#372620',
        surfaceLight: '#261B15',
        surfaceVariant: '#2C1F18',
        onSurface: '#F3E3D5',
        onSurfaceVariant: '#F3E3D5',
        outline: '#6B5244',
        primary: '#E2712C',
        secondary: '#D9A066',
        tertiary: '#C9B26A',
        error: '#EF8A8A',
        info: '#8FB6DD',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#E2712C',
        menuBg: '#170D09',
        onMenuBg: '#F3E3D5',
        menuGradient: 'linear-gradient(100deg, #170D09 0%, #2E1912 58%, #221510 100%)',
        drawerBg: '#241913',
        onDrawerBg: '#F3E3D5',
        drawerGradient: 'linear-gradient(180deg, #2A1D16 0%, #1D1410 100%)',
        workspace: '#100A07',
        workspaceGradient:
            'radial-gradient(circle at 20% -8%, rgba(226, 113, 44, 0.18), transparent 54%), radial-gradient(circle at 86% 6%, rgba(201, 178, 106, 0.12), transparent 48%)',
        listRow: '#1E1510',
        listRowSelected: 'rgba(226, 113, 44, 0.26)',
        listBorder: 'rgba(243, 227, 213, 0.22)',
        panelBorder: 'rgba(243, 227, 213, 0.40)',
        filterControlsBg: '#130C09',
        menuItemActive: 'rgba(226, 113, 44, 0.36)'
    }
}
