import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { useLocale } from 'vuetify'
import { mountWithPlugins } from '../helpers/mount-helpers'
import App from '@/App.vue'

const mockConnect = vi.fn()
const mockDisconnect = vi.fn()
const mockReconnect = vi.fn()
const mockSubscribe = vi.fn()
const mockOnResync = vi.fn()
const mockIsAuthenticated = vi.fn()
const mockNeedTokenRefresh = vi.fn()
const mockRouterReplace = vi.fn()

const mockAuthStore = {
    jwt: '',
    isAuthenticated: false,
    getUserData: null,
    refreshToken: vi.fn(),
    logout: vi.fn(),
    setToken: vi.fn()
}

const mockUserStore = {
    user: { id: '' },
    setUser: vi.fn()
}

const mockSettingsStore = {
    getSettings: [],
    spellcheck: false,
    loadSettings: vi.fn(),
    loadUserWordLists: vi.fn(),
    loadUserHotkeys: vi.fn(),
    getSetting: vi.fn(),
    getSettingBoolean: vi.fn(),
    getProfileLanguage: 'en'
}

vi.mock('vue-router', () => ({
    useRouter: () => ({ replace: mockRouterReplace }),
    useRoute: () => ({ name: 'assess', path: '/assess' })
}))

vi.mock('@/composables/useSSE', () => ({
    useSSE: () => ({
        connect: mockConnect,
        disconnect: mockDisconnect,
        reconnect: mockReconnect,
        subscribe: mockSubscribe,
        onResync: mockOnResync
    })
}))

vi.mock('@/composables/useAuth', () => ({
    useAuth: () => ({
        isAuthenticated: mockIsAuthenticated,
        needTokenRefresh: mockNeedTokenRefresh
    })
}))

vi.mock('@/stores/auth', () => ({
    useAuthStore: () => mockAuthStore
}))

vi.mock('@/stores/user', () => ({
    useUserStore: () => mockUserStore
}))

vi.mock('@/stores/settings', () => ({
    useSettingsStore: () => mockSettingsStore
}))

const LocaleProbe = defineComponent({
    name: 'LocaleProbe',
    setup() {
        const { current, isRtl } = useLocale()
        return { current, isRtl }
    },
    template: '<div class="locale-probe">{{ current }}:{{ isRtl }}</div>'
})

