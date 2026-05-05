import { describe, it, expect, beforeEach, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mountWithPlugins } from '../helpers/mount-helpers'
import NewReportItem from '@/components/analyze/NewReportItem.vue'

const mockCheckPermission = vi.fn(() => true)
const mockGetUserId = vi.fn(() => 99)

const mockAnalyzeStore = {
  getReportItemTypes: { items: [] },
  loadReportItemTypes: vi.fn()
}

const mockSettingsStore = {
  getSetting: vi.fn()
}

const mockRoute = {
  path: '/analyze',
  params: {}
}

const mockRouter = {
  push: vi.fn(),
  replace: vi.fn()
}

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    checkPermission: mockCheckPermission,
    getUserId: mockGetUserId
  })
}))

vi.mock('@/stores/analyze', () => ({
  useAnalyzeStore: () => mockAnalyzeStore
}))

vi.mock('@/stores/settings', () => ({
  useSettingsStore: () => mockSettingsStore
}))

vi.mock('@/components/analyze/NewsItemSelector.vue', () => ({
  default: {
    name: 'NewsItemSelector',
    props: ['attach', 'values', 'modify', 'reportItemId', 'edit', 'verticalView'],
    template: '<div class="news-item-selector-stub" />'
  }
}))

vi.mock('@/components/analyze/RemoteReportItemSelector.vue', () => ({
  default: {
    name: 'RemoteReportItemSelector',
    props: ['values', 'modify', 'edit', 'reportItemId'],
    template: '<div class="remote-report-item-selector-stub" />'
  }
}))

vi.mock('@/components/common/StateSelector.vue', () => ({
  default: {
    name: 'StateSelector',
    props: ['modelValue', 'availableStates', 'label', 'disabled'],
    template: '<div class="state-selector-stub" />'
  }
}))

vi.mock('@/components/common/attribute/AttributeContainer.vue', () => ({
  default: {
    name: 'AttributeContainer',
    props: ['attributeItem', 'edit', 'modify', 'reportItemId', 'readOnly'],
    template: '<div class="attribute-container-stub" />'
  }
}))

vi.mock('@/api/state', () => ({
  getEntityTypeStates: vi.fn()
}))

vi.mock('@/api/analyze', () => ({
  createNewReportItem: vi.fn(),
  updateReportItem: vi.fn(),
  lockReportItem: vi.fn(),
  unlockReportItem: vi.fn(),
  holdLockReportItem: vi.fn(),
  getReportItem: vi.fn(),
  getReportItemData: vi.fn(),
  getReportItemLocks: vi.fn(),
  aiGenerate: vi.fn()
}))

const VDialogStub = {
  name: 'VDialog',
  props: ['modelValue', 'fullscreen', 'persistent'],
  template: '<div class="v-dialog-stub"><slot /></div>'
}

const VOverlayStub = {
  name: 'VOverlay',
  props: ['modelValue'],
  template: '<div class="v-overlay-stub"><slot /></div>'
}

function makeReportType() {
  return {
    id: 5,
    title: 'Report Type',
    attribute_groups: []
  }
}

function makeReportItem() {
  return {
    id: 7,
    uuid: 'uuid-7',
    title: 'Original title',
    title_prefix: 'Original prefix',
    report_item_type_id: 5,
    state_id: 1,
    news_item_aggregates: [],
    remote_report_items: [],
    attributes: []
  }
}

