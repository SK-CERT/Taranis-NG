import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // State
  const user = ref({
    id: '',
    name: '',
    organization_name: '',
    permissions: []
  })

  const verticalView = ref(localStorage.getItem('TNGVericalView') === 'true' || false)

  // Getters
  const userId = computed(() => user.value.id)
  const userName = computed(() => user.value.name)
  const organizationName = computed(() => user.value.organization_name)
  const permissions = computed(() => user.value.permissions)

  // Actions
  function setUser(userData) {
    if (userData) {
      user.value = {
        id: userData.id || '',
        name: userData.name || '',
        organization_name: userData.organization_name || '',
        permissions: userData.permissions || []
      }
    }
  }

  function clearUser() {
    user.value = {
      id: '',
      name: '',
      organization_name: '',
      permissions: []
    }
  }

  function setVerticalView(value) {
    verticalView.value = value
    localStorage.setItem('TNGVericalView', value)
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
