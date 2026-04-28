<template>
  <v-btn
    variant="text"
    size="small"
    :disabled="disabled"
    :title="$t('report_item.tooltip.cvss_detail')"
    @click.prevent="openDialog"
  >
    <v-icon>{{ ICONS.CALCULATOR }}</v-icon>
  </v-btn>

  <v-dialog v-model="visible" fullscreen transition="dialog-bottom-transition">
    <v-card class="d-flex flex-column" style="height: 100vh">
      <!-- Sticky header -->
      <div class="calculator-header">
        <v-toolbar color="primary">
          <v-btn icon @click="cancel">
            <v-icon>{{ ICONS.CLOSE_BOX }}</v-icon>
          </v-btn>
          <v-toolbar-title>{{ $t('cvss_calculator.title') }}</v-toolbar-title>
          <v-spacer />

          <!-- Version selector tabs -->
          <v-btn-toggle
            v-model="selectedVersion"
            mandatory
            density="compact"
            variant="outlined"
            class="mr-4"
          >
            <v-btn
              v-for="ver in versionOptions"
              :key="ver"
              :value="ver"
              size="small"
            >
              {{ ver }}
            </v-btn>
          </v-btn-toggle>

          <v-switch
            v-model="showTooltips"
            label="Tooltip"
            density="compact"
            hide-details
            class="mr-4"
          />
        </v-toolbar>

        <!-- Score Header -->
        <v-sheet class="text-center pa-2" color="surface-variant">
          <v-text-field
            v-model="vectorInput"
            density="compact"
            variant="outlined"
            hide-details="auto"
            class="vector-input mx-auto mb-2"
            placeholder="Enter CVSS vector string..."
            @update:model-value="onVectorInput"
          />
          <v-row justify="center" no-gutters>
            <v-col
              v-for="scoreItem in scoreDisplay"
              :key="scoreItem.name"
              class="pa-0 mx-1 severity-box"
              :class="scoreItem.severityClass"
            >
              <span class="text-body-2 text-white">{{ scoreItem.label }} </span>
              <span class="text-body-2 text-white font-weight-bold text-uppercase">{{ scoreItem.severityLabel }}</span>
              <br>
              <span class="text-h5 font-weight-medium score-value">{{ scoreItem.score }}</span>
            </v-col>
          </v-row>
        </v-sheet>
      </div>

      <!-- Scrollable Metric Groups -->
      <v-container fluid class="pa-4 metric-scroll">
        <v-card
          v-for="(group, groupIndex) in metricGroups"
          :key="groupIndex"
          variant="outlined"
          class="mb-4"
          :class="`metric-group-${group.severityClass}`"
        >
          <v-card-title class="text-uppercase text-body-1 font-weight-bold pa-3">
            {{ group.label }}
            <v-tooltip v-if="showTooltips && group.tooltipKey" location="end" max-width="500">
              <template #activator="{ props: tp }">
                <v-icon v-bind="tp" size="x-small" class="ml-1">{{ ICONS.INFORMATION_OUTLINE }}</v-icon>
              </template>
              <span>{{ $t(group.tooltipKey) }}</span>
            </v-tooltip>
          </v-card-title>

          <v-card-text class="pt-0">
            <div v-for="metric in group.metrics" :key="metric.shortName" class="mb-3">
              <div class="d-flex align-center mb-1">
                <span class="text-primary text-body-2">{{ metric.label }}</span>
                <v-tooltip v-if="showTooltips && metric.tooltipKey" location="end" max-width="500">
                  <template #activator="{ props: tp }">
                    <v-icon v-bind="tp" size="x-small" class="ml-1">{{ ICONS.INFORMATION_OUTLINE }}</v-icon>
                  </template>
                  <span>{{ $t(metric.tooltipKey) }}</span>
                </v-tooltip>
              </div>
              <v-btn-toggle
                :model-value="getSelectedValueIndex(metric)"
                mandatory
                density="compact"
                @update:model-value="(idx) => onMetricToggle(metric, idx)"
              >
                <template v-for="(val, valIdx) in metric.values" :key="val.shortName">
                  <v-tooltip v-if="showTooltips && val.tooltipKey" location="bottom" max-width="300">
                    <template #activator="{ props: tp }">
                      <v-btn v-bind="tp" size="small" :value="valIdx">
                        <span>{{ val.label }}</span>
                        <v-icon size="small" color="primary" class="ml-1">
                          {{ 'mdi-alpha-' + val.shortName.toLowerCase() + '-box' }}
                        </v-icon>
                      </v-btn>
                    </template>
                    <span>{{ $t(val.tooltipKey) }}</span>
                  </v-tooltip>
                  <v-btn v-else size="small" :value="valIdx">
                    <span>{{ val.label }}</span>
                    <v-icon size="small" color="primary" class="ml-1">
                      {{ 'mdi-alpha-' + val.shortName.toLowerCase() + '-box' }}
                    </v-icon>
                  </v-btn>
                </template>
              </v-btn-toggle>
            </div>
          </v-card-text>
        </v-card>
      </v-container>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick, triggerRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'
