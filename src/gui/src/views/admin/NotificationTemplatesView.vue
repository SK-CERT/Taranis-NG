<template>
    <v-container
        fluid
        class="pa-0"
    >
        <ToolbarFilter
            :total-count="store.notificationTemplates.total_count"
            total-count-title="notification_template.total_count"
            @update-filter="setFilter"
        >
            <template #addbutton><AddNewButton @click="openCreate" /></template>
        </ToolbarFilter>
        <ContentData
            :items="store.notificationTemplates.items"
            card-item="CardCompact"
            delete-permission="MY_ASSETS_CONFIG"
            :loading="loading"
            @edit="openEdit"
            @delete="remove"
            @refresh="load"
        />
        <NotificationTemplateDialog
            v-model="dialog"
            :template="selected"
            @saved="load"
        />
    </v-container>
</template>

<script setup lang="ts">
    import { onMounted, ref } from 'vue'
    import { useAssetsStore } from '@/stores/assets'
    import { deleteNotificationTemplate } from '@/api/assets'
    import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
    import ContentData from '@/components/common/ContentData.vue'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import NotificationTemplateDialog from '@/components/config/notifications/NotificationTemplateDialog.vue'
    import type { NotificationTemplate } from '@/types/assets'
    const store = useAssetsStore()
    const loading = ref(false)
    const filter = ref({ search: '' })
    const dialog = ref(false)
    const selected = ref<NotificationTemplate | null>(null)
    const notify = (type: 'success' | 'error', loc: string): void => {
        window.dispatchEvent(new CustomEvent('notification', { detail: { type, loc } }))
    }
    const load = async (): Promise<void> => {
        loading.value = true
        try {
            await store.loadNotificationTemplates(filter.value)
        } catch {
            notify('error', 'notification_template.load_error')
        } finally {
            loading.value = false
        }
    }
    const setFilter = (value: { search: string }): void => {
        filter.value = value
        load()
    }
    const openCreate = (): void => {
        selected.value = null
        dialog.value = true
    }
    const openEdit = (value: unknown): void => {
        selected.value = value as NotificationTemplate
        dialog.value = true
    }
    const remove = async (value: unknown): Promise<void> => {
        try {
            await deleteNotificationTemplate(value as NotificationTemplate)
            notify('success', 'notification_template.removed')
            await load()
        } catch {
            notify('error', 'notification_template.removed_error')
        }
    }
    onMounted(load)
</script>
