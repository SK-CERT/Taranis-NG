import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { UserClaims } from '@/types/auth'
import type { PermissionKey } from '@/types/permissions'

type UserState = {
    id: string | number
    name: string
    organization_name: string
    permissions: PermissionKey[]
}

const emptyUser = (): UserState => ({
    id: '',
    name: '',
    organization_name: '',
    permissions: []
})

export const useUserStore = defineStore('user', () => {
    // State
    const user = ref<UserState>(emptyUser())

    // Keep the existing key spelling for backward compatibility.
    const verticalView = ref(localStorage.getItem('TNGVericalView') === 'true' || false)

    // Getters
    const userId = computed(() => user.value.id)
    const userName = computed(() => user.value.name)
    const organizationName = computed(() => user.value.organization_name)
    const permissions = computed(() => user.value.permissions)

    // Actions
    function setUser(userData?: Partial<UserClaims> | null): void {
        if (userData) {
            user.value = {
                id: userData.id || '',
                name: userData.name || '',
                organization_name: userData.organization_name || '',
                permissions: Array.isArray(userData.permissions) ? userData.permissions : []
            }
        }
    }

    function clearUser(): void {
        user.value = emptyUser()
    }

    function setVerticalView(value: boolean): void {
        verticalView.value = value
        localStorage.setItem('TNGVericalView', String(value))
    }

    return {
        // State
        user,
        verticalView,

        // Getters
        userId,
        userName,
        organizationName,
        permissions,

        // Actions
        setUser,
        clearUser,
        setVerticalView
    }
})