import {
  VERSION_CLASSES,
  createInstance,
  stripParentheses,
  detectVersion,
  getSeverityRating,
  calculateScoreItems
} from './cvss-utils.js'

const { t, te } = useI18n()

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const versionOptions = ['2.0', '3.0', '3.1', '4.0']

const visible = ref(false)
const selectedVersion = ref('3.1')
const showTooltips = ref(false)
const cvssInstance = ref(null)
const vectorInput = ref('')

// Name-to-i18n-key mapping for metric names
const NAME_TO_I18N = {
  'Attack Vector': 'attack_vector',
  'Attack Complexity': 'attack_complexity',
  'Privileges Required': 'privileges_required',
  'User Interaction': 'user_interaction',
  'Scope': 'scope',
  'Confidentiality Impact': 'confidentiality',
  'Confidentiality': 'confidentiality',
  'Integrity Impact': 'integrity',
  'Integrity': 'integrity',
  'Availability Impact': 'availability',
  'Availability': 'availability',
  'Exploit Code Maturity': 'exploitability_code_maturity',
  'Exploitability': 'exploitability_code_maturity',
  'Remediation Level': 'remediation_level',
  'Report Confidence': 'report_confidence',
  'Confidentiality Requirement': 'confidentiality_requirement',
  'Integrity Requirement': 'integrity_requirement',
  'Availability Requirement': 'availability_requirement',
  'Modified Attack Vector': 'modified_attack_vector',
  'Modified Attack Complexity': 'modified_attack_complexity',
  'Modified Privileges Required': 'modified_privileges_required',
  'Modified User Interaction': 'modified_user_interaction',
  'Modified Scope': 'modified_scope',
  'Modified Confidentiality': 'modified_confidentiality',
  'Modified Integrity': 'modified_integrity',
  'Modified Availability': 'modified_availability',
  // CVSS 2.0 specific
  'Authentication': 'authentication',
  'Collateral Damage Potential': 'collateral_damage_potential',
  'Target Distribution': 'target_distribution',
  // CVSS 4.0 specific
  'Attack Requirements': 'attack_requirements',
  'Vulnerable System Confidentiality': 'vulnerable_system_confidentiality',
  'Vulnerable System Integrity': 'vulnerable_system_integrity',
  'Vulnerable System Availability': 'vulnerable_system_availability',
  'Subsequent System Confidentiality': 'subsequent_system_confidentiality',
  'Subsequent System Integrity': 'subsequent_system_integrity',
  'Subsequent System Availability': 'subsequent_system_availability',
  'Modified Vulnerable System Confidentiality': 'modified_vulnerable_system_confidentiality',
  'Modified Vulnerable System Integrity': 'modified_vulnerable_system_integrity',
  'Modified Vulnerable System Availability': 'modified_vulnerable_system_availability',
  'Modified Subsequent System Confidentiality': 'modified_subsequent_system_confidentiality',
  'Modified Subsequent System Integrity': 'modified_subsequent_system_integrity',
  'Modified Subsequent System Availability': 'modified_subsequent_system_availability',
  'Modified Attack Requirements': 'modified_attack_requirements',
  'Safety': 'safety',
  'Automatable': 'automatable',
  'Recovery': 'recovery',
  'Value Density': 'value_density',
  'Vulnerability Response Effort': 'vulnerability_response_effort',
  'Provider Urgency': 'provider_urgency'
}

