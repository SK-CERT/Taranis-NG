<template>
  <v-row
    justify="center"
    class="attribute-value-layout pt-2"
    @mouseenter="itemHover = true"
    @mouseleave="itemHover = false"
  >
    <div class="col-left" style="position: relative">
      <span v-if="itemHover" class="icon-tooltip">{{ modifiedTooltip }}</span>
      <slot name="col_left" />
    </div>
    <div class="col-middle">
      <slot name="col_middle" />
    </div>
    <div class="col-right">
      <slot name="col_right">
        <v-btn
          v-if="delButtonVisible"
          variant="text"
          size="small"
          :title="t('report_item.tooltip.delete_value')"
          @click="handleDelete"
        >
          <v-icon>{{ ICONS.CLOSE }}</v-icon>
        </v-btn>
      </slot>
    </div>
  </v-row>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ICONS } from '@/config/ui-constants'

const props = defineProps({
  delButton: {
    type: Boolean,
    default: false
  },
  valIndex: {
    type: Number,
    required: true
  },
  occurrence: {
    type: Number,
    default: null
  },
  values: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['del-value'])

const { t } = useI18n()
const itemHover = ref(false)

const delButtonVisible = computed(() => {
  return itemHover.value && !(props.occurrence >= props.values.length)
})

const modifiedTooltip = computed(() => {
  const value = props.values[props.valIndex]
  if (value?.user !== null) {
    return `${value?.last_updated} ${value?.user?.name}`
  }
  return ''
})

const handleDelete = () => {
  emit('del-value')
}
</script>

<style scoped>
.attribute-value-layout {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.col-left {
  flex-shrink: 0;
  width: auto;
}

.col-middle {
  flex: 1;
  min-width: 200px;
}

.col-right {
  flex-shrink: 0;
  width: auto;
}

.icon-tooltip {
  position: absolute;
  left: 0;
  top: -24px;
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
}
</style>
