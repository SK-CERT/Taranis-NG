<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="date-value">
          {{ formatDate(values[index].value) }}
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
              type="date"
              density="compact"
              variant="outlined"
              :label="$t('attribute.value')"
              :disabled="values[index].locked || !canModify"
              style="max-width: 200px"
              @focus="onFocus(index)"
              @blur="onBlur(index)"
              @update:model-value="onEdit(index)"
            />
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

onMounted(() => {
  if (props.values?.length === 0 && canModify.value && !props.readOnly) {
    add()
  }
})

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString()
  } catch (e) {
    return dateStr
  }
}
</script>

<style scoped>
.date-value {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
