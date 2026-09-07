import type { ThemeFamily } from './types'

/**
 * The original Taranis-NG palette.
 *
 * Values are carried over verbatim from the former inline theme block in
 * `main.ts` and from the `[data-theme]` blocks of `styles/colors.css`, so
 * selecting this family reproduces the pre-theming appearance exactly.
 *
 * `surfaceBright` / `surfaceLight` / `onSurfaceVariant` are deliberately left
 * unset here: this family never defined them, so it keeps inheriting Vuetify's
 * defaults. The other families do set them.
 */
export const taranis: ThemeFamily = {
    id: 'taranis',
    label: 'Taranis-NG',
    light: {
        background: '#F2F5F9',
        surface: '#FFFFFF',
        surfaceVariant: '#EAF0F6',
        onSurface: '#172333',
        outline: '#B8C5D2',
        primary: '#176FB5',
        onPrimary: '#FFFFFF',
        secondary: '#00677F',
        onSecondary: '#FFFFFF',
        tertiary: '#4E55B0',
        onTertiary: '#FFFFFF',
        error: '#FF5252',
        onError: '#FFFFFF',
        info: '#2196F3',
        onInfo: '#FFFFFF',
        success: '#4CAF50',
        onSuccess: '#FFFFFF',
        warning: '#FB8C00',
        onWarning: '#FFFFFF',
        accent: '#82B1FF',
        menuBg: '#071724',
        onMenuBg: '#EEF6FC',
        drawerBg: '#DFE8F0',
        onDrawerBg: '#000000',
        workspace: '#D7E1E9',
        listRow: '#FFFFFF',
        menuItemActive: 'rgba(88, 167, 232, 0.18)',
        listRowSelected: '#FFF3CD',
        listBorder: 'rgba(52, 82, 104, 0.34)',
        panelBorder: 'rgba(52, 82, 104, 0.58)',
        filterControlsBg: '#D8E3EB',
        drawerIcon: 'rgba(0, 0, 0, 0.54)',
        drawerDivider: 'rgba(0, 0, 0, 0.12)'
    },
    dark: {
        background: '#0D1621',
        surface: '#152230',
        surfaceVariant: '#203040',
        onSurface: '#E8EEF5',
        outline: '#526273',
        primary: '#58A7E8',
        onPrimary: '#FFFFFF',
        secondary: '#64D4F8',
        onSecondary: '#003543',
        tertiary: '#BEC2FF',
        onTertiary: '#1D2380',
        error: '#CF6679',
        onError: '#690005',
        info: '#2196F3',
        success: '#4CAF50',
        warning: '#FB8C00',
        accent: '#82B1FF',
        menuBg: '#071724',
        onMenuBg: '#EEF6FC',
        drawerBg: '#1B3549',
        onDrawerBg: '#FFFFFF',
        workspace: '#07141E',
        listRow: '#132838',
        menuItemActive: 'rgba(88, 167, 232, 0.18)',
        listRowSelected: 'rgba(var(--v-theme-primary), 0.22)',
        listBorder: 'rgba(126, 169, 198, 0.38)',
        panelBorder: 'rgba(126, 169, 198, 0.58)',
        filterControlsBg: '#0A1B28',
        drawerIcon: '#FFFFFF',
        drawerDivider: 'rgba(255, 255, 255, 0.2)'
    }
}
