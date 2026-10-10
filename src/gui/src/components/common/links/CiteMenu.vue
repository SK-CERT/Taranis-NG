<template>
    <v-menu
        location="bottom end"
        :disabled="disabled"
    >
        <template #activator="{ props: menuProps }">
            <!-- mousedown.prevent keeps the focus (and the caret) in the text while the menu opens -->
            <v-btn
                v-bind="menuProps"
                icon
                variant="text"
                :density="density"
                :size="size"
                tabindex="-1"
                :disabled="disabled"
                :title="t('links.cite')"
                :aria-label="t('links.cite')"
                data-test="cite-menu"
                @mousedown.stop.prevent
            >
                <v-icon>{{ ICONS.CITE }}</v-icon>
            </v-btn>
        </template>
        <v-list
            density="compact"
            max-width="560"
            class="cite-menu"
        >
            <v-list-item
                v-if="links.length === 0 && groups.every((group) => group.links.length === 0)"
                disabled
                :title="t('links.cite_no_links')"
            />
            <v-list-item
                v-for="link in links"
                :key="link.key"
                data-test="cite-link"
                @click="emit('pick', link)"
            >
                <template #prepend>
                    <span class="cite-menu__number">[{{ link.number }}]</span>
                </template>
                <v-list-item-title>
                    <bdi
                        dir="ltr"
                        :title="link.url"
                        >{{ shortUrl(link.url) }}</bdi
                    >
                </v-list-item-title>
            </v-list-item>
            <template
                v-for="group in groups"
                :key="group.title"
            >
                <template v-if="group.links.length > 0">
                    <v-divider class="my-1" />
                    <v-list-subheader>
                        <bdi dir="auto">{{ group.title }}</bdi>
                    </v-list-subheader>
                    <v-list-item
                        v-for="link in group.links"
                        :key="`${group.title}:${link.key}`"
                        data-test="cite-external-link"
                        @click="emit('pick-external', link)"
                    >
                        <template #prepend>
                            <v-icon
                                size="small"
                                class="cite-menu__number"
                                :icon="ICONS.LINK"
                            />
                        </template>
                        <v-list-item-title>
                            <bdi
                                dir="ltr"
                                :title="link.url"
                                >{{ shortUrl(link.url) }}</bdi
                            >
                        </v-list-item-title>
                    </v-list-item>
                </template>
            </template>
        </v-list>
    </v-menu>
</template>

<script setup lang="ts">
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'
    import { shortUrl, type CitableLink, type ExternalLink } from '@/utils/linkReferences'

    withDefaults(
        defineProps<{
            /** The form's own links. */
            links: CitableLink[]
            /** Further links, grouped under a heading each. */
            groups?: Array<{ title: string; links: ExternalLink[] }>
            disabled?: boolean
            density?: 'default' | 'comfortable' | 'compact'
            size?: string
        }>(),
        {
            groups: () => [],
            disabled: false,
            density: 'compact',
            size: 'default'
        }
    )

    const emit = defineEmits<{
        (e: 'pick', link: CitableLink): void
        (e: 'pick-external', link: ExternalLink): void
    }>()

    const { t } = useI18n()
</script>

<style scoped>
    .cite-menu__number {
        min-width: 36px;
        margin-inline-end: 8px;
        color: rgb(var(--v-theme-primary));
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }
</style>
