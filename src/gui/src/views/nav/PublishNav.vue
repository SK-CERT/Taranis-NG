<template>
    <NavSkeleton v-if="loading" />
    <GroupNavList
        v-else
        :groups="links"
        :active-id="activeId"
        title-key="nav_menu.product_presets"
        @select="onSelect"
    />
</template>

<script setup lang="ts">
    import { computed, ref, onMounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { getAllUserProductPresets } from '@/api/user'
    import GroupNavList from '@/components/common/GroupNavList.vue'
    import NavSkeleton from '@/components/common/NavSkeleton.vue'
    import { ICONS } from '@/config/ui-constants'
    import { DEFAULT_PRODUCT_ICON, type ProductPreset } from '@/types/product-presets'
    import { type GroupNavItem } from '@/types/routing'

    const ALL = 'all'
    const ALL_LINK: GroupNavItem = { id: ALL, icon: ICONS.FOLDER_MULTIPLE, title: 'publish.all_products', translate: true, route: '/publish' }

    const router = useRouter()
    const route = useRoute()

    const loading = ref(true)
    const links = ref<GroupNavItem[]>([ALL_LINK])

    // Highlight the product preset of the current /publish/:productPresetId route, All without one.
    const activeId = computed(() => String(route.params['productPresetId'] || ALL))

    const onSelect = (link: { route?: string }): void => {
        if (link.route) router.push(link.route)
    }

    onMounted(async () => {
        try {
            const response = await getAllUserProductPresets()
            const productPresets = (response?.data?.items as ProductPreset[]) || []
            links.value = [
                ALL_LINK,
                ...productPresets.map((productPreset) => ({
                    id: String(productPreset.id),
                    icon: productPreset.icon || DEFAULT_PRODUCT_ICON,
                    title: productPreset.name,
                    translate: false,
                    route: `/publish/${productPreset.id}`
                }))
            ]
            // A product preset the user may no longer see (deleted, or its ACL changed): list them all.
            if (!links.value.some((link) => link.id === activeId.value)) {
                router.replace('/publish')
            }
        } catch (error) {
            console.error('Error loading product presets:', error)
        } finally {
            loading.value = false
        }
    })
</script>
