<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="text-value">
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
            <v-textarea
              v-model="values[index].value"
              density="compact"
              variant="outlined"
              :label="$t('attribute.value')"
              rows="3"
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

const { canModify, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp } = useAttributes(props)

onMounted(() => {
  if (props.values?.length === 0 && canModify.value && !props.readOnly) {
    add()
  }
})
</script>

<style scoped>
.text-value {
  display: block;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
