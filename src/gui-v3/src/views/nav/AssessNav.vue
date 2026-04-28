<template>
  <v-list density="compact" class="pa-0">
    <!-- Section icon -->
    <v-list-item class="justify-center pa-2">
      <v-icon size="large">mdi-newspaper-variant</v-icon>
    </v-list-item>

    <v-divider class="mx-2" />

    <!-- Group links -->
    <v-list-item
      v-for="group in groups"
      :key="group.id"
      :to="group.route"
      class="px-1 py-2"
      density="compact"
    >
      <template #default>
        <div class="d-flex flex-column align-center text-center">
          <v-icon :color="group.color" size="small" class="mb-1">
            {{ group.icon }}
          </v-icon>
          <span class="text-caption" style="font-size: 0.65rem; line-height: 1.2">
            {{ group.translate ? $t(group.title) : group.title }}
          </span>
        </div>
      </template>
    </v-list-item>
  </v-list>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useConfigStore } from '@/stores/config'

const router = useRouter()
const route = useRoute()
const configStore = useConfigStore()

const groups = ref([])

onMounted(async () => {
  try {
    await configStore.loadOSINTSourceGroupsAssess()
    groups.value = configStore.osintSourceGroupsForAssess

    // If not on a specific group route and groups exist, redirect to first
    if (!route.path.includes('/group/') && groups.value.length > 0) {
      router.push(groups.value[0].route)
    }
  } catch (error) {
    console.error('Error loading OSINT source groups:', error)
  }
})
</script>

<style scoped>
.v-list-item {
  min-height: auto;
}
</style>
