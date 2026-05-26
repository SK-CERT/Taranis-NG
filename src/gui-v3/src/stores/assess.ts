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

type ListState<T = unknown> = {
    total_count: number
    items: T[]
}

type SelectableItem = {
    id: string | number
    type: string
    [key: string]: unknown
}

type GroupLoadPayload = {
    group_id: string | number
    data: Record<string, unknown>
}

type ApiResponse<T> = {
    data?: T
}

const emptyListState = <T = unknown>(): ListState<T> => ({ total_count: 0, items: [] })

export const useAssessStore = defineStore('assess', () => {
    // State
    const newsitems = ref<ListState>(emptyListState())
    const multi_select = ref(false)
    const selection = ref<SelectableItem[]>([])
    const current_group_id = ref('')
    const manual_osint_sources = ref<unknown[]>([])
    const filter = ref<Record<string, unknown>>({})

    // Getters
    const getNewsItems = computed(() => newsitems.value || emptyListState())
    const getMultiSelect = computed(() => multi_select.value)
    const getSelection = computed(() => selection.value)
    const selectedItems = computed(() => {
        return new Set(selection.value.map((item) => item.id))
    })
    const getCurrentGroup = computed(() => current_group_id.value)
    const getManualOSINTSourcesList = computed(() => (Array.isArray(manual_osint_sources.value) ? manual_osint_sources.value : []))
    const getFilter = computed(() => filter.value)

    // Actions
    async function loadNewsItemsByGroup(data: GroupLoadPayload): Promise<ApiResponse<ListState>> {
        const response = await getNewsItemsByGroup(data.group_id, data.data)
        if (!response) {
            const fallback = { data: newsitems.value }
            return fallback
        }
        newsitems.value = response.data || emptyListState()
        return response
    }

    function multiSelect(enable: boolean): void {
        multi_select.value = enable
        selection.value = []
    }

    function select(selected_item: SelectableItem): void {
        selection.value.push(selected_item)
    }

    function deselect(selectedItem: SelectableItem): void {
        for (let i = 0; i < selection.value.length; i++) {
            const item = selection.value[i]
            if (item && item.type === selectedItem.type && item.id === selectedItem.id) {
                selection.value.splice(i, 1)
                break
            }
        }
    }

    function changeCurrentGroup(group_id: string): void {
        current_group_id.value = group_id
    }

    async function loadManualOSINTSources(): Promise<ApiResponse<unknown[]>> {
        const response = await getManualOSINTSources()
        const responseData = response?.data
        manual_osint_sources.value = Array.isArray(responseData) ? responseData : []
        return response
    }

    function setFilter(data: Record<string, unknown>): void {
        filter.value = data
    }

    async function voteNewsItemAggregate(group_id: string | number, aggregate_id: string | number, vote: unknown): Promise<unknown> {
        const response = await apiVoteAggregate(group_id, aggregate_id, vote)
        return response
    }

    async function readNewsItemAggregate(group_id: string | number, aggregate_id: string | number): Promise<unknown> {
        const response = await apiReadAggregate(group_id, aggregate_id)
        return response
    }

    async function importantNewsItemAggregate(group_id: string | number, aggregate_id: string | number): Promise<unknown> {
        const response = await apiImportantAggregate(group_id, aggregate_id)
        return response
    }

    async function deleteNewsItemAggregate(group_id: string | number, aggregate_id: string | number): Promise<unknown> {
        const response = await apiDeleteAggregate(group_id, aggregate_id)
        return response
    }

    async function saveNewsItemAggregate(
        group_id: string | number,
        aggregate_id: string | number,
        title: string,
        description: string,
        comments: string
    ): Promise<unknown> {
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
