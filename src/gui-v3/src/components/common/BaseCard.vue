<template>
  <div class="card-container d-flex align-center" :class="{ 'ga-3': multiSelectActive && showSelectionCheckbox }">
    <!-- Checkbox outside card to prevent triggering card click -->
    <div v-if="multiSelectActive && showSelectionCheckbox" class="checkbox-column" @click.stop>
      <v-checkbox
        v-model="internalSelected"
        density="compact"
        hide-details
        @update:model-value="emitSelectionChange"
      />
    </div>

    <!-- Card content -->
    <v-hover v-slot="{ isHovering, props: hoverProps }">
      <v-card
        v-bind="hoverProps"
        class="card-item mb-3 flex-grow-1"
        :class="cardClass"
        :elevation="isHovering ? 12 : 2"
        :color="cardColor"
        @click="handleCardClick"
      >
        <v-card-text>
          <!-- Content slot -->
          <div>
            <slot name="content" :is-hovering="isHovering" />
          </div>
          <!-- Actions slot (always visible if multiselect is not active) -->
          <div v-if="!multiSelectActive" class="d-flex ga-1 mt-2 justify-end">
            <slot name="actions" />
          </div>
        </v-card-text>
      </v-card>
    </v-hover>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  multiSelectActive: {
    type: Boolean,
    default: false
  },
  showSelectionCheckbox: {
    type: Boolean,
    default: true
  },
  checkboxLabel: {
    type: String,
    default: 'Select'
  },
  preselected: {
    type: Boolean,
    default: false
  },
  cardClass: {
    type: [String, Object],
    default: ''
  },
  cardColor: {
    type: String,
    default: undefined
  }
})

const emit = defineEmits(['card-click', 'selection-change'])

const internalSelected = ref(props.preselected)

// Watch preselected prop and sync with internalSelected
watch(
  () => props.preselected,
  (newValue) => {
    internalSelected.value = newValue
  }
)

const handleCardClick = () => {
  emit('card-click')
}

const emitSelectionChange = () => {
  emit('selection-change', internalSelected.value)
}
</script>

<style scoped>

.card-container {
  width: 100%;
  display: flex;
  flex-direction: row;
  align-items: center;
  flex: 1 1 0;
}

.checkbox-column {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 12px;
}

.card-item {
  transition: all 0.2s ease-in-out;
  cursor: pointer;
  width: 100%;
  flex: 1 1 0;
}
</style>

<style>
/* Card deletion/transition animations - non-scoped to apply to TransitionGroup children */
.card-list-move,
.card-list-enter-active,
.card-list-leave-active {
  transition: all 0.3s ease;
}

.card-list-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.card-list-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

.card-list-leave-active {
  position: absolute;
  width: 100%;
}
</style>
