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
            :data-action="Action.OPEN"
            @click.stop
        >
            <v-icon :size="iconSize">
                {{ ICONS.OPEN }}
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
            :data-action="Action.UNGROUP"
            @click.stop="$emit('action', Action.UNGROUP)"
        >
            <v-icon :size="iconSize">
                {{ ICONS.UNGROUP }}
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
            :data-action="Action.CREATE_REPORT"
            @click.stop="$emit('action', Action.CREATE_REPORT)"
        >
            <v-icon :size="iconSize">
                {{ ICONS.ANALYZE }}
            </v-icon>
        </v-btn>

        <!-- Like -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="likeState === 'others' ? t('assess.tooltip.liked_by_others') : t('assess.tooltip.like_item')"
            :data-action="Action.LIKE"
            @click.stop="$emit('action', Action.LIKE)"
        >
            <v-icon
                :size="iconSize"
                :color="voteColor(likeState)"
            >
                {{ likeState === 'none' ? ICONS.LIKE_OUTLINE : ICONS.LIKE }}
            </v-icon>
        </v-btn>
        <span
            v-if="showCounts && canModify"
            class="vote-count"
            :class="{ 'is-empty': Number(item.likes || 0) === 0 }"
        >
            {{ Number(item.likes || 0) > 0 ? Number(item.likes || 0) : '0' }}
        </span>

        <!-- Dislike -->
        <v-btn
            v-if="canModify"
            icon
            :disabled="disabled"
            :size="size"
            :variant="variant"
            :title="dislikeState === 'others' ? t('assess.tooltip.disliked_by_others') : t('assess.tooltip.dislike_item')"
            :data-action="Action.DISLIKE"
            @click.stop="$emit('action', Action.DISLIKE)"
        >
            <v-icon
                :size="iconSize"
                :color="voteColor(dislikeState)"
            >
                {{ dislikeState === 'none' ? ICONS.UNLIKE_OUTLINE : ICONS.UNLIKE }}
            </v-icon>
        </v-btn>
        <span
            v-if="showCounts && canModify"
            class="vote-count"
            :class="{ 'is-empty': Number(item.dislikes || 0) === 0 }"
        >
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
            :data-action="Action.IMPORTANT"
            @click.stop="$emit('action', Action.IMPORTANT)"
        >
            <v-icon
                :size="iconSize"
                :color="item.important ? 'warning' : undefined"
            >
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
            :data-action="Action.READ"
            @click.stop="$emit('action', Action.READ)"
        >
            <v-icon
                :size="iconSize"
                :color="item.read ? 'warning' : undefined"
            >
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
            :data-action="Action.DELETE"
            @click.stop="showDeleteDialog = true"
        />

        <!-- Delete Confirmation Dialog. The dialog's own heading asks the question, so the
             message names the item the user is about to delete - as every other card does. -->
        <ConfirmationDialog
            v-model="showDeleteDialog"
            :message="itemTitle"
            max-width="600px"
            @confirm="$emit('action', Action.DELETE)"
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
    import { Action, type ActionKey } from '@/types/actions'

    type AssessItem = {
        id?: number | string
        title?: string
        me_like?: boolean
        me_dislike?: boolean
        likes?: number
        dislikes?: number
        important?: boolean
        read?: boolean
        modify?: boolean
        entityType?: 'news_item' | 'news_item_aggregate'
        link?: string
        news_items?: Array<{
            news_item_data?: {
                link?: string
                title?: string
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
        (e: 'action', action: ActionKey): void
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

    /** Aggregates and child items both carry `title`; fall back to the source data for either. */
    const itemTitle = computed(() => {
        return props.item.title || newsItems.value[0]?.news_item_data?.title || ''
    })

    const hasLink = computed(() => {
        return !!itemLink.value
    })

    /**
     * Who cast the vote: yourself, a colleague, or nobody. `me_like` / `me_dislike` are this
     * user's own vote, while `likes` / `dislikes` count the whole team's - so a vote that is not
     * yours but is counted was cast by someone else.
     */
    type VoteState = 'me' | 'others' | 'none'

    const likeState = computed<VoteState>(() => {
        if (props.item.me_like) {
            return 'me'
        }
        return Number(props.item.likes || 0) > 0 ? 'others' : 'none'
    })

    const dislikeState = computed<VoteState>(() => {
        if (props.item.me_dislike) {
            return 'me'
        }
        return Number(props.item.dislikes || 0) > 0 ? 'others' : 'none'
    })

    const voteColor = (state: VoteState): string | undefined => {
        if (state === 'me') {
            return 'warning'
        }
        return state === 'others' ? 'primary' : undefined
    }

    const canModify = computed(() => {
        const itemAllowsModification = props.item.entityType !== 'news_item' || props.item.modify === true
        return checkPermission(PERMISSIONS.ASSESS_UPDATE) && itemAllowsModification
    })

    const canDelete = computed(() => {
        const itemAllowsDeletion = props.item.entityType !== 'news_item' || props.item.modify === true
        return checkPermission(PERMISSIONS.ASSESS_DELETE) && itemAllowsDeletion
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
