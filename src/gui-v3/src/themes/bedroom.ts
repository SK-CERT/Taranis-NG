import type { ThemeFamily } from './types'

/**
 * Bedroom - #194357 Bleu Nuit, #575419 Vert Olive, #571920 Bordeaux Profond,
 * #AC6B73 Rose Patine, #A9C8D6 Bleu Brume. A dim, warm room: night-blue
 * shadow, olive throw, wine headboard, dusty rose linen and misty morning light.
 *
 * Roles follow what each colour can carry rather than its name. Bordeaux is the
 * strongest text colour in the set (13.4:1 on white) so it becomes the light
 * variant's body text; Bleu Nuit takes `primary` at 10.6:1 and the top bar;
 * Bleu Brume is too light to be text (1.8:1) so it is the sidebar, the bar's
 * lettering and - inverted - the dark variant's body text.
 *
 * Rose Patine is the one that needs care. At 4.1:1 on white it is just under AA
 * as text and only 3.8:1 on a dark surface, so it never takes a text role:
 * it lives on the card and panel borders, the hovered and selected row, the
 * table headers and the active nav item, where it is unmissable. `accent` and
 * `secondary` alone would have hidden it, as this app renders neither.
 */
export const bedroom: ThemeFamily = {
    id: 'bedroom',
    label: 'Bedroom',
    light: {
        background: '#D3E4EC',
        surface: '#FFFFFF',
        surfaceBright: '#FFFFFF',
        surfaceLight: '#F1F7FA',
        surfaceVariant: '#E3CDD1',
        onSurface: '#571920',
        onSurfaceVariant: '#571920',
        outline: '#9FB3BF',
        primary: '#194357',
        secondary: '#575419',
        tertiary: '#AC6B73',
        error: '#A32430',
        info: '#194357',
        success: '#575419',
        warning: '#A66300',
        accent: '#AC6B73',
        menuBg: '#194357',
        onMenuBg: '#A9C8D6',
        drawerBg: '#A9C8D6',
        onDrawerBg: '#571920',
        workspace: '#C3D9E3',
        listRow: '#FFFFFF',
        listRowSelected: '#E8D0D4',
        listRowHover: 'rgba(172, 107, 115, 0.14)',
        listBorder: 'rgba(172, 107, 115, 0.65)',
        panelBorder: 'rgba(87, 25, 32, 0.55)',
        filterControlsBg: '#CFE1E9',
        menuItemActive: 'rgba(172, 107, 115, 0.55)'
    },
    dark: {
        background: '#101C24',
        surface: '#16262F',
        surfaceBright: '#243C48',
        surfaceLight: '#1B2E38',
        surfaceVariant: '#2B2126',
        onSurface: '#A9C8D6',
        onSurfaceVariant: '#A9C8D6',
        outline: '#4A6675',
        primary: '#C98A92',
        secondary: '#A9C8D6',
        tertiary: '#9AA83C',
        error: '#D96A72',
        info: '#A9C8D6',
        success: '#9AA83C',
        warning: '#D9A05A',
        accent: '#AC6B73',
        menuBg: '#194357',
        onMenuBg: '#A9C8D6',
        drawerBg: '#1B2E38',
        onDrawerBg: '#A9C8D6',
        workspace: '#0C161C',
        listRow: '#15242C',
        listRowSelected: 'rgba(172, 107, 115, 0.32)',
        listRowHover: 'rgba(172, 107, 115, 0.16)',
        listBorder: 'rgba(172, 107, 115, 0.48)',
        panelBorder: 'rgba(172, 107, 115, 0.70)',
        filterControlsBg: '#0F1A21',
        menuItemActive: 'rgba(172, 107, 115, 0.48)'
    }
}
