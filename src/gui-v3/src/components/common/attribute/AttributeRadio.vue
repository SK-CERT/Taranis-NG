<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="radio-value">
          {{ values[index].value }}
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
            <v-radio-group
              v-model="values[index].value"
              inline
              density="compact"
              class="radio-single-row"
              :disabled="values[index].locked || !canModify"
              @focus="onFocus(index)"
              @blur="onBlur(index)"
              @update:model-value="onEdit(index)"
            >
              <v-radio
                v-for="(option, optionIndex) in radioOptions"
                :key="`${index}-${optionIndex}`"
                :label="getOptionLabel(option)"
                :value="getOptionValue(option)"
              />
            </v-radio-group>
          </template>
        </AttributeValueLayout>
      </div>
    </template>
  </AttributeItemLayout>
</template>

<script setup>
import { computed, onMounted } from 'vue'
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

const { canModify, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onEdit } = useAttributes(props)

const radioOptions = computed(() => {
  return (
    props.attributeGroup?.attribute?.attribute_enums ||
    props.attributeGroup?.attribute?.enum_items ||
    props.attributeGroup?.attribute?.enum_values ||
    []
  )
})

const getOptionLabel = (option) => {
  if (option && typeof option === 'object') {
    return option.value ?? option.title ?? option.name ?? String(option.id ?? '')
  }
  return String(option ?? '')
}

const getOptionValue = (option) => {
  if (option && typeof option === 'object') {
    return option.value ?? option.id ?? option.title ?? option.name
  }
  return option
}

onMounted(() => {
  if (props.values?.length === 0 && canModify.value && !props.readOnly) {
    add()
  }
})
</script>

<style scoped>
.radio-value {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}

.radio-single-row :deep(.v-selection-control-group) {
  flex-wrap: nowrap;
  gap: 12px;
}
</style>
