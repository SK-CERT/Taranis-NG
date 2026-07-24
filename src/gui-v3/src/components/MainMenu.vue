<template>
    <v-app-bar
        app
        clipped-left
        height="60"
        color="surface"
        class="main-menu"
    >
        <!-- Menu toggle button -->
        <v-app-bar-nav-icon
            v-if="isAuthenticated && showNavToggle"
            color="primary"
            class="menu-toggle"
            @click="toggleNav"
        />

        <!-- Logo -->
        <router-link
            to="/dashboard"
            class="brand-link"
        >
            <v-img
                :src="darkLogo"
                alt="Taranis NG"
                contain
                height="42"
                width="148"
            />
        </router-link>

        <v-spacer />
        <!-- Main navigation buttons -->
        <nav
            v-if="isAuthenticated"
            class="primary-navigation"
            :aria-label="t('main_menu.dashboard')"
        >
            <v-btn
                v-for="button in visibleButtons"
                :key="button.routeName"
                :to="button.route"
                variant="text"
                :class="{ 'primary-navigation__item--active': isButtonActive(button) }"
                class="primary-navigation__item"
                :aria-current="isButtonActive(button) ? 'page' : undefined"
            >
                <v-icon start>
                    {{ button.icon }}
                </v-icon>
                <span class="primary-navigation__label">{{ t(button.title) }}</span>
            </v-btn>
        </nav>

        <v-divider
            vertical
            class="menu-divider mx-3"
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
    import Permissions from '@/services/permissions'
    import type { PermissionKey } from '@/types/permissions'
    import darkLogo from '@/assets/taranis-logo-nav-dark.svg'

    withDefaults(
        defineProps<{
            showNavToggle?: boolean
        }>(),
        {
            showNavToggle: true
        }
    )
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
            title: 'main_menu.my_assets',
            icon: ICONS.FILE_CABINET,
            permission: 'MY_ASSETS_ACCESS',
            route: '/myassets',
            routeName: 'myassets',
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
            return checkPermission(Permissions[button.permission]) && button.show
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

<style scoped>
    .main-menu {
        border-bottom: 1px solid rgba(255, 255, 255, 0.13) !important;
        background: #071724 !important;
        color: #eef6fc !important;
        box-shadow: 0 2px 8px rgba(8, 26, 40, 0.22) !important;
    }

    .main-menu :deep(.v-toolbar__content) {
        padding-inline: clamp(0.6rem, 2vw, 1.5rem);
        gap: 0.35rem;
    }

    .menu-toggle {
        margin-inline-end: 0.25rem;
        color: #b9ddf7 !important;
    }

    .brand-link {
        display: flex;
        align-items: center;
        flex: 0 0 auto;
        padding: 0.25rem 0.45rem;
        border-radius: 3px;
    }

    .primary-navigation {
        display: flex;
        align-items: center;
        gap: 0.15rem;
    }

    .primary-navigation__item {
        min-width: 0;
        min-height: 36px;
        padding-inline: 0.85rem;
        border-radius: 3px;
        color: rgba(238, 246, 252, 0.76);
        font-weight: 600;
        letter-spacing: 0.015em;
        text-transform: none;
    }

    .primary-navigation__item:hover {
        color: #ffffff;
        background: rgba(255, 255, 255, 0.1);
    }

    .primary-navigation__item--active {
        color: #ffffff;
        background: rgba(88, 167, 232, 0.18);
        box-shadow: none;
    }

    @media (max-width: 1260px) {
        .primary-navigation__item {
            padding-inline: 0.65rem;
        }
    }

    @media (max-width: 1080px) {
        .brand-link :deep(.v-img) {
            width: 116px !important;
        }

        .primary-navigation__label {
            display: none;
        }

        .primary-navigation__item {
            min-width: 36px;
            padding-inline: 0.55rem;
        }

        .primary-navigation__item :deep(.v-icon) {
            margin-inline-end: 0;
        }
    }

    @media (max-width: 680px) {
        .brand-link {
            display: none;
        }

        .main-menu :deep(.v-toolbar__content) {
            padding-inline: 0.35rem;
        }

        .primary-navigation {
            overflow-x: auto;
        }

        .menu-divider {
            margin-inline: 0.25rem !important;
        }
    }
</style>
