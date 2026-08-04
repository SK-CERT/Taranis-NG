<template>
    <v-card
        :class="['asset-card', vulnerable ? 'status-alert' : 'status-normal']"
        hover
        @click="emit('edit', asset)"
    >
        <v-card-title class="d-flex align-center">
            <v-icon class="mr-3">{{ asset.tag || 'mdi-server' }}</v-icon>
            <span>{{ asset.name || asset.title }}</span>
            <v-spacer />
            <ActionButton
                v-if="canModify"
                action="delete"
                @click.stop="confirmDelete = true"
            />
        </v-card-title>
        <v-card-subtitle v-if="asset.serial">{{ asset.serial }}</v-card-subtitle>
        <v-card-text>{{ asset.description || asset.subtitle }}</v-card-text>
        <v-card-actions>
            <v-chip
                :color="vulnerable ? 'error' : 'success'"
                size="small"
                variant="flat"
            >
                <v-icon start>{{ vulnerable ? 'mdi-shield-alert' : 'mdi-shield-check' }}</v-icon>
                {{ vulnerable ? `${t('asset.vulnerabilities_count')}${asset.vulnerabilities_count}` : t('asset.no_vulnerabilities') }}
            </v-chip>
        </v-card-actions>
    </v-card>
    <ConfirmationDialog
        v-model="confirmDelete"
        title-key="common.messagebox.delete"
        :message="asset.name || asset.title || ''"
        @confirm="emit('delete', asset)"
    />
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import type { Asset } from '@/types/assets'
    const props = defineProps<{ asset: Asset }>()
    const emit = defineEmits<{ (e: 'edit', asset: Asset): void; (e: 'delete', asset: Asset): void }>()
    const { t } = useI18n()
    const { checkPermission } = useAuth()
    const confirmDelete = ref(false)
    const vulnerable = computed(() => (props.asset.vulnerabilities_count || 0) > 0)
    const canModify = computed(() => checkPermission('MY_ASSETS_CREATE'))
</script>

<style scoped>
    .asset-card {
        height: 100%;
        border-left: 4px solid;
    }
    .status-alert {
        border-left-color: rgb(var(--v-theme-error));
    }
    .status-normal {
        border-left-color: rgb(var(--v-theme-success));
    }
</style>
