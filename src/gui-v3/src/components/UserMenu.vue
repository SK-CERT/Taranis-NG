<template>
    <div class="user-menu">
        <!-- User Menu -->
        <v-menu offset-y>
            <template #activator="{ props }">
                <v-btn
                    data-test="user-menu"
                    icon
                    v-bind="props"
                >
                    <v-icon>mdi-shield-account</v-icon>
                </v-btn>
            </template>

            <v-list>
                <!-- User info -->
                <v-list-item>
                    <template #prepend>
                        <v-avatar color="primary">
                            <v-icon color="white">mdi-shield-account</v-icon>
                        </v-avatar>
                    </template>
                    <v-list-item-title>{{ username }}</v-list-item-title>
                    <v-list-item-subtitle>{{ organizationName }}</v-list-item-subtitle>
                </v-list-item>

                <v-divider />

                <!-- Settings -->
                <v-list-item @click="showSettings">
                    <template #prepend>
                        <v-icon>mdi-account-cog</v-icon>
                    </template>
                    <v-list-item-title>{{ t('user_menu.settings') }}</v-list-item-title>
                </v-list-item>

                <!-- Logout -->
                <v-list-item
                    data-test="logout-action"
                    @click="handleLogout"
                >
                    <template #prepend>
                        <v-icon>mdi-logout</v-icon>
                    </template>
                    <v-list-item-title>{{ t('user_menu.logout') }}</v-list-item-title>
                </v-list-item>
            </v-list>
        </v-menu>

        <!-- User Settings Dialog (includes Security tab) -->
        <UserSettings v-model="settingsVisible" />
    </div>
</template>

<script setup lang="ts">
    import { ref, computed } from 'vue'
    import { useRouter } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { useAuthStore } from '@/stores/auth'
    import { useUserStore } from '@/stores/user'
    import UserSettings from './UserSettings.vue'

    const { t } = useI18n()
    const router = useRouter()
    const authStore = useAuthStore()
    const userStore = useUserStore()

    const settingsVisible = ref<boolean>(false)

    const username = computed(() => userStore.userName || 'User')
    const organizationName = computed(() => userStore.organizationName || 'No Organization')

    const showSettings = (): void => {
        settingsVisible.value = true
    }

    const handleLogout = async (): Promise<void> => {
        try {
            await authStore.logout()
            if (authStore.hasExternalLogoutUrl) {
                window.location.href = authStore.getLogoutURL
            } else {
                router.push('/login')
            }
        } catch (error: unknown) {
            console.error('Logout error:', error)
        }
    }
</script>

<style scoped>
    .user-menu {
        display: flex;
        align-items: center;
    }
</style>
