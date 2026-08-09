<template>
    <article
        :class="['asset-card', vulnerable ? 'status-alert' : 'status-normal']"
        tabindex="0"
        @click="emit('edit', asset)"
        @keydown.enter="emit('edit', asset)"
    >
        <div class="asset-card__icon">
            <v-icon size="24">{{ asset.tag || 'mdi-server' }}</v-icon>
        </div>

        <div class="asset-card__identity">
            <strong
                ><bdi dir="auto">{{ asset.name || asset.title }}</bdi></strong
            >
            <i18n-t
                v-if="showSerial"
                keypath="asset.serial_with_value"
                tag="span"
            >
                <template #value>
                    <bdi dir="ltr">{{ asset.serial }}</bdi>
                </template>
            </i18n-t>
        </div>

        <p class="asset-card__description">
            <bdi dir="auto">{{ asset.description || asset.subtitle }}</bdi>
        </p>

        <div
            v-if="asset.asset_cpes?.length"
            class="asset-card__cpes"
            :title="cpeCountMessage"
        >
            <span class="d-sr-only">{{ cpeCountMessage }}</span>
            <v-icon
                size="17"
                aria-hidden="true"
            >
                mdi-tag-multiple-outline
            </v-icon>
            <strong aria-hidden="true">{{ formatNumber(cpeCount) }}</strong>
        </div>

        <v-chip
            class="asset-card__status"
            :color="vulnerable ? 'error' : 'success'"
            size="small"
            variant="tonal"
        >
            <v-icon start>{{ vulnerable ? 'mdi-shield-alert' : 'mdi-shield-check' }}</v-icon>
            <i18n-t
                keypath="asset.vulnerabilities_count"
                :plural="vulnerabilityCount"
            >
                <template #count>
                    <strong>{{ formatNumber(vulnerabilityCount) }}</strong>
                </template>
            </i18n-t>
        </v-chip>

        <div
            v-if="canModify"
            class="asset-card__actions"
        >
            <ActionButton
                action="delete"
                size="x-small"
                icon_size="small"
                @click.stop="confirmDelete = true"
            />
        </div>
    </article>
    <ConfirmationDialog
        v-model="confirmDelete"
        title-key="common.messagebox.delete"
        @confirm="emit('delete', asset)"
    >
        <bdi dir="auto">{{ asset.name || asset.title || '' }}</bdi>
    </ConfirmationDialog>
</template>

<script setup lang="ts">
    import { computed, ref } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { useAuth } from '@/composables/useAuth'
    import ActionButton from '@/components/common/buttons/ActionButton.vue'
    import ConfirmationDialog from '@/components/common/dialogs/ConfirmationDialog.vue'
    import type { Asset } from '@/types/assets'
    import { useLocaleFormatters } from '@/composables/useLocaleFormatters'
    const props = defineProps<{ asset: Asset }>()
    const emit = defineEmits<{ (e: 'edit', asset: Asset): void; (e: 'delete', asset: Asset): void }>()
    const { t } = useI18n()
    const { formatNumber } = useLocaleFormatters()
    const { checkPermission } = useAuth()
    const confirmDelete = ref(false)
    const vulnerabilityCount = computed(() => Math.max(0, Number(props.asset.vulnerabilities_count ?? 0)))
    const cpeCount = computed(() => props.asset.asset_cpes?.length ?? 0)
    const vulnerable = computed(() => vulnerabilityCount.value > 0)
    const cpeCountMessage = computed(() => t('asset.cpe_count', { count: formatNumber(cpeCount.value) }, cpeCount.value))
    const canModify = computed(() => checkPermission('MY_ASSETS_CREATE'))
    const showSerial = computed(() => Boolean(props.asset.serial) && props.asset.serial !== (props.asset.name || props.asset.title))
</script>

<style scoped>
    .asset-card {
        position: relative;
        display: grid;
        grid-template-columns: auto minmax(11rem, 0.55fr) minmax(14rem, 1fr) auto auto auto;
        align-items: center;
        width: 100%;
        min-height: 68px;
        padding: 0.5rem 0.65rem;
        gap: 0.7rem;
        border-bottom: 1px solid var(--review-list-border);
        background: var(--review-list-row);
        cursor: pointer;
        outline: none;
    }

    .asset-card:last-child {
        border-bottom: 0;
    }

    .asset-card:hover,
    .asset-card:focus-visible {
        z-index: 1;
        background: var(--review-list-row-hover);
        box-shadow: inset 0 0 0 2px rgb(var(--v-theme-primary));
    }

    .asset-card__icon {
        display: grid;
        width: 38px;
        height: 38px;
        place-items: center;
        border: 1px solid rgba(var(--v-theme-primary), 0.22);
        border-radius: 3px;
        background: rgba(var(--v-theme-primary), 0.09);
        color: rgb(var(--v-theme-primary));
    }

    .asset-card__identity {
        display: flex;
        min-width: 0;
        flex-direction: column;
        gap: 0.1rem;
    }

    .asset-card__identity strong {
        overflow: hidden;
        font-size: 0.88rem;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .asset-card__identity span,
    .asset-card__description,
    .asset-card__cpes {
        color: rgba(var(--v-theme-on-surface), 0.58);
        font-size: 0.72rem;
    }

    .asset-card__description {
        display: -webkit-box;
        min-width: 0;
        margin: 0;
        overflow: hidden;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        line-height: 1.3;
    }

    .asset-card__cpes {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        white-space: nowrap;
    }

    .asset-card__status {
        min-width: max-content;
        border-radius: 3px;
        font-weight: 650;
    }

    .asset-card__actions {
        display: flex;
        align-items: center;
        min-height: 36px;
        padding-inline-start: 0.55rem;
        border-inline-start: 1px solid rgba(var(--v-theme-outline), 0.18);
    }

    .status-alert .asset-card__icon {
        border-color: rgba(var(--v-theme-error), 0.28);
        background: rgba(var(--v-theme-error), 0.08);
        color: rgb(var(--v-theme-error));
    }

    @media (max-width: 900px) {
        .asset-card {
            grid-template-columns: auto minmax(10rem, 0.8fr) minmax(12rem, 1fr) auto auto;
        }

        .asset-card__cpes {
            display: none;
        }
    }

    @media (max-width: 650px) {
        .asset-card {
            grid-template-columns: auto minmax(0, 1fr) auto auto;
            gap: 0.5rem;
        }

        .asset-card__description {
            display: none;
        }

        .asset-card__status {
            max-width: 9rem;
            overflow: hidden;
        }
    }
</style>
