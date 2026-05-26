import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

type OSINTSourceSelectionItem = {
    id: string | number
    type: string
    [key: string]: unknown
}

export const useOSINTSourceStore = defineStore('osint_source', () => {
    // State
    const multi_select_osint_source = ref(false)
    const selection = ref<OSINTSourceSelectionItem[]>([])

    // Getters
    const getOSINTSourcesMultiSelect = computed(() => multi_select_osint_source.value)
    const getOSINTSourcesSelection = computed(() => selection.value)

    // Actions
    function multiSelectOSINTSource(enable: boolean): void {
        multi_select_osint_source.value = enable
        selection.value = []
    }

    function selectOSINTSource(selected_item: OSINTSourceSelectionItem): void {
        selection.value.push(selected_item)
    }

    function deselectOSINTSource(selectedItem: OSINTSourceSelectionItem): void {
        for (let i = 0; i < selection.value.length; i++) {
            const item = selection.value[i]
            if (item && item.type === selectedItem.type && item.id === selectedItem.id) {
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
