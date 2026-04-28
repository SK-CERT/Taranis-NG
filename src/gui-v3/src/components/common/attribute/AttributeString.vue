<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="numbered-string-value">
          <span v-if="values.length > 1" class="string-number text--disabled">{{ index + 1 }}.</span>
          <span class="string-content">{{ values[index].value }}</span>
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
            <span v-if="values.length > 1" class="string-number text--disabled">{{ index + 1 }}.</span>
          </template>
          <template #col_middle>
            <v-text-field
              v-model="values[index].value"
              density="compact"
              variant="outlined"
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
</script>

<style scoped>
.string-number {
  margin-right: 8px;
  user-select: none;
  min-width: 24px;
  display: inline-block;
}

.numbered-string-value {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.string-content {
  flex: 1;
  word-break: break-word;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
