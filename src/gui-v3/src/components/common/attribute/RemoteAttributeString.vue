<template>
  <attribute-item-layout
    :attribute-group="attributeGroup"
    :read-only="true"
    :editable="false"
  >
    <template #values>
      <div v-for="value in attributeGroup.attributes" :key="value.id">
        <attribute-value-layout
          :value="value"
          :read-only="true"
          :editable="false"
        >
          <template #display>
            <span class="text-sm text-gray-300">
              {{ value.value }}
            </span>
          </template>
        </attribute-value-layout>
      </div>
    </template>
  </attribute-item-layout>
</template>

<script setup>
import AttributeItemLayout from './AttributeItemLayout.vue'
import AttributeValueLayout from './AttributeValueLayout.vue'

const props = defineProps({
  attributeGroup: {
    type: Object,
    required: true
  },
  reportItemId: {
    type: Number,
    required: true
  }
})

// TODO: Phase 3 - Add remote-specific features:
// - Display source/origin information
// - Show when data came from API feed
// - Prevent editing with clear UI indication
// - Link to original source if available
</script>

<style scoped>
/* TODO: Add remote string styling */
</style>
