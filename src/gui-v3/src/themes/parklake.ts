import type { ThemeFamily } from './types'

/**
 * Park Lake - #0A3323 dark green, #839958 moss green, #F7F4D5 beige,
 * #D3968C rosy brown, #105666 midnight green. A water-lily pond: deep green
 * shade, sunlit beige water, moss, lily pink and the teal of open water.
 *
 * All five are used verbatim. The dark green is both the body text and the top
 * bar (13.9:1 on white, 12.5:1 under beige), beige is the light ground and the
 * dark variant's text, midnight green clears AA as light `primary` at 8.25:1
 * and moss does the same on dark at 4.87:1, so neither needs adjusting. Only
 * midnight green cannot cross over - at 1.86:1 on a dark surface it is
 * lightened for the dark variant's teal accents.
 *
 * The rosy brown is the lily pink, and it has to land on surfaces that actually
 * paint: the table headers, the selected and hovered row, the card and panel
 * borders, and the active nav item on the green bar. Holding it in `accent` and
 * `secondary` left it invisible, because this app renders neither.
 */
export const parklake: ThemeFamily = {
    id: 'parklake',
    label: 'Park Lake',
    light: {
        background: '#F7F4D5',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#FBF9E6',
        surfaceVariant: '#E9CFC8',
        onSurface: '#0A3323',
        onSurfaceVariant: '#0A3323',
        outline: '#C6C79C',
        primary: '#105666',
        secondary: '#0A3323',
        tertiary: '#839958',
        error: '#B3261E',
        info: '#105666',
        success: '#5C7A33',
        warning: '#A66300',
        accent: '#D3968C',
        menuBg: '#0A3323',
        onMenuBg: '#F7F4D5',
        drawerBg: '#E7E4C0',
        onDrawerBg: '#0A3323',
        workspace: '#EDE9C8',
        listRow: '#FFFFFF',
        listRowSelected: '#D3968C',
        listRowHover: 'rgba(211, 150, 140, 0.16)',
        listBorder: 'rgba(211, 150, 140, 0.70)',
        panelBorder: 'rgba(196, 122, 110, 0.85)',
        filterControlsBg: '#EEEBC9',
        menuItemActive: 'rgba(211, 150, 140, 0.45)'
    },
    dark: {
        background: '#071A14',
        surface: '#0D2A20',
        surfaceBright: '#1A4534',
        surfaceLight: '#103326',
        surfaceVariant: '#12392B',
        onSurface: '#F7F4D5',
        onSurfaceVariant: '#F7F4D5',
        outline: '#47705C',
        primary: '#D3968C',
        secondary: '#105666',
        tertiary: '#4CA3B8',
        error: '#E8776B',
        info: '#4CA3B8',
        success: '#A3B86E',
        warning: '#E0A94A',
        accent: '#D3968C',
        menuBg: '#0A3323',
        onMenuBg: '#F7F4D5',
        drawerBg: '#103326',
        onDrawerBg: '#F7F4D5',
        workspace: '#061711',
        listRow: '#0C2519',
        listRowSelected: 'rgba(211, 150, 140, 0.30)',
        listRowHover: 'rgba(211, 150, 140, 0.16)',
        listBorder: 'rgba(211, 150, 140, 0.50)',
        panelBorder: 'rgba(211, 150, 140, 0.72)',
        filterControlsBg: '#081E17',
        menuItemActive: 'rgba(211, 150, 140, 0.42)'
    }
}
