<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="datetime-value">
          <span v-if="values.length > 1" class="datetime-number text--disabled">{{ index + 1 }}.</span>
          {{ formatDateTime(values[index].value) }}
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
          <template #col_middle>
            <v-text-field
              v-model="values[index].value"
              density="compact"
              variant="outlined"
              type="datetime-local"
              :label="$t('attribute.value')"
              :class="getLockedStyle(index)"
              :disabled="values[index].locked || !canModify"
              @focus="onFocus(index)"
              @blur="onBlur(index)"
              @keyup="onKeyUp(index)"
            />
          </template>
        </AttributeValueLayout>
      </div>
    </template>
  </AttributeItemLayout>
</template>

<script setup>
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

const { canModify, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp } = useAttributes(props)

const formatDateTime = (value) => {
  if (!value) return '–'
  try {
    const date = new Date(value)
    if (isNaN(date.getTime())) return value
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch {
    return value
  }
}
</script>

<style scoped>
.datetime-number {
  margin-right: 8px;
  user-select: none;
  min-width: 24px;
  display: inline-block;
}

.datetime-value {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
