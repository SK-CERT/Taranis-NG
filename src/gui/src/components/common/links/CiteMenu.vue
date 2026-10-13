<template>
    <v-menu
        v-model="open"
        location="bottom end"
        :disabled="disabled"
        :close-on-content-click="false"
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
        <v-card
            max-width="560"
            class="cite-menu"
        >
            <!-- Outside the list: its key handling would take Home/End from the input. -->
            <div
                v-if="searchable"
                class="pa-2"
            >
                <SearchField
                    v-model="query"
                    :label="t('links.cite_search')"
                    autofocus
                    data-test="cite-search"
                    @keydown.enter.prevent="pickFirst"
                />
            </div>
            <v-list
                density="compact"
                max-height="360"
                class="overflow-y-auto"
            >
                <v-list-item
                    v-if="offered === 0"
                    disabled
                    :title="t('links.cite_no_links')"
                />
                <v-list-item
                    v-else-if="shownLinks.length === 0 && shownGroups.length === 0"
                    disabled
                    :title="t('links.cite_no_match')"
                    data-test="cite-no-match"
                />
                <v-list-item
                    v-for="link in shownLinks"
                    :key="link.key"
                    data-test="cite-link"
                    @click="pick(link)"
                >
                    <template #prepend>
                        <bdi
                            dir="ltr"
                            class="cite-menu__token"
                            >{{ linkToken(link.key) }}</bdi
                        >
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
                    v-for="group in shownGroups"
                    :key="group.title"
                >
                    <v-divider class="my-1" />
                    <v-list-subheader>
                        <bdi dir="auto">{{ group.title }}</bdi>
                    </v-list-subheader>
                    <v-list-item
                        v-for="link in group.links"
                        :key="`${group.title}:${link.key}`"
                        data-test="cite-external-link"
                        @click="pickExternal(link)"
                    >
                        <template #prepend>
                            <!-- No token: citing copies the link into the form's links under a new key. -->
                            <v-icon
                                size="small"
                                class="cite-menu__icon"
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
            </v-list>
        </v-card>
    </v-menu>
</template>

<script setup lang="ts">
    import { computed, ref, watch } from 'vue'
    import { useI18n } from 'vue-i18n'
    import SearchField from '@/components/common/SearchField.vue'
    import { ICONS } from '@/config/ui-constants'
    import { linkToken, shortUrl, type CitableLink, type ExternalLink } from '@/utils/linkReferences'

    /** More links than this, and the menu offers a search. */
    const SEARCH_THRESHOLD = 8

    const props = withDefaults(
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

    const open = ref(false)
    const query = ref<string | undefined>('')

    const offered = computed(() => props.links.length + props.groups.reduce((count, group) => count + group.links.length, 0))
    const searchable = computed(() => offered.value > SEARCH_THRESHOLD)

    // Clearing the search sets null, whatever the model's type says.
    const needle = computed(() => (searchable.value ? (query.value ?? '').trim().toLowerCase() : ''))
    const matches = (text: string): boolean => text.toLowerCase().includes(needle.value)

    // A link is found by its URL or its token; a report's links also by the report's title.
    const shownLinks = computed(() => props.links.filter((link) => matches(link.url) || matches(linkToken(link.key))))
    const shownGroups = computed(() =>
        props.groups
            .map((group) => (matches(group.title) ? group : { ...group, links: group.links.filter((link) => matches(link.url)) }))
            .filter((group) => group.links.length > 0)
    )

    watch(open, (isOpen) => {
        if (isOpen) {
            query.value = ''
        }
    })

    const pick = (link: CitableLink): void => {
        emit('pick', link)
        open.value = false
    }

    const pickExternal = (link: ExternalLink): void => {
        emit('pick-external', link)
        open.value = false
    }

    /** Enter in the search cites the first link found. */
    const pickFirst = (): void => {
        const [link] = shownLinks.value
        if (link) {
            pick(link)
            return
        }
        const external = shownGroups.value[0]?.links[0]
        if (external) {
            pickExternal(external)
        }
    }
</script>

<style scoped>
    .cite-menu__token {
        margin-inline-end: 8px;
        color: rgb(var(--v-theme-primary));
        font-weight: 600;
    }

    .cite-menu__icon {
        margin-inline-end: 8px;
        color: rgb(var(--v-theme-primary));
    }
</style>
