<template>
  <AttributeItemLayout :add-button="addButtonVisible" :values="values" @add-value="add">
    <template #content>
      <div v-for="(value, index) in values" :key="`${value.index}-${index}`" class="value-holder">
        <!-- Read-only or remote -->
        <span v-if="readOnly || values[index].remote" class="boolean-value">
          <v-icon :color="values[index].value ? 'success' : 'error'" size="small">
            {{ values[index].value ? ICONS.CHECK_CIRCLE : ICONS.CLOSE }}
          </v-icon>
          {{ values[index].value ? $t('common.yes') : $t('common.no') }}
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
            <v-switch
              v-model="values[index].value"
              :label="values[index].value ? $t('common.yes') : $t('common.no')"
              density="compact"
              :disabled="values[index].locked || !canModify"
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
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'
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
</script>

<style scoped>
.boolean-value {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.value-holder {
  width: 100%;
  margin-bottom: 4px;
}
</style>