const VALUE_NAME_TO_I18N = {
  'Network': 'network',
  'Adjacent': 'adjacent',
  'Adjacent Network': 'adjacent_network',
  'Local': 'local',
  'Physical': 'physical',
  'Low': 'low',
  'High': 'high',
  'None': 'none',
  'Required': 'required',
  'Unchanged': 'unchanged',
  'Changed': 'changed',
  'Not Defined': 'not_defined',
  'Medium': 'medium',
  'Unproven': 'unproven',
  'Proof-of-Concept': 'proof_of_concept',
  'Proof of Concept': 'proof_of_concept',
  'Functional': 'functional',
  'Official Fix': 'official_fix',
  'Temporary Fix': 'temporary_fix',
  'Workaround': 'workaround',
  'Unavailable': 'unavailable',
  'Unknown': 'unknown',
  'Reasonable': 'reasonable',
  'Confirmed': 'confirmed',
  // CVSS 2.0 specific
  'Multiple': 'multiple',
  'Single': 'single',
  // CVSS 4.0 specific
  'Present': 'present',
  'Active': 'active',
  'Passive': 'passive',
  'Attacked': 'attacked',
  'Not Attacked': 'not_attacked',
  'Clear': 'clear',
  'Green': 'green',
  'Amber': 'amber',
  'Red': 'red',
  'Negligible': 'negligible',
  'Diffuse': 'diffuse',
  'Concentrated': 'concentrated',
  'Automatic': 'automatic',
  'User': 'user',
  'Irrecoverable': 'irrecoverable',
  'Automatable': 'automatable'
}

// Labels for metric group cards (more specific than score labels)
const CATEGORY_GROUP_LABELS = {
  'base': 'cvss_calculator.base_score',
  'temporal': 'cvss_calculator.temporal_score',
  'environmental': 'cvss_calculator.environmental_score',
  'threat': 'cvss_calculator.threat_score',
  'environmental-base': 'cvss_calculator.environmental_base_score',
  'environmental-security-requirement': 'cvss_calculator.environmental_security_requirement_score',
  'supplemental': 'cvss_calculator.supplemental_score'
}

const CATEGORY_TOOLTIP_KEYS = {
  'base': 'cvss_calculator_tooltip.baseMetricGroup_Legend',
  'temporal': 'cvss_calculator_tooltip.temporalMetricGroup_Legend',
  'environmental': 'cvss_calculator_tooltip.environmentalMetricGroup_Legend'
}

function syncVectorInput() {
  vectorInput.value = vectorString.value
}

function getMetricI18nKey(name) {
  const key = NAME_TO_I18N[name]
  if (key && te(`cvss_calculator.${key}`)) {
    return `cvss_calculator.${key}`
  }
  return null
}

function getMetricLabel(name, shortName) {
  const i18nKey = getMetricI18nKey(name)
  if (i18nKey) return t(i18nKey)
  return `${name} (${shortName})`
}

function getValueLabel(name) {
  const key = VALUE_NAME_TO_I18N[name]
  if (key && te(`cvss_calculator.${key}`)) {
    return t(`cvss_calculator.${key}`)
  }
  return name
}

// Computed: vector string from instance
const vectorString = computed(() => {
  if (!cvssInstance.value) return ''
  return cvssInstance.value.toString()
})

// Computed: scores from instance
const scores = computed(() => {
  if (!cvssInstance.value) return null
  try {
    return cvssInstance.value.calculateScores()
  } catch {
    return null
  }
})

// Computed: score display items for header
// Uses the vector string to create a fresh instance (same as attribute display)
const scoreDisplay = computed(() => {
  return calculateScoreItems(vectorInput.value, t, te) || []
})

function getScoreTypeForCategory(categoryName) {
  if (categoryName === 'base') return 'base'
  if (categoryName === 'temporal' || categoryName === 'threat') return categoryName
  if (categoryName.startsWith('environmental')) return 'environmental'
  if (categoryName === 'supplemental') return 'supplemental'
  return categoryName
}

function mapComponents(components) {
  return components.map((comp) => {
    const tooltipMetricKey = `cvss_calculator_tooltip.${comp.shortName}_Heading`
    return {
      shortName: comp.shortName,
      label: getMetricLabel(comp.name, comp.shortName),
      component: comp,
      tooltipKey: te(tooltipMetricKey) ? tooltipMetricKey : null,
      values: comp.values
        .filter((v) => !v.hide)
        .map((v) => {
          const valTooltipKey = `cvss_calculator_tooltip.${comp.shortName}_${v.shortName}_Label`
          return {
            shortName: v.shortName,
            label: getValueLabel(v.name),
            value: v,
            tooltipKey: te(valTooltipKey) ? valTooltipKey : null
          }
        })
    }
  })
}

