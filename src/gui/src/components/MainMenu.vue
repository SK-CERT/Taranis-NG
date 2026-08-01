<template>
    <v-app-bar
        app
        clipped-left
        density="compact"
        color="surface"
    >
        <!-- Menu toggle button -->
        <v-app-bar-nav-icon
            v-if="isAuthenticated"
            color="white"
            @click="toggleNav"
        />

        <!-- Logo -->
        <div class="d-flex align-center justify-start">
            <v-img
                :src="isDark ? darkLogo : lightLogo"
                alt="Taranis NG"
                contain
                height="48"
                width="auto"
            />
        </div>

        <v-spacer />
        <!-- Main navigation buttons -->
        <template v-if="isAuthenticated">
            <v-btn
                v-for="button in visibleButtons"
                :key="button.routeName"
                :to="button.route"
                :variant="isButtonActive(button) ? 'outlined' : 'text'"
                :color="isButtonActive(button) ? 'primary' : undefined"
                :opacity="isButtonActive(button) ? 1 : 0.85"
            >
                <v-icon start>
                    {{ button.icon }}
                </v-icon>
                {{ t(button.title) }}
            </v-btn>
        </template>

        <v-divider
            vertical
            class="mx-2"
        />

        <!-- User menu -->
        <UserMenu v-if="isAuthenticated" />
    </v-app-bar>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useRoute } from 'vue-router'
    import { useAuth } from '@/composables/useAuth'
    import { ICONS } from '@/config/ui-constants'
    import UserMenu from './UserMenu.vue'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import type { PermissionKey } from '@/types/permissions'
    import { useTheme } from 'vuetify'
    import lightLogo from '@/assets/taranis-logo-nav.svg'
    import darkLogo from '@/assets/taranis-logo-nav-dark.svg'

    // useTheme() must be called at the top of setup, NOT inside a computed()
    // getter — the getter runs lazily during async re-computation (e.g. an
    // axios response updating the auth store), where getCurrentInstance() is
    // null, and Vuetify's useTheme() asserts its presence. See Login.vue.
    const { global: themeGlobal } = useTheme()
    const isDark = computed(() => themeGlobal.current.value.dark)
    const { t } = useI18n()
    const { isAuth, checkPermission } = useAuth()
    const route = useRoute()

    type MenuButton = {
        title: string
        icon: string
        permission: PermissionKey
        route: string
        routeName: string
        show: boolean
    }

    const buttons: MenuButton[] = [
        {
            title: 'main_menu.dashboard',
            icon: ICONS.CHART_BOX,
            permission: 'ASSESS_ACCESS',
            route: '/dashboard',
            routeName: 'dashboard',
            show: true
        },

        {
            title: 'main_menu.assess',
            icon: ICONS.NEWSPAPER_VARIANT,
            permission: 'ASSESS_ACCESS',
            route: '/assess',
            routeName: 'assess',
            show: true
        },
        {
            title: 'main_menu.analyze',
            icon: ICONS.FILE_TABLE,
            permission: 'ANALYZE_ACCESS',
            route: '/analyze/local',
            routeName: 'analyze',
            show: true
        },
        {
            title: 'main_menu.publish',
            icon: ICONS.SEND,
            permission: 'PUBLISH_ACCESS',
            route: '/publish',
            routeName: 'publish',
            show: true
        },
        {
            title: 'main_menu.config',
            icon: ICONS.COG,
            permission: 'CONFIG_ACCESS',
            route: '/config',
            routeName: 'config',
            show: true
        }
    ]

    const isAuthenticated = computed(() => isAuth.value)

    const visibleButtons = computed(() => {
        return buttons.filter((button) => {
            return checkPermission(PERMISSIONS[button.permission]) && button.show
        })
    })

    const isButtonActive = (button: MenuButton): boolean => {
        if (route.name === button.routeName) {
            return true
        }
        // Config groups many child routes (collectors, reports, ...) under /config/*
        // with their own names, so match by the top-level path segment instead.
        const base = '/' + button.route.split('/')[1]
        return route.path === base || route.path.startsWith(base + '/')
    }

    const toggleNav = (): void => {
        window.dispatchEvent(new Event('nav-clicked'))
    }

    // No additional onMounted logic needed
</script>
