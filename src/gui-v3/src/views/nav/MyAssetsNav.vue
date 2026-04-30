<template>
  <v-list density="compact" class="pa-0">
    <!-- Section icon -->
    <v-list-item class="justify-center pa-2">
      <v-icon :color="iconColor" size="large">mdi-file-cabinet</v-icon>
    </v-list-item>

    <v-divider class="mx-2" :color="dividerColor" />

    <!-- Asset group links -->
    <v-list-item
      v-for="link in links"
      :key="link.id"
      :to="link.route"
      class="px-1 py-2"
      density="compact"
    >
      <template #default>
        <div class="d-flex flex-column align-center text-center">
          <v-icon :color="iconColor" size="small" class="mb-1">
            {{ link.icon }}
          </v-icon>
          <span class="text-caption" :style="{ color: textColor, fontSize: '0.65rem', lineHeight: '1.2' }">
            {{ link.title }}
          </span>
        </div>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useAssetsStore } from '@/stores/assets'

const router = useRouter()
const route = useRoute()
const { global: themeGlobal } = useTheme()
const assetsStore = useAssetsStore()

const groups = ref([])
const links = ref([])

const isDark = computed(() => themeGlobal.name.value === 'dark')
const textColor = computed(() => isDark.value ? '#ffffff' : '#000000')
const iconColor = computed(() => isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)')
const dividerColor = computed(() => isDark.value ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.12)')

onMounted(async () => {
  try {
    await assetsStore.loadAssetGroups({ search: '' })
    const assetGroups = assetsStore.asset_groups?.items || []
    groups.value = Array.isArray(assetGroups) ? assetGroups : []

    // Build links from asset groups
    for (let i = 0; i < groups.value.length; i++) {
      links.value.push({
        icon: 'mdi-folder-multiple',
        title: groups.value[i].name,
        route: '/myassets/group/' + groups.value[i].id,
        id: groups.value[i].id
      })
    }

    // If not on a specific group route and links exist, redirect to first
    if (!route.path.includes('/group/') && links.value.length > 0) {
      router.push(links.value[0].route)
    }
  } catch (error) {
    console.error('Error loading asset groups:', error)
  }
})
</script>

<style scoped>
.v-list-item {
  min-height: auto;
}
</style>
