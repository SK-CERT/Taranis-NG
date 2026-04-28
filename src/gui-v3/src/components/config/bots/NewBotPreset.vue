<template>
  <v-dialog
    v-model="dialog"
    max-width="800"
    persistent
    scrollable
  >
    <template #activator="{ props: activatorProps }">
      <v-btn
        v-if="canCreate"
        v-bind="activatorProps"
        color="primary"
        prepend-icon="mdi-plus"
      >
        {{ t('common.add_btn') }}
      </v-btn>
    </template>

    <v-card>
      <v-card-title>
        <span class="text-h5">
          {{ isEdit ? t('bot_preset.edit') : t('bot_preset.add_new') }}
        </span>
      </v-card-title>

      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-select
            v-model="selectedNode"
            :items="nodes"
            item-title="name"
            item-value="id"
            return-object
            :label="t('bot_preset.node')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :disabled="isEdit || saving || loadingNodes"
            :loading="loadingNodes"
            :rules="[(v) => !!v || t('error.required')]"
          />

          <v-select
            v-if="selectedNode"
            v-model="selectedBot"
            :items="selectedNode.bots || []"
            item-title="name"
            item-value="id"
            return-object
            :label="t('bot_preset.bot')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :disabled="isEdit || saving"
            :rules="[(v) => !!v || t('error.required')]"
          />

          <v-text-field
            v-if="selectedBot"
            v-model="localItem.name"
            :label="t('bot_preset.name')"
            variant="outlined"
            density="comfortable"
            class="mb-3"
            :rules="[(v) => !!v || t('error.required')]"
            :disabled="saving"
          />

          <v-textarea
            v-if="selectedBot"
            v-model="localItem.description"
            :label="t('bot_preset.description')"
            variant="outlined"
            density="comfortable"
            rows="3"
            class="mb-3"
            :disabled="saving"
          />

          <!-- Dynamic Parameter Fields -->
          <div v-if="selectedBot && selectedBot.parameters && selectedBot.parameters.length > 0">
            <v-divider class="my-4" />
            <h3 class="text-subtitle-1 mb-3">{{ t('bot_preset.parameters') }}</h3>

            <div
              v-for="(param, index) in selectedBot.parameters"
              :key="param.key || index"
              class="mb-3"
            >
              <v-row align="center">
                <v-col cols="11">
                  <v-text-field
                    v-model="parameterValues[index]"
                    :label="param.name"
                    :type="param.key && param.key.includes('PASSWORD') ? 'password' : 'text'"
                    variant="outlined"
                    density="comfortable"
                    :disabled="saving"
                    :placeholder="param.default_value"
                  />
                </v-col>
                <v-col cols="1">
                  <v-tooltip location="top">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" color="primary">mdi-help-circle</v-icon>
                    </template>
                    <span>{{ param.description }}</span>
                  </v-tooltip>
                </v-col>
              </v-row>
            </div>
          </div>

          <v-alert
            v-if="showValidationError"
            type="error"
            density="compact"
            class="mb-3"
          >
            {{ t('error.validation') }}
          </v-alert>

          <v-alert
            v-if="showError"
            type="error"
            density="compact"
            class="mb-3"
          >
            {{ t('bot_preset.error') }}
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
          :disabled="saving || !selectedBot"
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
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AddNewButton from '@/components/common/buttons/AddNewButton.vue'
import { useAuth } from '@/composables/useAuth'
import { createNewBotPreset, updateBotPreset, getAllBotsNodes } from '@/api/config'

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
const loadingNodes = ref(false)
const showValidationError = ref(false)
const showError = ref(false)

const nodes = ref([])
const selectedNode = ref(null)
const selectedBot = ref(null)
const parameterValues = ref([])

const defaultItem = {
  id: null,
  name: '',
  description: '',
  bot_id: null,
  parameter_values: []
}

const localItem = ref({ ...defaultItem })

const isEdit = computed(() => !!localItem.value.id)
const canCreate = computed(() => checkPermission('CONFIG_BOT_PRESET_CREATE'))

// Watch for edit item changes
watch(
  () => props.editItem,
  (newVal) => {
    if (newVal) {
      localItem.value = { ...newVal }

      // Find and set the node and bot
      for (const node of nodes.value) {
        const bot = node.bots?.find((b) => b.id === newVal.bot_id)
        if (bot) {
          selectedNode.value = node
          selectedBot.value = bot

          // Map parameter values
          parameterValues.value =
            bot.parameters?.map((param) => {
              const paramValue = newVal.parameter_values?.find((pv) => pv.parameter.id === param.id)
              return paramValue ? paramValue.value : param.default_value || ''
            }) || []
          break
        }
      }

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

// Watch selected bot to initialize parameter values
watch(selectedBot, (newBot) => {
  if (!isEdit.value && newBot && newBot.parameters) {
    parameterValues.value = newBot.parameters.map((param) => param.default_value || '')
  }
})

// Load bots nodes on mount
onMounted(async () => {
  await loadNodes()
})

const loadNodes = async () => {
  loadingNodes.value = true
  try {
    const response = await getAllBotsNodes({ search: '' })
    nodes.value = response.items || []

    // Auto-select first node and bot if available
    if (!isEdit.value && nodes.value.length > 0) {
      selectedNode.value = nodes.value[0]
      if (selectedNode.value.bots && selectedNode.value.bots.length > 0) {
        selectedBot.value = selectedNode.value.bots[0]
      }
    }
  } catch (error) {
    console.error('Error loading bots nodes:', error)
  } finally {
    loadingNodes.value = false
  }
}

const resetForm = () => {
  localItem.value = { ...defaultItem }
  selectedNode.value = null
  selectedBot.value = null
  parameterValues.value = []
  showValidationError.value = false
  showError.value = false
  if (formRef.value) {
    formRef.value.resetValidation()
  }
}

const cancel = () => {
  dialog.value = false
}

const handleSubmit = async () => {
  showValidationError.value = false
  showError.value = false

  const { valid } = await formRef.value.validate()

  if (!valid || !selectedBot.value) {
    showValidationError.value = true
    return
  }

  saving.value = true

  try {
    // Prepare parameter values
    const paramValues =
      selectedBot.value.parameters?.map((param, index) => ({
        value: parameterValues.value[index] || param.default_value || '',
        parameter: param
      })) || []

    const payload = {
      ...localItem.value,
      bot_id: selectedBot.value.id,
      parameter_values: paramValues
    }

    if (isEdit.value) {
      await updateBotPreset(payload)
      window.dispatchEvent(
        new CustomEvent('notification', {
          detail: { type: 'success', loc: 'common.updated_successfully' }
        })
      )
    } else {
      await createNewBotPreset(payload)
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
