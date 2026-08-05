<template>
    <v-card variant="outlined">
        <v-card-title class="d-flex align-center">
            {{ t('notification_template.recipients') }}
            <v-spacer />
            <AddNewButton
                label="notification_template.new_recipient"
                @click="edit()"
            />
        </v-card-title>
        <v-data-table
            :headers="headers"
            :items="model"
            :items-per-page="-1"
            hide-default-footer
        >
            <template #item.actions="{ item }">
                <ActionButton
                    action="edit"
                    @click="edit(item)"
                />
                <ActionButton
                    action="delete"
                    @click="remove(item)"
                />
            </template>
        </v-data-table>
    </v-card>
    <v-dialog
        v-model="dialog"
        max-width="520"
    >
        <v-card>
            <DialogToolbar
                :title="t(index < 0 ? 'notification_template.add_recipient' : 'notification_template.edit_recipient')"
                @cancel="dialog = false"
                @save="save"
            />
            <v-card-text>
                <v-text-field
                    v-model="working.email"
                    :spellcheck="false"
                    :label="t('notification_template.email')"
                    type="email"
                    variant="outlined"
                />
                <v-text-field
                    v-model="working.name"
                    :spellcheck="spellcheck"
                    :label="t('notification_template.recipient_name')"
                    variant="outlined"
                />
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useSpellcheck } from '@/composables/useSpellcheck'
    import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import DialogToolbar from '@/components/common/dialogs/DialogToolbar.vue'
    import type { NotificationRecipient } from '@/types/assets'
    const model = defineModel<NotificationRecipient[]>({ default: () => [] })
    const { t } = useI18n()
    const spellcheck = useSpellcheck()
    const dialog = ref(false)
    const index = ref(-1)
    const working = ref<NotificationRecipient>({ email: '', name: '' })
    const headers = computed(() => [
        { title: t('notification_template.email'), key: 'email' },
        { title: t('notification_template.recipient_name'), key: 'name' },
        { title: t('common.actions'), key: 'actions', sortable: false }
    ])
    const edit = (item?: NotificationRecipient): void => {
        index.value = item ? model.value.indexOf(item) : -1
        working.value = item ? { ...item } : { email: '', name: '' }
        dialog.value = true
    }
    const save = (): void => {
        if (!working.value.email.trim()) return
        if (index.value < 0) model.value.push({ ...working.value })
        else model.value.splice(index.value, 1, { ...working.value })
        dialog.value = false
    }
    const remove = (item: NotificationRecipient): void => {
        const found = model.value.indexOf(item)
        if (found >= 0) model.value.splice(found, 1)
    }
</script>
