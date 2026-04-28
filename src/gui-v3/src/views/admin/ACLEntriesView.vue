<template>
  <v-container fluid class="pa-0">
    <!-- Toolbar -->
    <ToolbarFilter
      title="nav_menu.acls"
      :total-count="configStore.acls.total_count"
      total-count-title="acl.total_count"
      @update-filter="handleFilterUpdate"
    >
      <template #addbutton>
        <NewACL :edit-item="editItem" @saved="handleSaved" />
      </template>
    </ToolbarFilter>

    <!-- Content -->
    <ContentData
      :items="configStore.acls.items"
      card-item="CardCompact"
      delete-permission="CONFIG_ACL_DELETE"
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
import { deleteACLEntry } from '@/api/config'
import ToolbarFilter from '@/components/common/ToolbarFilter.vue'
import ContentData from '@/components/common/ContentData.vue'
import NewACL from '@/components/config/acl/NewACL.vue'

const { t } = useI18n()
const configStore = useConfigStore()

const loading = ref(false)
const filter = ref({ search: '' })
const editItem = ref(null)

const loadData = async () => {
  loading.value = true
  try {
    await configStore.loadACLEntries(filter.value)
  } catch (error) {
    console.error('Error loading ACL entries:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterUpdate = (newFilter) => {
  filter.value = newFilter
  loadData()
}

const handleDelete = async (acl) => {
  try {
    await deleteACLEntry(acl)
    console.log('ACL entry deleted successfully')
    await loadData()
  } catch (error) {
    console.error('Error deleting ACL entry:', error)
  }
}

const handleEdit = (acl) => {
  editItem.value = acl
}

const handleSaved = () => {
  editItem.value = null
  loadData()
}

onMounted(() => {
  loadData()
})
</script>