function getScoreForCategory(scores, categoryName) {
  if (!scores) return null
  switch (categoryName) {
    case 'base':
      return scores.base !== undefined ? scores.base : scores.overall
    case 'temporal':
      return scores.temporal
    case 'environmental':
    case 'environmental-base':
    case 'environmental-security-requirement':
      return scores.environmental
    case 'threat':
      return scores.threat
    case 'supplemental':
      return null
    default:
      return scores.overall
  }
}

// Computed: metric groups for display
const metricGroups = computed(() => {
  if (!cvssInstance.value) return []

  const registeredComponents = cvssInstance.value.getRegisteredComponents()
  const groups = []

  for (const [category, components] of registeredComponents) {
    const score = getScoreForCategory(scores.value, category.name)
    const scoreNum = score !== null && score !== undefined ? Number(score) : 0
    const severity = getSeverityRating(scoreNum)

    const scoreType = getScoreTypeForCategory(category.name)
    const labelKey = CATEGORY_GROUP_LABELS[category.name] || CATEGORY_GROUP_LABELS[scoreType]
    const tooltipKey = CATEGORY_TOOLTIP_KEYS[category.name] || null

    groups.push({
      name: category.name,
      label: labelKey ? t(labelKey) : category.name,
      tooltipKey: tooltipKey && te(tooltipKey) ? tooltipKey : null,
      severityClass: severity.name,
      metrics: mapComponents(components)
    })
  }

  return groups
})

function getSelectedValueIndex(metric) {
  if (!cvssInstance.value) return 0
  const currentValue = cvssInstance.value.getComponent(metric.component)
  if (!currentValue) return 0
  const idx = metric.values.findIndex((v) => v.shortName === currentValue.shortName)
  return idx >= 0 ? idx : 0
}

function onMetricToggle(metric, valueIndex) {
  if (!cvssInstance.value) return
  const val = metric.values[valueIndex]
  if (val) {
    cvssInstance.value.applyComponent(metric.component, val.value)
    triggerRef(cvssInstance)
    syncVectorInput()
  }
}

function onVectorInput(input) {
  const cleaned = stripParentheses(input?.trim())
  if (!cleaned) return

  const detected = detectVersion(cleaned)
  if (detected) {
    try {
      const newInstance = createInstance(detected, cleaned)
      // Temporarily suppress the version watcher by setting version first
      if (selectedVersion.value !== detected) {
        suppressVersionWatch = true
        selectedVersion.value = detected
      }
      cvssInstance.value = newInstance
      syncVectorInput()
    } catch {
      // invalid vector, ignore
    }
  } else {
    // Try applying to current instance
    try {
      cvssInstance.value.applyVector(cleaned)
      triggerRef(cvssInstance)
      syncVectorInput()
    } catch {
      // invalid vector, ignore
    }
  }
}

let suppressVersionWatch = false

// Watch version changes: clear metrics, create fresh instance
watch(selectedVersion, (newVersion) => {
  if (suppressVersionWatch) {
    suppressVersionWatch = false
    return
  }
  cvssInstance.value = createInstance(newVersion)
  syncVectorInput()
})

function openDialog() {
  const value = stripParentheses(props.modelValue)
  const detected = detectVersion(value)

  if (detected) {
    selectedVersion.value = detected
    nextTick(() => {
      try {
        cvssInstance.value = createInstance(detected, value)
      } catch {
        cvssInstance.value = createInstance(detected)
      }
      syncVectorInput()
    })
  } else {
    // No valid vector - use default version with fresh instance
    cvssInstance.value = createInstance(selectedVersion.value)
    syncVectorInput()
  }

  visible.value = true
}

function cancel() {
  emit('update:modelValue', vectorString.value)
  visible.value = false
}
</script>

<style scoped>
.calculator-header {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 1;
}

.metric-scroll {
  flex: 1;
  overflow-y: auto;
}

.vector-input {
  max-width: 800px;
  font-family: monospace;
}

.severity-box {
  border-radius: 4px;
  padding: 4px 8px;
  max-width: 280px;
  transition: background-color 250ms, color 250ms;
}

.severity-none {
  background-color: #53aa33;
}
.severity-na {
  background-color: #9e9e9e;
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

.metric-group-none {
  border-left: 4px solid #53aa33;
}
.metric-group-low {
  border-left: 4px solid #ffcb0d;
}
.metric-group-medium {
  border-left: 4px solid #f9a009;
}
.metric-group-high {
  border-left: 4px solid #df3d03;
}
.metric-group-critical {
  border-left: 4px solid red;
}
</style>
