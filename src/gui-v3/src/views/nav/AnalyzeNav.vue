<template>
  <v-list density="compact" class="pa-0">
    <!-- Section icon -->
    <v-list-item class="justify-center pa-2">
      <v-icon :color="iconColor" size="large">mdi-file-table</v-icon>
    </v-list-item>

    <v-divider class="mx-2" :color="dividerColor" />

    <!-- Group links -->
    <v-list-item
      v-for="link in links"
      :key="link.route"
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
            {{ link.translate ? $t(link.title) : link.title }}
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
import { useAnalyzeStore } from '@/stores/analyze'

const router = useRouter()
const route = useRoute()
const { global: themeGlobal } = useTheme()
const analyzeStore = useAnalyzeStore()

const groups = ref([])
const links = ref([])

const isDark = computed(() => themeGlobal.name.value === 'dark')
const textColor = computed(() => isDark.value ? '#ffffff' : '#000000')
const iconColor = computed(() => isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)')
const dividerColor = computed(() => isDark.value ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.12)')

onMounted(async () => {
  try {
    await analyzeStore.loadReportItemGroups()
    groups.value = analyzeStore.getReportItemGroups

    // Add local link
    links.value.push({
      icon: 'mdi-home-circle-outline',
      title: 'nav_menu.local',
      translate: true,
      route: '/analyze/local'
    })

    // Add group links (groups are just strings)
    const groupArray = Array.isArray(groups.value) ? groups.value : []
    for (let i = 0; i < groupArray.length; i++) {
      links.value.push({
        icon: 'mdi-arrow-down-bold-circle-outline',
        title: groupArray[i],
        translate: false,
        route: '/analyze/group-' + groupArray[i].replaceAll(' ', '-')
      })
    }

    // If not on a specific scope route, redirect to local
    if (!route.params.scope) {
      router.push('/analyze/local')
    }
  } catch (error) {
    console.error('Error loading report item groups:', error)
  }
})
</script>

<style scoped>
.v-list-item {
  min-height: auto;
}
</style>
