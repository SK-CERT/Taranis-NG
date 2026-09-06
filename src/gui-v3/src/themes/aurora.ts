import type { ThemeFamily } from './types'

/**
 * Aurora - a night sky with northern lights, and the first family to use the
 * optional gradient tokens.
 *
 * Every gradient stays tonally close to the base colour underneath it. That is
 * a hard rule, not a style preference: the contrast contract measures text
 * against the base colour, so a gradient wandering far from it would make that
 * measurement a lie. The top bar sweeps between two shades of the same deep
 * teal-navy; the workspace carries the aurora itself, as translucent glows over
 * its base, and no text sits directly on it - the panels cover it.
 */
export const aurora: ThemeFamily = {
    id: 'aurora',
    label: 'Aurora',
    light: {
        background: '#EDF4F5',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#F4F9FA',
        surfaceVariant: '#DCE9EC',
        onSurface: '#0F2630',
        onSurfaceVariant: '#0F2630',
        outline: '#A6C1C8',
        primary: '#0F6E7A',
        secondary: '#3B5EA8',
        tertiary: '#6B4E9E',
        error: '#B3261E',
        info: '#0F6E7A',
        success: '#2E7D52',
        warning: '#A66300',
        accent: '#1E9E86',
        menuBg: '#0E2A33',
        onMenuBg: '#DCF0F0',
        menuGradient: 'linear-gradient(100deg, #0E2A33 0%, #124049 55%, #12324A 100%)',
        drawerBg: '#E1EDEF',
        onDrawerBg: '#0F2630',
        drawerGradient: 'linear-gradient(180deg, #E9F3F5 0%, #DAE8EB 100%)',
        workspace: '#DBE7EA',
        workspaceGradient:
            'radial-gradient(circle at 18% -10%, rgba(30, 158, 134, 0.20), transparent 58%), radial-gradient(circle at 88% 4%, rgba(107, 78, 158, 0.16), transparent 52%)',
        listRow: '#FFFFFF',
        listRowSelected: '#CFEDE4',
        listBorder: 'rgba(15, 38, 48, 0.26)',
        panelBorder: 'rgba(15, 38, 48, 0.48)',
        filterControlsBg: '#DFEBEE',
        menuItemActive: 'rgba(30, 158, 134, 0.34)'
    },
    dark: {
        background: '#08121A',
        surface: '#0F1C25',
        surfaceBright: '#1B3140',
        surfaceLight: '#13242F',
        surfaceVariant: '#162B36',
        onSurface: '#DCEAEC',
        onSurfaceVariant: '#DCEAEC',
        outline: '#41626E',
        primary: '#4FD1B5',
        secondary: '#8FA8E8',
        tertiary: '#C3A6F0',
        error: '#EF8A8A',
        info: '#4FD1B5',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#4FD1B5',
        menuBg: '#08191F',
        onMenuBg: '#DCEAEC',
        menuGradient: 'linear-gradient(100deg, #08191F 0%, #0D2E38 55%, #11223C 100%)',
        drawerBg: '#0D1F28',
        onDrawerBg: '#DCEAEC',
        drawerGradient: 'linear-gradient(180deg, #102530 0%, #0B1A22 100%)',
        workspace: '#060E14',
        workspaceGradient:
            'radial-gradient(circle at 16% -8%, rgba(79, 209, 181, 0.16), transparent 56%), radial-gradient(circle at 86% 6%, rgba(195, 166, 240, 0.14), transparent 50%)',
        listRow: '#0E1B23',
        listRowSelected: 'rgba(79, 209, 181, 0.22)',
        listBorder: 'rgba(220, 234, 236, 0.22)',
        panelBorder: 'rgba(220, 234, 236, 0.40)',
        filterControlsBg: '#0A151C',
        menuItemActive: 'rgba(79, 209, 181, 0.30)'
    }
}
