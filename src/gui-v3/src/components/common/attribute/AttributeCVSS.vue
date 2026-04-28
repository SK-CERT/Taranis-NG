<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="numbered-cvss-value">
          <span v-if="values.length > 1" class="cvss-number text--disabled">{{ index + 1 }}.</span>
          <v-chip :color="getCVSSColor(values[index].value)" size="small" class="mr-2">
            {{ values[index].value }}
          </v-chip>
          <span class="text-caption text-grey">{{ getCVSSSeverity(values[index].value) }}</span>
        </span>

        <!-- Editable -->
        <AttributeValueLayout
          v-if="!readOnly && canModify && !values[index].remote"
          :del-button="true"
          :occurrence="attributeGroup.min_occurrence"
          :values="values"
          :val-index="index"
          @del-value="del(index)"
        >
          <template #col_left>
            <CalculatorCVSS
              :model-value="values[index].value"
              :disabled="values[index].locked || !canModify"
              @update:model-value="(v) => updateFromCalculator(index, v)"
            />
          </template>
          <template #col_middle>
            <v-text-field
              v-model="values[index].value"
              density="compact"
              variant="outlined"
              label="CVSS Vector / Score"
              :rules="[vectorRule]"
              :class="getLockedStyle(index)"
              :disabled="values[index].locked || !canModify"
              @focus="onFocus(index)"
              @blur="onBlur(index)"
              @keyup="onKeyUp(index)"
            />

            <!-- Score display for vector strings (always rendered to reserve space) -->
            <div class="score-display" :style="{ visibility: getVectorScores(values[index].value) ? 'visible' : 'hidden' }">
              <v-row justify="center" no-gutters>
                <template v-if="getVectorScores(values[index].value)">
                  <v-col
                    v-for="scoreItem in getVectorScores(values[index].value)"
                    :key="scoreItem.name"
                    class="pa-0 mx-1 severity-box"
                    :class="scoreItem.severityClass"
                  >
                    <span class="text-body-2 text-white">{{ scoreItem.label }} </span>
                    <span class="text-body-2 text-white font-weight-bold text-uppercase">{{ scoreItem.severityLabel }}</span>
                    <br>
                    <span class="text-subtitle-1 font-weight-medium score-value">{{ scoreItem.score }}</span>
                  </v-col>
                </template>
                <template v-else>
                  <v-col class="pa-0 mx-1 severity-box severity-na" style="min-height: 48px">&nbsp;</v-col>
                </template>
              </v-row>
            </div>
          </template>
        </AttributeValueLayout>
      </div>
    </template>
  </AttributeItemLayout>
</template>

<script setup>
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'
import CalculatorCVSS from '../CalculatorCVSS.vue'
import { useAttributes } from './useAttributes.js'
import { calculateScoreItems, detectVersion, createInstance, stripParentheses } from '../cvss-utils.js'

const { t, te } = useI18n()

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

const { canModify, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp } = useAttributes(props)

// Auto-add first empty entry so the text field is always visible
onMounted(() => {
  if (props.values?.length === 0 && canModify.value && !props.readOnly) {
    add()
  }
})

const vectorRule = (value) => {
  if (!value || value === '') return true
  const cleaned = stripParentheses(value)
  // Accept plain numeric scores (0.0 - 10.0)
  if (/^(10(\.0)?|[0-9](\.[0-9])?)$/.test(cleaned)) return true
  // Validate vector strings using the library
  try {
    const version = detectVersion(cleaned)
    if (!version) return t('cvss_calculator.validator')
    createInstance(version, cleaned)
    return true
  } catch {
    return t('cvss_calculator.validator')
  }
}

function updateFromCalculator(index, vectorValue) {
  props.values[index].value = vectorValue
  onKeyUp(index)
}

function getVectorScores(value) {
  return calculateScoreItems(value, t, te)
}

const getCVSSColor = (score) => {
  const s = parseFloat(score)
  if (s >= 9.0) return 'error'
  if (s >= 7.0) return 'deep-orange'
  if (s >= 4.0) return 'warning'
  if (s > 0) return 'success'
  return 'grey'
}

const getCVSSSeverity = (score) => {
  const s = parseFloat(score)
  if (s >= 9.0) return 'Critical'
  if (s >= 7.0) return 'High'
  if (s >= 4.0) return 'Medium'
  if (s > 0) return 'Low'
  return 'None'
}
</script>

<style scoped>
.cvss-number {
  margin-right: 8px;
  user-select: none;
  min-width: 24px;
  display: inline-block;
}

.numbered-cvss-value {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}

.score-display {
  margin-bottom: 8px;
}

.severity-box {
  border-radius: 4px;
  padding: 4px 8px;
  max-width: 200px;
  text-align: center;
  transition: background-color 250ms;
}

.severity-none {
  background-color: #53aa33;
}
.severity-low {
  background-color: #ffcb0d;
}
.severity-medium {
  background-color: #f9a009;
}
.severity-high {
  background-color: #df3d03;
}
.severity-critical {
  background-color: red;
}

.score-value {
  display: block;
  line-height: 1.4;
}
</style>