describe('App SSE boot flow', () => {
    let wrapper

    beforeEach(() => {
        vi.useFakeTimers()
        vi.clearAllMocks()

        mockConnect.mockResolvedValue({})
        mockDisconnect.mockReturnValue(undefined)
        mockReconnect.mockResolvedValue({})
        mockSubscribe.mockReturnValue(undefined)
        mockIsAuthenticated.mockReturnValue(true)
        mockNeedTokenRefresh.mockReturnValue(false)

        mockAuthStore.jwt = 'stored-token'
        mockAuthStore.isAuthenticated = true
        mockAuthStore.getUserData = { id: 1, name: 'Admin', permissions: [] }
        mockAuthStore.refreshToken.mockResolvedValue({})
        mockAuthStore.logout.mockReturnValue(undefined)
        mockAuthStore.setToken.mockReturnValue(undefined)

        mockUserStore.user = { id: 1 }
        mockUserStore.setUser.mockReturnValue(undefined)

        mockSettingsStore.getSettings = [{ id: 1, key: 'DARK_THEME' }]
        mockSettingsStore.spellcheck = false
        mockSettingsStore.loadSettings.mockResolvedValue({})
        mockSettingsStore.loadUserWordLists.mockResolvedValue({})
        mockSettingsStore.loadUserHotkeys.mockResolvedValue({})
        mockSettingsStore.getSetting.mockImplementation((key, defValue = '') => {
            if (key === 'DARK_THEME') return 'false'
            if (key === 'SPELLCHECK') return 'true'
            return defValue
        })
        mockSettingsStore.getProfileLanguage = 'en'

        vi.stubGlobal('requestAnimationFrame', (callback) => {
            callback()
            return 1
        })
    })

    afterEach(() => {
        wrapper?.unmount()
        wrapper = null
        vi.useRealTimers()
        vi.unstubAllGlobals()
    })

    it('should initialize settings and register SSE listeners on authenticated mount', async () => {
        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        await flushPromises()

        expect(mockSettingsStore.loadSettings).toHaveBeenCalledWith({ search: '' })
        expect(mockSettingsStore.loadUserWordLists).toHaveBeenCalled()
        expect(mockSettingsStore.loadUserHotkeys).toHaveBeenCalled()
        await vi.waitFor(() => {
            expect(mockConnect).toHaveBeenCalledTimes(1)
        })
        expect(mockSubscribe.mock.calls.map(([eventName]) => eventName)).toEqual([
            'news-items-updated',
            'report-items-updated',
            'report-item-updated',
            'report-item-locked',
            'report-item-unlocked'
        ])
    })

    it('should not start a session when the stored token is absent', async () => {
        // Session bootstrap happens before App mounts, so App only sees store state.
        mockAuthStore.jwt = ''
        mockAuthStore.isAuthenticated = false
        mockAuthStore.getUserData = null
        mockIsAuthenticated.mockReturnValue(false)

        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        await flushPromises()

        expect(mockSettingsStore.loadSettings).not.toHaveBeenCalled()
        expect(mockConnect).not.toHaveBeenCalled()
    })

    it('should reconnect SSE after token refresh when refresh is needed', async () => {
        mockNeedTokenRefresh.mockReturnValue(true)

        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        vi.advanceTimersByTime(5000)
        await flushPromises()

        await vi.waitFor(() => {
            expect(mockAuthStore.refreshToken).toHaveBeenCalledTimes(1)
            expect(mockReconnect).toHaveBeenCalledTimes(1)
        })
    })

    it('should leave protected content when token refresh fails', async () => {
        mockNeedTokenRefresh.mockReturnValue(true)
        mockAuthStore.refreshToken.mockRejectedValue(new Error('Token expired'))

        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        vi.advanceTimersByTime(5000)
        await flushPromises()

        expect(mockRouterReplace).toHaveBeenCalledWith('/login')
        expect(mockReconnect).not.toHaveBeenCalled()
    })

    it('should leave protected content immediately when the stored token expires', async () => {
        mockIsAuthenticated.mockReturnValue(false)
        mockAuthStore.logout.mockResolvedValue(undefined)

        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        vi.advanceTimersByTime(5000)

        expect(mockAuthStore.logout).toHaveBeenCalledTimes(1)
        expect(mockRouterReplace).toHaveBeenCalledWith('/login')
    })

    it('should initialize authenticated session when logged-in event fires', async () => {
        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: true,
                    NotificationSnackbar: true
                }
            }
        })

        await flushPromises()
        mockConnect.mockClear()
        mockSubscribe.mockClear()

        window.dispatchEvent(new Event('logged-in'))
        await flushPromises()

        await vi.waitFor(() => {
            expect(mockConnect).toHaveBeenCalledTimes(1)
            expect(mockSubscribe).toHaveBeenCalledTimes(5)
        })
    })

    it('synchronizes runtime locale changes with document metadata and Vuetify direction', async () => {
        wrapper = mountWithPlugins(App, {
            global: {
                stubs: {
                    MainMenu: LocaleProbe,
                    NotificationSnackbar: true
                }
            }
        })
        await flushPromises()

        wrapper.vm.$i18n.locale = 'ar'
        await nextTick()

        expect(document.documentElement.lang).toBe('ar')
        expect(document.documentElement.dir).toBe('rtl')
        expect(wrapper.get('.locale-probe').text()).toBe('ar:true')

        wrapper.vm.$i18n.locale = 'unsupported-locale'
        await nextTick()
        await nextTick()

        expect(wrapper.vm.$i18n.locale).toBe('en')
        expect(document.documentElement.lang).toBe('en')
        expect(document.documentElement.dir).toBe('ltr')
        expect(wrapper.get('.locale-probe').text()).toBe('en:false')
    })
})
