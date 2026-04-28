import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getManualOSINTSources,
  getNewsItemsByGroup,
  voteNewsItemAggregate as apiVoteAggregate,
  readNewsItemAggregate as apiReadAggregate,
  importantNewsItemAggregate as apiImportantAggregate,
  deleteNewsItemAggregate as apiDeleteAggregate,
  saveNewsItemAggregate as apiSaveAggregate
} from '@/api/assess'

export const useAssessStore = defineStore('assess', () => {
  // State
  const newsitems = ref({ total_count: 0, items: [] })
  const multi_select = ref(false)
  const selection = ref([])
  const current_group_id = ref('')
  const manual_osint_sources = ref([])
  const filter = ref({})

  // Getters
  const getNewsItems = computed(() => newsitems.value || { total_count: 0, items: [] })
  const getMultiSelect = computed(() => multi_select.value)
  const getSelection = computed(() => selection.value)
  const selectedItems = computed(() => {
    return new Set(selection.value.map((item) => item.id))
  })
  const getCurrentGroup = computed(() => current_group_id.value)
  const getManualOSINTSourcesList = computed(() =>
    Array.isArray(manual_osint_sources.value) ? manual_osint_sources.value : []
  )
  const getFilter = computed(() => filter.value)

  // Actions
  async function loadNewsItemsByGroup(data) {
    const response = await getNewsItemsByGroup(data.group_id, data.data)
    if (response) {
      newsitems.value = response.data || { total_count: 0, items: [] }
    }
    return response
  }

  function multiSelect(enable) {
    multi_select.value = enable
    selection.value = []
  }

  function select(selected_item) {
    selection.value.push(selected_item)
  }

  function deselect(selectedItem) {
    for (let i = 0; i < selection.value.length; i++) {
      if (
        selection.value[i].type === selectedItem.type &&
        selection.value[i].id === selectedItem.id
      ) {
        selection.value.splice(i, 1)
        break
      }
    }
  }

  function changeCurrentGroup(group_id) {
    current_group_id.value = group_id
  }

  async function loadManualOSINTSources() {
    const response = await getManualOSINTSources()
    manual_osint_sources.value = response.data || []
    return response
  }

  function setFilter(data) {
    filter.value = data
  }

  async function voteNewsItemAggregate(group_id, aggregate_id, vote) {
    const response = await apiVoteAggregate(group_id, aggregate_id, vote)
    return response
  }

  async function readNewsItemAggregate(group_id, aggregate_id) {
    const response = await apiReadAggregate(group_id, aggregate_id)
    return response
  }

  async function importantNewsItemAggregate(group_id, aggregate_id) {
    const response = await apiImportantAggregate(group_id, aggregate_id)
    return response
  }

  async function deleteNewsItemAggregate(group_id, aggregate_id) {
    const response = await apiDeleteAggregate(group_id, aggregate_id)
    return response
  }

  async function saveNewsItemAggregate(group_id, aggregate_id, title, description, comments) {
    const response = await apiSaveAggregate(group_id, aggregate_id, title, description, comments)
    return response
  }

  return {
    // State
    newsitems,
    multi_select,
    selection,
    current_group_id,
    manual_osint_sources,
    filter,

    // Getters
    getNewsItems,
    getMultiSelect,
    getSelection,
    selectedItems,
    getCurrentGroup,
    getManualOSINTSourcesList,
    getFilter,

    // Actions
    loadNewsItemsByGroup,
    multiSelect,
    select,
    deselect,
    changeCurrentGroup,
    loadManualOSINTSources,
    setFilter,
    voteNewsItemAggregate,
    readNewsItemAggregate,
    importantNewsItemAggregate,
    deleteNewsItemAggregate,
    saveNewsItemAggregate
  }
})
