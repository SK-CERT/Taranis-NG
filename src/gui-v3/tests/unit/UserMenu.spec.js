import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mountWithPlugins } from '../helpers/mount-helpers'
import UserMenu from '@/components/UserMenu.vue'

const mockRouterReplace = vi.fn()
const mockLogout = vi.fn()

vi.mock('vue-router', () => ({
    useRouter: () => ({ replace: mockRouterReplace })
}))

vi.mock('@/stores/auth', () => ({
    useAuthStore: () => ({
        logout: mockLogout,
        hasExternalLogoutUrl: false,
        getLogoutURL: '/logout'
    })
}))

vi.mock('@/stores/user', () => ({
    useUserStore: () => ({
        userName: 'Analyst',
        organizationName: 'CERT'
    })
}))

describe('UserMenu logout', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.spyOn(console, 'error').mockImplementation(() => undefined)
    })

    it('navigates away before a pending local logout request settles', async () => {
        let rejectLogout
        mockLogout.mockReturnValue(
            new Promise((_, reject) => {
                rejectLogout = reject
            })
        )
        const wrapper = mountWithPlugins(UserMenu, {
            global: { stubs: { VMenu: true, UserSettings: true } }
        })

        const request = wrapper.vm.handleLogout()

        expect(mockRouterReplace).toHaveBeenCalledWith('/login')

        rejectLogout(new Error('Server unavailable'))
        await request
    })

    it('still navigates to login when server logout rejects immediately', async () => {
        mockLogout.mockRejectedValue(new Error('Server unavailable'))
        const wrapper = mountWithPlugins(UserMenu, {
            global: { stubs: { VMenu: true, UserSettings: true } }
        })

        await wrapper.vm.handleLogout()

        expect(mockRouterReplace).toHaveBeenCalledWith('/login')
    })
})
