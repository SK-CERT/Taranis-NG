<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="tlp-holder">
        <!-- Read-only or remote -->
        <div v-if="readOnly || values[index].remote" class="tlp-display">
          <div
            class="tlp-badge"
            :style="getTLPStyle(values[index].value)"
          >
            {{ values[index].value || '—' }}
          </div>
          <span class="tlp-description">{{ getTLPDescription(values[index].value) }}</span>
        </div>

        <!-- Editable -->
        <AttributeValueLayout
          v-if="!readOnly && canModify && !values[index].remote"
          :del-button="true"
          :occurrence="attributeGroup.min_occurrence"
          :values="values"
          :val-index="index"
          @del-value="del(index)"
        >
          <template #col_middle>
            <div class="tlp-selector">
              <div class="tlp-options">
                <button
                  v-for="tlp in tlpOptions"
                  :key="tlp"
                  class="tlp-button"
                  :class="{ active: values[index].value === tlp }"
                  :style="getTLPStyle(tlp)"
                  :disabled="values[index].locked || !canModify"
                  @click="values[index].value = tlp; onEdit(index)"
                >
                  {{ tlp }}
                </button>
              </div>
              <div v-if="values[index].value" class="tlp-info">
                {{ getTLPDescription(values[index].value) }}
              </div>
            </div>
          </template>
        </AttributeValueLayout>
      </div>
    </template>
  </AttributeItemLayout>
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'
import { useAttributes } from './useAttributes.js'

const props = defineProps({
  attributeGroup: {
    type: Object,
    required: true
  },
  values: {
    type: Array,
    required: true
  },
  readOnly: {
    type: Boolean,
    default: false
  },
  edit: {
    type: Boolean,
    default: false
  },
  modify: {
    type: Boolean,
    default: false
  },
  reportItemId: {
    type: Number,
    required: true
  }
})

const { t } = useI18n()
const { canModify, addButtonVisible, add, del, onEdit } = useAttributes(props)

onMounted(() => {
  if (props.values?.length === 0 && canModify.value && !props.readOnly) {
    add()
  }
})

// Set CLEAR as default for new values
watch(
  () => props.values,
  (newValues) => {
    newValues.forEach((val) => {
      if (!val.value) {
        val.value = 'CLEAR'
      }
    })
  },
  { immediate: true, deep: true }
)

// TLP (Traffic Light Protocol) options in order
const tlpOptions = ['CLEAR', 'GREEN', 'AMBER', 'AMBER+STRICT', 'RED']

// TLP color definitions
const tlpColors = {
  'CLEAR': { bg: '#ffffff', text: '#000000' },
  'GREEN': { bg: '#33FF00', text: '#000000' },
  'AMBER': { bg: '#FFC000', text: '#000000' },
  'AMBER+STRICT': { bg: '#FFC000', text: '#000000' },
  'RED': { bg: '#FF2B2B', text: '#ffffff' }
}

// TLP descriptions
const tlpDescriptions = {
  'CLEAR': 'Unrestricted - Information may be distributed without restriction',
  'GREEN': 'Community - Information may be shared within communities',
  'AMBER': 'Limited Sharing - Information should not be publicly disclosed',
  'AMBER+STRICT': 'Strictly Limited Sharing - Information should not be shared outside the organization',
  'RED': 'Not for Sharing - Information may not be shared with anyone'
}

const getTLPStyle = (tlp) => {
  const config = tlpColors[tlp]
  if (!config) {
    return {
      backgroundColor: '#666666',
      color: '#ffffff'
    }
  }
  return {
    backgroundColor: config.bg,
    color: config.text
  }
}

const getTLPDescription = (tlp) => {
  return tlpDescriptions[tlp] || 'Unknown TLP level'
}
</script>

<style scoped>
.tlp-holder {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.tlp-display {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tlp-badge {
  padding: 6px 14px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.875rem;
  min-width: 80px;
  text-align: center;
}

.tlp-description {
  font-size: 0.875rem;
  color: rgba(255, 255, 255, 0.7);
}

.tlp-selector {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.tlp-options {
  display: flex;
  gap: 4px;
  width: 100%;
  flex-wrap: nowrap;
}

.tlp-button {
  padding: 6px 6px;
  border: 2px solid transparent;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.65rem;
  cursor: pointer;
  transition: all 0.2s;
  flex: 1;
  white-space: nowrap;
}

.tlp-button:not(:disabled):hover {
  border-color: rgba(255, 255, 255, 0.3);
}

.tlp-button.active {
  border-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.3);
}

.tlp-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tlp-info {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.6);
  padding: 4px 0;
}
</style>
