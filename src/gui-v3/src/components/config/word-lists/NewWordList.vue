<template>
  <v-dialog
    v-model="dialog"
    max-width="1200"
    persistent
    scrollable
    fullscreen
  >
    <template #activator="{ props: activatorProps }">
      <AddNewButton :show="canCreate" v-bind="activatorProps" />
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <span class="text-h5">
          {{ isEdit ? t('word_list.edit') : t('word_list.add_new') }}
        </span>
        <v-spacer />
        <v-btn icon :disabled="saving" @click="cancel">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-row>
            <v-col cols="12">
              <v-text-field
                v-model="localItem.name"
                :label="t('word_list.name')"
                variant="outlined"
                density="comfortable"
                :rules="[(v) => !!v || t('error.required')]"
                :disabled="saving"
              />
            </v-col>
            <v-col cols="12">
              <v-textarea
                v-model="localItem.description"
                :label="t('word_list.description')"
                variant="outlined"
                density="comfortable"
                rows="3"
                :disabled="saving"
              />
            </v-col>
            <v-col cols="12">
              <v-checkbox
                v-model="localItem.use_for_stop_words"
                :label="t('word_list.use_for_stop_words')"
                color="primary"
                :disabled="saving"
              />
            </v-col>
          </v-row>

          <v-divider class="my-4" />

          <v-row>
            <v-col cols="12">
              <div class="d-flex align-center mb-3">
                <h3 class="text-h6">{{ t('word_list.categories') }}</h3>
                <v-spacer />
                <v-btn
                  color="primary"
                  prepend-icon="mdi-plus"
                  :disabled="saving"
                  @click="addCategory"
                >
                  {{ t('word_list.new_category') }}
                </v-btn>
              </div>

              <!-- Categories -->
              <v-expansion-panels v-model="expandedPanels" multiple>
                <v-expansion-panel
                  v-for="(category, index) in localItem.categories"
                  :key="index"
                  :value="index"
                >
                  <v-expansion-panel-title>
                    <div class="d-flex align-center w-100">
                      <v-icon class="mr-2">mdi-folder-outline</v-icon>
                      <strong>
                        {{ category.name || t('word_list.category') + ' ' + (index + 1) }}
                      </strong>
                      <v-spacer />
                      <v-btn
                        icon
                        size="small"
                        variant="text"
                        color="error"
                        :disabled="saving"
                        @click.stop="deleteCategory(index)"
                      >
                        <v-icon color="error">{{ ICONS.DELETE }}</v-icon>
                      </v-btn>
                    </div>
                  </v-expansion-panel-title>

                  <v-expansion-panel-text>
                    <v-row>
                      <v-col cols="12">
                        <v-text-field
                          v-model="category.name"
                          :label="t('word_list.name')"
                          variant="outlined"
                          density="comfortable"
                          :disabled="saving"
                        />
                      </v-col>
                      <v-col cols="12">
                        <v-textarea
                          v-model="category.description"
                          :label="t('word_list.description')"
                          variant="outlined"
                          density="comfortable"
                          rows="2"
                          :disabled="saving"
                        />
                      </v-col>
                      <v-col cols="12">
                        <v-text-field
                          v-model="category.link"
                          :label="t('word_list.link')"
                          variant="outlined"
                          density="comfortable"
                          hint="Optional URL for downloading word entries"
                          :disabled="saving"
                        />
                      </v-col>
                    </v-row>

                    <v-divider class="my-3" />

                    <!-- Words/Entries for this category -->
                    <div class="mb-3">
                      <div class="d-flex align-center mb-2">
                        <h4 class="text-subtitle-1">{{ t('word_list.words') }}</h4>
                        <v-spacer />
                        <v-btn
                          size="small"
                          color="primary"
                          prepend-icon="mdi-plus"
                          :disabled="saving"
                          @click="addWord(index)"
                        >
                          {{ t('word_list.new_word') }}
                        </v-btn>
                      </div>

                      <v-data-table
                        :headers="wordHeaders"
                        :items="category.entries || []"
                        density="compact"
                        :items-per-page="5"
                      >
                        <template #item.value="{ item }">
                          <v-text-field
                            v-model="item.value"
                            variant="outlined"
                            density="compact"
                            hide-details
                            :disabled="saving"
                          />
                        </template>
                        <template #item.description="{ item }">
                          <v-text-field
                            v-model="item.description"
                            variant="outlined"
                            density="compact"
                            hide-details
                            :disabled="saving"
                          />
                        </template>
                        <template #item.actions="{ item }">
                          <v-btn
                            icon
                            size="small"
                            variant="text"
                            color="error"
                            :disabled="saving"
                            @click="deleteWord(index, category.entries.indexOf(item))"
                          >
                            <v-icon color="error">{{ ICONS.DELETE }}</v-icon>
                          </v-btn>
                        </template>
                        <template #no-data>
                          <div class="text-center pa-4 text-grey">
                            {{ t('word_list.no_words') }}
                          </div>
                        </template>
                      </v-data-table>
                    </div>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>

              <div v-if="localItem.categories.length === 0" class="text-center pa-8 text-grey">
                <v-icon size="64" color="grey-lighten-1">mdi-folder-open-outline</v-icon>
                <div class="text-h6 mt-2">{{ t('word_list.no_categories') }}</div>
                <div class="text-body-2">{{ t('word_list.add_category_hint') }}</div>
              </div>
            </v-col>
          </v-row>

          <v-alert
            v-if="showValidationError"
            type="error"
            density="compact"
            class="mb-3 mt-4"
          >
            {{ t('error.validation') }}
          </v-alert>

          <v-alert
            v-if="showError"
            type="error"
            density="compact"
            class="mb-3 mt-4"
          >
            {{ t('word_list.error') }}
          </v-alert>
        </v-form>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn
          color="grey"
          variant="text"
          :disabled="saving"
          @click="cancel"
        >
          {{ t('common.cancel') }}
        </v-btn>
        <v-btn
          color="primary"
          variant="text"
          :loading="saving"
          :disabled="saving"
          @click="handleSubmit"
        >
          <v-icon start>mdi-content-save</v-icon>
          {{ t('common.save') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ICONS } from '@/config/ui-constants'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import { useAuth } from '@/composables/useAuth'
import { createNewWordList, updateWordList } from '@/api/config'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  editItem: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()
const { checkPermission } = useAuth()

const dialog = ref(false)
const formRef = ref(null)
const saving = ref(false)
const showValidationError = ref(false)
const showError = ref(false)
const expandedPanels = ref([])

const defaultItem = {
  id: null,
  name: '',
  description: '',
  use_for_stop_words: false,
  categories: []
}

const localItem = ref({ ...defaultItem })

const isEdit = computed(() => !!localItem.value.id)
const canCreate = computed(() => checkPermission('CONFIG_WORD_LIST_CREATE'))

const wordHeaders = [
  { title: t('word_list.value'), key: 'value', sortable: true, width: '40%' },
  { title: t('word_list.description'), key: 'description', sortable: false, width: '50%' },
  { title: t('common.actions'), key: 'actions', sortable: false, width: '10%', align: 'center' }
]

// Watch for edit item changes
watch(
  () => props.editItem,
  (newVal) => {
    if (newVal) {
      localItem.value = JSON.parse(JSON.stringify(newVal)) // Deep clone

      // Expand all panels when editing
      expandedPanels.value = localItem.value.categories.map((_, index) => index)

      dialog.value = true
    }
  },
  { immediate: true, deep: true }
)

// Watch dialog state
watch(dialog, (newVal) => {
  if (!newVal) {
    resetForm()
  }
  emit('update:modelValue', newVal)
})

const resetForm = () => {
  localItem.value = { ...defaultItem, categories: [] }
  expandedPanels.value = []
  showValidationError.value = false
  showError.value = false
  if (formRef.value) {
    formRef.value.resetValidation()
  }
}

const cancel = () => {
  dialog.value = false
}

const addCategory = () => {
  localItem.value.categories.push({
    name: '',
    description: '',
    link: '',
    entries: []
  })
  // Expand the newly added category
  expandedPanels.value.push(localItem.value.categories.length - 1)
}

const deleteCategory = (index) => {
  localItem.value.categories.splice(index, 1)
  // Update expanded panels
  expandedPanels.value = expandedPanels.value
    .filter((p) => p !== index)
    .map((p) => (p > index ? p - 1 : p))
}

const addWord = (categoryIndex) => {
  if (!localItem.value.categories[categoryIndex].entries) {
    localItem.value.categories[categoryIndex].entries = []
  }
  localItem.value.categories[categoryIndex].entries.push({
    value: '',
    description: ''
  })
}

const deleteWord = (categoryIndex, wordIndex) => {
  localItem.value.categories[categoryIndex].entries.splice(wordIndex, 1)
}

const handleSubmit = async () => {
  showValidationError.value = false
  showError.value = false

  const { valid } = await formRef.value.validate()

  if (!valid) {
    showValidationError.value = true
    return
  }

  saving.value = true

  try {
    if (isEdit.value) {
      await updateWordList(localItem.value)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.updated_successfully' }
        })
      )
    } else {
      await createNewWordList(localItem.value)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.created_successfully' }
        })
      )
    }

    dialog.value = false
    emit('saved')
  } catch (error) {
    window.dispatchEvent(
      new CustomEvent('notification', {
        detail: { type: 'error', loc: 'common.error_saving' }
      })
    )
    showError.value = true
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.w-100 {
  width: 100%;
}
</style>
