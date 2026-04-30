import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useOSINTSourceStore = defineStore('osint_source', () => {
  // State
  const multi_select_osint_source = ref(false)
  const selection = ref([])

  // Getters
  const getOSINTSourcesMultiSelect = computed(() => multi_select_osint_source.value)
  const getOSINTSourcesSelection = computed(() => selection.value)

  // Actions
  function multiSelectOSINTSource(enable) {
    multi_select_osint_source.value = enable
    selection.value = []
  }

  function selectOSINTSource(selected_item) {
    selection.value.push(selected_item)
  }

  function deselectOSINTSource(selectedItem) {
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

  return {
    // State
    multi_select_osint_source,
    selection,

    // Getters
    getOSINTSourcesMultiSelect,
    getOSINTSourcesSelection,

    // Actions
    multiSelectOSINTSource,
    selectOSINTSource,
    deselectOSINTSource
  }
})
