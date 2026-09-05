import type { ThemeFamily } from './types'

/**
 * CESNET - #0068A2, #5A5A5A, #AAAAAA, #FFFFFF.
 *
 * A four-colour institutional palette: one blue and a neutral ramp. The blue
 * clears AA as text on white (5.93:1) so it is `primary` verbatim, and the two
 * greys land where greys belong - #5A5A5A the secondary and the borders,
 * #AAAAAA the outline. Only the semantic quartet is borrowed from outside the
 * palette, because a status colour has to stay recognisable.
 */
export const cesnet: ThemeFamily = {
    id: 'cesnet',
    label: 'CESNET',
    light: {
        background: '#F4F6F8',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#EFF2F5',
        surfaceVariant: '#E4E9ED',
        onSurface: '#3A3A3A',
        onSurfaceVariant: '#3A3A3A',
        outline: '#AAAAAA',
        primary: '#0068A2',
        secondary: '#5A5A5A',
        tertiary: '#4A6E85',
        error: '#C62828',
        info: '#0068A2',
        success: '#2E7D32',
        warning: '#A66300',
        accent: '#4CA6D9',
        menuBg: '#00456B',
        onMenuBg: '#FFFFFF',
        drawerBg: '#E9EEF2',
        onDrawerBg: '#3A3A3A',
        workspace: '#E7EBEF',
        listRow: '#FFFFFF',
        listRowSelected: '#D6E9F5',
        listBorder: 'rgba(90, 90, 90, 0.34)',
        panelBorder: 'rgba(90, 90, 90, 0.55)',
        filterControlsBg: '#E8EDF1',
        menuItemActive: 'rgba(255, 255, 255, 0.18)'
    },
    dark: {
        background: '#121618',
        surface: '#1A2023',
        surfaceBright: '#2C3438',
        surfaceLight: '#212829',
        surfaceVariant: '#252D30',
        onSurface: '#E8ECEF',
        onSurfaceVariant: '#E8ECEF',
        outline: '#5A5A5A',
        primary: '#4CA6D9',
        secondary: '#AAAAAA',
        tertiary: '#7FC1E0',
        error: '#EF8A8A',
        info: '#4CA6D9',
        success: '#7FC796',
        warning: '#E8B15C',
        accent: '#0068A2',
        menuBg: '#062F47',
        onMenuBg: '#FFFFFF',
        drawerBg: '#202729',
        onDrawerBg: '#FFFFFF',
        workspace: '#0E1214',
        listRow: '#191F22',
        listRowSelected: 'rgba(76, 166, 217, 0.24)',
        listBorder: 'rgba(170, 170, 170, 0.34)',
        panelBorder: 'rgba(170, 170, 170, 0.52)',
        filterControlsBg: '#14191B',
        menuItemActive: 'rgba(76, 166, 217, 0.30)'
    }
}
