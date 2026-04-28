import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import App from '@/App.vue'

const mockConnect = vi.fn()
const mockDisconnect = vi.fn()
const mockReconnect = vi.fn()
const mockSubscribe = vi.fn()
const mockIsAuthenticated = vi.fn()
const mockNeedTokenRefresh = vi.fn()

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
  getProfileLanguage: 'en'
}

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() })
}))

vi.mock('@/composables/useSSE', () => ({
  useSSE: () => ({
    connect: mockConnect,
    disconnect: mockDisconnect,
    reconnect: mockReconnect,
    subscribe: mockSubscribe
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
    mockSettingsStore.getSetting.mockImplementation((key) => {
      if (key === 'DARK_THEME') return { value: 'false' }
      if (key === 'SPELLCHECK') return { value: 'true' }
      return null
    })
    mockSettingsStore.getProfileLanguage = 'en'

    document.cookie = 'jwt=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
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
    document.cookie = 'jwt=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
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

  it('should bootstrap from jwt cookie and call authStore.setToken before connecting', async () => {
    mockAuthStore.jwt = ''
    mockAuthStore.isAuthenticated = false
    mockAuthStore.getUserData = null
    mockIsAuthenticated.mockReturnValue(false)
    document.cookie = 'jwt=cookie-token; path=/'

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

    expect(mockAuthStore.setToken).toHaveBeenCalledWith('cookie-token')
    await vi.waitFor(() => {
      expect(mockConnect).toHaveBeenCalledTimes(1)
    })
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
})