describe('NewReportItem SSE collaboration', () => {
  let analyzeApi
  let stateApi

  beforeEach(async () => {
    vi.clearAllMocks()

    mockCheckPermission.mockReturnValue(true)
    mockGetUserId.mockReturnValue(99)
    mockRoute.path = '/analyze'
    mockRoute.params = {}

    mockAnalyzeStore.getReportItemTypes = { items: [makeReportType()] }
    mockAnalyzeStore.loadReportItemTypes.mockResolvedValue({
      data: mockAnalyzeStore.getReportItemTypes
    })

    mockSettingsStore.getSetting.mockImplementation((key) => {
      if (key === 'SPELLCHECK') {
        return { value: 'true' }
      }
      return null
    })

    analyzeApi = await import('@/api/analyze')
    stateApi = await import('@/api/state')

    vi.mocked(stateApi.getEntityTypeStates).mockResolvedValue({
      data: {
        states: [{ id: 1, is_default: true, icon: 'mdi-check', color: 'success' }]
      }
    })

    vi.mocked(analyzeApi.getReportItem).mockResolvedValue({
      data: makeReportItem()
    })

    vi.mocked(analyzeApi.getReportItemLocks).mockResolvedValue({
      data: {}
    })

    vi.mocked(analyzeApi.getReportItemData).mockResolvedValue({
      data: {
        title: 'Updated title remotely'
      }
    })
  })

  async function mountOpenedEditor() {
    const wrapper = mountWithPlugins(NewReportItem, {
      props: { showButton: false },
      global: {
        stubs: {
          VDialog: VDialogStub,
          VOverlay: VOverlayStub
        }
      }
    })

    await flushPromises()
    await wrapper.vm.showDetail({ id: 7, modify: true })
    await flushPromises()

    return wrapper
  }

  it('locks and unlocks title fields when collaborative events arrive from another user', async () => {
    const wrapper = await mountOpenedEditor()

    const getTitleFields = () => {
      const textFields = wrapper.findAllComponents({ name: 'VTextField' })
      return {
        titlePrefixField: textFields.find((field) => field.props('modelValue') === 'Original prefix'),
        titleField: textFields.find((field) => field.props('modelValue') === 'Original title')
      }
    }

    const { titlePrefixField, titleField } = getTitleFields()

    expect(titleField.props('disabled')).toBe(false)
    expect(titlePrefixField.props('disabled')).toBe(false)

    window.dispatchEvent(
      new CustomEvent('report-item-locked', {
        detail: { report_item_id: 7, field_id: 'title', user_id: 123 }
      })
    )
    window.dispatchEvent(
      new CustomEvent('report-item-locked', {
        detail: { report_item_id: 7, field_id: 'title_prefix', user_id: 123 }
      })
    )
    await flushPromises()

    const lockedFields = getTitleFields()
    expect(lockedFields.titlePrefixField.props('disabled')).toBe(true)
    expect(lockedFields.titleField.props('disabled')).toBe(true)

    window.dispatchEvent(
      new CustomEvent('report-item-unlocked', {
        detail: { report_item_id: 7, field_id: 'title', user_id: 123 }
      })
    )
    window.dispatchEvent(
      new CustomEvent('report-item-unlocked', {
        detail: { report_item_id: 7, field_id: 'title_prefix', user_id: 123 }
      })
    )
    await flushPromises()

    const unlockedFields = getTitleFields()
    expect(unlockedFields.titlePrefixField.props('disabled')).toBe(false)
    expect(unlockedFields.titleField.props('disabled')).toBe(false)
  })

  it('updates the report title from a collaborative report-item-updated event', async () => {
    const wrapper = await mountOpenedEditor()

    window.dispatchEvent(
      new CustomEvent('report-item-updated', {
        detail: { report_item_id: 7, user_id: 123 }
      })
    )
    await flushPromises()

    expect(wrapper.html()).toContain('Updated title remotely')
    expect(wrapper.html()).not.toContain('Original title')
    expect(analyzeApi.getReportItemData).toHaveBeenCalledWith(7, {
      report_item_id: 7,
      user_id: 123
    })
  })

  it('ignores collaborative lock events originating from the current user', async () => {
    const wrapper = await mountOpenedEditor()

    window.dispatchEvent(
      new CustomEvent('report-item-locked', {
        detail: { report_item_id: 7, field_id: 'title', user_id: 99 }
      })
    )
    await flushPromises()

    const textFields = wrapper.findAllComponents({ name: 'VTextField' })
    expect(textFields[1].props('disabled')).toBe(false)
  })
})
