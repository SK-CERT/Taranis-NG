<template>
    <div class="assess-item-actions">
        <!-- Open Link -->
        <v-btn
            v-if="showOpenLink && hasLink"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :href="itemLink"
            target="_blank"
            rel="noreferrer"
            :title="t('assess.tooltip.open_source')"
            @click.stop
        >
            <v-icon :size="iconSize">
                {{ ICONS.OPEN }}
            </v-icon>
        </v-btn>

        <!-- Create Report (Single Item Only) -->
        <v-btn
            v-if="showCreateReport && canCreateReport"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.analyze_item')"
            @click.stop="$emit('action', 'create-report')"
        >
            <v-icon :size="iconSize">
                {{ ICONS.ANALYZE }}
            </v-icon>
        </v-btn>

        <!-- Ungroup (Aggregate Only) -->
        <v-btn
            v-if="showUngroup && canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.ungroup_item')"
            @click.stop="$emit('action', 'ungroup')"
        >
            <v-icon :size="iconSize">
                {{ ICONS.UNGROUP }}
            </v-icon>
        </v-btn>

        <!-- Like -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.like_item')"
            @click.stop="$emit('action', 'like')"
        >
            <v-icon :size="iconSize" :color="item.me_like ? 'warning' : undefined">
                {{ item.me_like ? ICONS.LIKE : ICONS.LIKE_OUTLINE }}
            </v-icon>
        </v-btn>
        <span v-if="showCounts && canModify" class="vote-count" :class="{ 'is-empty': Number(item.likes || 0) === 0 }">
            {{ Number(item.likes || 0) > 0 ? Number(item.likes || 0) : '0' }}
        </span>

        <!-- Dislike -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.dislike_item')"
            @click.stop="$emit('action', 'dislike')"
        >
            <v-icon :size="iconSize" :color="item.me_dislike ? 'warning' : undefined">
                {{ item.me_dislike ? ICONS.UNLIKE : ICONS.UNLIKE_OUTLINE }}
            </v-icon>
        </v-btn>
        <span v-if="showCounts && canModify" class="vote-count" :class="{ 'is-empty': Number(item.dislikes || 0) === 0 }">
            {{ Number(item.dislikes || 0) > 0 ? Number(item.dislikes || 0) : '0' }}
        </span>

        <!-- Important -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.important_item')"
            @click.stop="$emit('action', 'important')"
        >
            <v-icon :size="iconSize" :color="item.important ? 'warning' : undefined">
                {{ item.important ? ICONS.IMPORTANT : ICONS.IMPORTANT_OUTLINE }}
            </v-icon>
        </v-btn>

        <!-- Read/Unread -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.read_item')"
            @click.stop="$emit('action', 'read')"
        >
            <v-icon :size="iconSize" :color="item.read ? 'warning' : undefined">
                {{ item.read ? ICONS.READ : ICONS.READ_OUTLINE }}
            </v-icon>
        </v-btn>

        <!-- Delete -->
        <ActionButton
            v-if="canDelete"
            action="delete"
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="t('assess.tooltip.delete_item')"
            @click.stop="showDeleteDialog = true"
        />

        <!-- Delete Confirmation Dialog -->
        <ConfirmationDialog
            v-model="showDeleteDialog"
            :message="t('assess.delete_confirmation')"
            max-width="600px"
            @confirm="$emit('action', 'delete')"
        />
    </div>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import { PERMISSIONS } from '@/services/auth/permissions'
    import { ICONS } from '@/config/ui-constants'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'

    type AssessItem = {
        id?: number | string
        me_like?: boolean
        me_dislike?: boolean
        likes?: number
        dislikes?: number
        important?: boolean
        read?: boolean
        link?: string
        news_items?: Array<{
            news_item_data?: {
                link?: string
                [key: string]: unknown
            }
        }>
        [key: string]: any
    }

    type BtnVariant = 'text' | 'flat' | 'plain' | 'outlined' | 'elevated' | 'tonal'

    const props = withDefaults(
        defineProps<{
            item: AssessItem
            size?: string
            variant?: BtnVariant
            iconSize?: string
            showCreateReport?: boolean
            showUngroup?: boolean
            showCounts?: boolean
            showOpenLink?: boolean
            disabled?: boolean
        }>(),
        {
            size: 'small',
            variant: 'text',
            iconSize: 'small',
            showCreateReport: false,
            showUngroup: false,
            showCounts: false,
            showOpenLink: true,
            disabled: false
        }
    )

    const emit = defineEmits<{
        (e: 'action', action: string): void
    }>()

    const { t } = useI18n()
    const { checkPermission } = useAuth()

    const showDeleteDialog = ref<boolean>(false)

    const newsItems = computed(() => props.item.news_items ?? [])

    const itemLink = computed(() => {
        // Support both news_items array (aggregate) and direct link property
        if (newsItems.value.length > 0) {
            const firstNewsItem = newsItems.value[0]
            return firstNewsItem?.news_item_data?.link || ''
        }
        return props.item.link || ''
    })

    const hasLink = computed(() => {
        return !!itemLink.value
    })

    const canModify = computed(() => {
        return checkPermission(PERMISSIONS.ASSESS_UPDATE)
    })

    const canDelete = computed(() => {
        return checkPermission(PERMISSIONS.ASSESS_DELETE)
    })

    const canCreateReport = computed(() => {
        return checkPermission(PERMISSIONS.ANALYZE_CREATE)
    })
</script>

<style scoped>
    .assess-item-actions {
        display: flex;
        align-items: center;
        gap: 4px;
    }

    .vote-count {
        min-width: 0.75rem;
        text-align: center;
        font-size: 0.75rem;
        color: rgb(var(--v-theme-on-surface));
        opacity: 0.7;
        margin-left: -0.5rem;
        margin-right: -0.2rem;
    }

    .vote-count.is-empty {
        visibility: hidden;
    }
</style>
