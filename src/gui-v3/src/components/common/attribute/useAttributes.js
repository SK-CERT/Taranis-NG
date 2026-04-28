import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useUserStore } from '@/stores/user'
import Permissions from '@/services/auth/permissions'
import { getReportItemData, holdLockReportItem, lockReportItem, unlockReportItem, updateReportItem } from '@/api/analyze'

/**
 * Composable for shared attribute editing logic
 * Handles add/delete operations, locking, and API synchronization
 *
 * @param {Object} props - Component props (must be reactive)
 * @returns {Object} Methods and computed properties for attribute handling
 */
export function useAttributes(props) {
  const authStore = useAuthStore()
  const userStore = useUserStore()
  const keyTimeout = ref(null)

  const currentUserId = () => userStore.userId

  // Computed properties
  const canModify = computed(() => {
    if (props?.edit === false) {
      return authStore.checkPermission(Permissions.ANALYZE_UPDATE) && props?.modify === true
    }
    return true
  })

  const addButtonVisible = computed(() => {
    return (props.values?.length || 0) < (props.attributeGroup?.max_occurrence || Infinity) && !props.readOnly && canModify.value
  })

  const delButtonVisible = computed(() => {
    // This is set by parent based on hover state, just for reference
    return (props.attributeGroup?.min_occurrence || 0) < (props.values?.length || 0)
  })

  // Methods

  /**
   * Add a new attribute value
   */
  const add = async () => {
    if (!props.values) {
      console.warn('Cannot add attribute: values array is undefined')
      return
    }

    if (props.edit === true) {
      try {
        const data = {
          add: true,
          report_item_id: props.reportItemId,
          attribute_id: -1,
          attribute_group_item_id: props.attributeGroup.id
        }

        const updateResponse = await updateReportItem(props.reportItemId, data)
        const response = await getReportItemData(props.reportItemId, updateResponse.data)
        const itemData = response.data

        props.values.push({
          id: itemData.attribute_id,
          index: props.values.length,
          value: '',
          last_updated: itemData.attribute_last_updated,
          user: { name: itemData.attribute_user }
        })
      } catch (error) {
        console.error('Failed to add attribute value:', error)
      }
    } else {
      props.values.push({
        id: -1,
        index: props.values.length,
        value: '',
        user: null
      })
    }

    // Re-index values
    props.values.forEach((val, idx) => {
      val.index = idx
    })
  }

  /**
   * Delete an attribute value
   */
  const del = async (index) => {
    if (!props.values || !props.values[index]) {
      console.warn('Cannot delete attribute: values array or item is undefined')
      return
    }

    if (props.edit === true) {
      try {
        const data = {
          delete: true,
          report_item_id: props.reportItemId,
          attribute_group_item_id: props.attributeGroup.id,
          attribute_id: props.values[index].id
        }

        await updateReportItem(props.reportItemId, data)
        props.values.splice(index, 1)
      } catch (error) {
        console.error('Failed to delete attribute value:', error)
      }
    } else {
      props.values.splice(index, 1)
    }

    // Re-index values
    setTimeout(() => {
      if (props.values) {
        props.values.forEach((val, idx) => {
          val.index = idx
        })
      }
    }, 100)
  }

  /**
   * Get locked style for a field
   */
  const getLockedStyle = (fieldIndex) => {
    if (!props.values || !props.values[fieldIndex]) {
      return ''
    }
    return props.values[fieldIndex].locked === true ? 'locked-style' : ''
  }

  /**
   * Handle field focus - lock the field during editing
   */
  const onFocus = async (fieldIndex) => {
    if (!props.values || !props.values[fieldIndex]) {
      return
    }

    if (props.edit === true) {
      try {
        await lockReportItem(props.reportItemId, { field_id: props.values[fieldIndex].id })
      } catch (error) {
        console.error('Failed to lock field:', error)
      }
    }
  }

  /**
   * Handle field blur - save changes and unlock
   */
  const onBlur = async (fieldIndex) => {
    if (!props.values || !props.values[fieldIndex]) {
      return
    }

    if (props.edit === true) {
      await onEdit(fieldIndex)
      try {
        await unlockReportItem(props.reportItemId, { field_id: props.values[fieldIndex].id })
      } catch (error) {
        console.error('Failed to unlock field:', error)
      }
    }
  }

  /**
   * Handle key up - hold lock with periodic heartbeat
   */
  const onKeyUp = (fieldIndex) => {
    if (!props.values || !props.values[fieldIndex]) {
      return
    }

    if (props.edit === true) {
      clearTimeout(keyTimeout.value)
      keyTimeout.value = setTimeout(() => {
        holdLockReportItem(props.reportItemId, { field_id: props.values[fieldIndex].id }).catch((error) => {
          console.error('Failed to hold lock:', error)
        })
      }, 1000)
    }
  }

  /**
   * Save attribute edit to backend
   */
  const onEdit = async (fieldIndex) => {
    if (!props.values || !props.values[fieldIndex]) {
      return
    }

    if (props.edit === true) {
      try {
        const value = props.values[fieldIndex]
        const dataUpdate = {
          update: true,
          attribute_id: value.id
        }

        let attrValue = value.value
        const valueDescr = value.value_description

        // Type-specific transformations
        if (props.attributeGroup.attribute.type === 'CPE') {
          attrValue = attrValue.replace(/\*/g, '%')
        } else if (props.attributeGroup.attribute.type === 'BOOLEAN') {
          attrValue = value === true ? 'true' : 'false'
        }

        dataUpdate.attribute_value = attrValue
        dataUpdate.value_description = valueDescr

        const updateResponse = await updateReportItem(props.reportItemId, dataUpdate)
        const response = await getReportItemData(props.reportItemId, updateResponse.data)
        const itemData = response.data

        props.values[fieldIndex].last_updated = itemData.attribute_last_updated
        props.values[fieldIndex].user = { name: itemData.attribute_user }
      } catch (error) {
        console.error('Failed to save attribute value:', error)
      }
    }
  }

  /**
   * Handle enum selection for enum attributes
   */
  const enumSelected = (data) => {
    if (!props.values || !props.values[data.index]) {
      return
    }

    props.values[data.index].value = data.value
    props.values[data.index].value_description = data.value_description
    onEdit(data.index)
  }

  const reportItemLocked = (data) => {
    if (props.edit === true && props.reportItemId === data.report_item_id) {
      if (data.user_id !== currentUserId()) {
        for (let index = 0; index < props.values.length; index++) {
          if (props.values[index].id == data.field_id) {
            props.values[index].locked = true
            break
          }
        }
      }
    }
  }

  const reportItemUnlocked = (data) => {
    if (props.edit === true && props.reportItemId === data.report_item_id) {
      if (data.user_id !== currentUserId()) {
        for (let index = 0; index < props.values.length; index++) {
          if (props.values[index].id == data.field_id) {
            props.values[index].locked = false
            break
          }
        }
      }
    }
  }

  const reportItemUpdated = async (dataInfo) => {
    if (props.edit === true && props.reportItemId === dataInfo.report_item_id) {
      if (dataInfo.user_id !== currentUserId()) {
        if (dataInfo.update !== undefined) {
          const response = await getReportItemData(props.reportItemId, dataInfo)
          const itemData = response.data

          for (let index = 0; index < props.values.length; index++) {
            if (props.values[index].id == itemData.attribute_id) {
              let value = itemData.attribute_value
              if (props.attributeGroup.attribute.type === 'CPE') {
                value = value.replace(/%/g, '*')
              } else if (props.attributeGroup.attribute.type === 'BOOLEAN') {
                value = value === 'true'
              }

              props.values[index].value = value
              props.values[index].value_description = itemData.attribute_value_description
              props.values[index].last_updated = itemData.attribute_last_updated
              props.values[index].user = { name: itemData.attribute_user }
              break
            }
          }
        } else if (dataInfo.add !== undefined) {
          if (dataInfo.attribute_group_item_id === props.attributeGroup.id) {
            const response = await getReportItemData(props.reportItemId, dataInfo)
            const itemData = response.data

            props.values.push({
              id: itemData.attribute_id,
              index: props.values.length,
              value: itemData.attribute_value,
              value_description: itemData.value_description,
              binary_mime_type: itemData.binary_mime_type,
              binary_size: itemData.binary_size,
              binary_description: itemData.binary_description,
              last_updated: itemData.attribute_last_updated,
              user: { name: itemData.attribute_user }
            })
          }
        } else if (dataInfo.delete !== undefined) {
          for (let index = 0; index < props.values.length; index++) {
            if (props.values[index].id === dataInfo.attribute_id) {
              props.values.splice(index, 1)
              break
            }
          }
        }
      }
    }
  }

  const reportItemLockedEvent = (event) => {
    reportItemLocked(event.detail)
  }

  const reportItemUnlockedEvent = (event) => {
    reportItemUnlocked(event.detail)
  }

  const reportItemUpdatedEvent = (event) => {
    reportItemUpdated(event.detail)
  }

  onMounted(() => {
    window.addEventListener('report-item-locked', reportItemLockedEvent)
    window.addEventListener('report-item-unlocked', reportItemUnlockedEvent)
    window.addEventListener('report-item-updated', reportItemUpdatedEvent)
  })

  // Cleanup
  onUnmounted(() => {
    clearTimeout(keyTimeout.value)
    window.removeEventListener('report-item-locked', reportItemLockedEvent)
    window.removeEventListener('report-item-unlocked', reportItemUnlockedEvent)
    window.removeEventListener('report-item-updated', reportItemUpdatedEvent)
  })

  return {
    canModify,
    addButtonVisible,
    delButtonVisible,
    add,
    del,
    getLockedStyle,
    onFocus,
    onBlur,
    onKeyUp,
    onEdit,
    enumSelected
  }
}
