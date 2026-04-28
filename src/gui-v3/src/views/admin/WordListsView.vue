<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.word_lists"
      :total-count="configStore.wordLists.total_count"
      total-count-title="word_list.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewWordList :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.wordLists.items"
      card-item="CardCompact"
      delete-permission="CONFIG_WORD_LIST_DELETE"
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
import { deleteWordList } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewWordList from '@/components/config/word-lists/NewWordList.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadWordLists(filter.value)
  } catch (error) {
    console.error('Error loading word lists:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (wordList) => {
  try {
    await deleteWordList(wordList)
    console.log('Word list deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting word list:', error)
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
