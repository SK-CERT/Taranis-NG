<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.bot_presets"
      :total-count="configStore.botPresets.total_count"
      total-count-title="bot_preset.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewBotPreset :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.botPresets.items"
      card-item="CardCompact"
      delete-permission="CONFIG_BOT_PRESET_DELETE"
      :loading="loading"
      @delete="handleDelete"
      @edit="handleEdit"
      @refresh="loadData"
    />
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfigStore } from '@/stores/config'
import { deleteBotPreset } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewBotPreset from '@/components/config/bots/NewBotPreset.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadBotPresets(filter.value)
  } catch (error) {
    console.error('Error loading bot presets:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (preset) => {
  try {
    await deleteBotPreset(preset)
    console.log('Bot preset deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting bot preset:', error)
  }
}

const handleEdit = (item) => {
  editItem.value = item
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
