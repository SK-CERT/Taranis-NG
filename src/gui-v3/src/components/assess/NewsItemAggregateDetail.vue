<template>
    <NewsItemDetailDialog
        v-model="showDialog"
        :news-item="newsItem"
        :multi-select-active="multiSelectActive"
        @action="handleAction"
        @delete="handleDelete"
    />
</template>

<script setup lang="ts">
    import { ref } from 'vue'
    import NewsItemDetailDialog from '@/components/assess/NewsItemDetailDialog.vue'
    import ApiService from '@/services/api_service'

    type NewsItem = {
        id?: number | string
        [key: string]: any
    }

    type ActionPayload = {
        action?: string
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attach?: string | HTMLElement | undefined
            verticalView?: boolean
            multiSelectActive?: boolean
        }>(),
        {
            attach: undefined,
            verticalView: false,
            multiSelectActive: false
        }
    )

    const emit = defineEmits<{
        (e: 'action', payload: ActionPayload): void
        (e: 'delete', item: NewsItem): void
    }>()

    const showDialog = ref<boolean>(false)
    const newsItem = ref<NewsItem>({})

    const getNewsItemAggregate = (groupId: string | null, aggregateId: string | number) => {
        return ApiService.get('/assess/news-item-aggregates/' + aggregateId)
    }

    const open = async (item: NewsItem): Promise<void> => {
        try {
            // For aggregate items, get the full detail from API
            if (item && item.id) {
                const response = await getNewsItemAggregate(null, item.id)
                newsItem.value = (response || item) as NewsItem
            } else {
                newsItem.value = item
            }
            showDialog.value = true
        } catch {
            // Fallback to passed item data
            newsItem.value = item
            showDialog.value = true
        }
    }

    const handleAction = (payload: ActionPayload): void => {
        emit('action', payload)
    }

    const handleDelete = (item: NewsItem): void => {
        showDialog.value = false
        emit('delete', item)
    }

    defineExpose({
        open
    })
</script>
