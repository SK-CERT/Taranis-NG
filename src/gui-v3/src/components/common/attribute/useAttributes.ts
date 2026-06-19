import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/auth/permissions'
import { getReportItemData, holdLockReportItem, lockReportItem, unlockReportItem, updateReportItem } from '@/api/analyze'

type AttributeUser = {
    name?: string
} | null

type AttributeValue = {
    id?: number | string
    index?: string | number
    value?: unknown
    value_description?: string
    binary_mime_type?: unknown
    binary_size?: unknown
    binary_description?: unknown
    locked?: boolean
    last_updated?: unknown
    user?: AttributeUser
}

type AttributeGroup = {
    id?: number
    min_occurrence?: number
    max_occurrence?: number
    attribute?: {
        type?: string
        enum_values?: unknown[]
        enum_items?: unknown[]
        attribute_enums?: unknown[]
    } | null
}

type UseAttributesProps = {
    edit?: boolean
    modify?: boolean
    readOnly?: boolean
    reportItemId: number
    attributeGroup?: AttributeGroup
    values: AttributeValue[]
}

type EnumSelectedData = {
    index: number
    value: unknown
    value_description?: string
}

type ReportEventData = {
    report_item_id: number
    user_id?: number | string
    field_id?: number | string
    update?: unknown
    add?: unknown
    delete?: unknown
    attribute_id?: number
    attribute_group_item_id?: number
}

type ReportItemDataResponse = {
    data: {
        attribute_id?: number | string
        attribute_last_updated?: unknown
        attribute_user?: string
        attribute_value?: unknown
        attribute_value_description?: string
        value_description?: string
        binary_mime_type?: unknown
        binary_size?: unknown
        binary_description?: unknown
    }
}

type DataUpdatePayload = {
    update: true
    attribute_id?: number | string
    attribute_value?: unknown
    value_description?: string
}

/**
 * Composable for shared attribute editing logic.
 * Handles add/delete operations, locking, and API synchronization.
 */
export function useAttributes<T extends UseAttributesProps>(props: Readonly<T>) {
    const userStore = useUserStore()
    const keyTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

    const currentUserId = () => userStore.userId

    const canModify = computed(() => {
        if (props?.edit === false) {
            return AuthService.hasPermission(Permissions.ANALYZE_UPDATE) && props?.modify === true
        }
        return true
    })

    const addButtonVisible = computed(() => {
        return props.values.length < (props.attributeGroup?.max_occurrence || Infinity) && !props.readOnly && canModify.value
    })

    const delButtonVisible = computed(() => {
        // This is set by parent based on hover state, just for reference.
        return (props.attributeGroup?.min_occurrence || 0) < props.values.length
    })

    const add = async () => {
        if (props.edit === true) {
            try {
                const data = {
                    add: true,
                    report_item_id: props.reportItemId,
                    attribute_id: -1,
                    attribute_group_item_id: props.attributeGroup?.id
                }

                const updateResponse = await updateReportItem(props.reportItemId, data)
                const response = await getReportItemData(props.reportItemId, (updateResponse as { data: unknown }).data)
                const itemData = (response as ReportItemDataResponse).data

                props.values.push({
                    id: Number(itemData.attribute_id),
                    index: props.values.length,
                    value: '',
                    last_updated: itemData.attribute_last_updated,
                    user: { name: String(itemData.attribute_user ?? '') }
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

        props.values.forEach((val, idx) => {
            val.index = idx
        })
    }

    const del = async (index: number) => {
        if (!props.values[index]) {
            console.warn('Cannot delete attribute: values array or item is undefined')
            return
        }

        if (props.edit === true) {
            try {
                const data = {
                    delete: true,
                    report_item_id: props.reportItemId,
                    attribute_group_item_id: props.attributeGroup?.id,
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

        setTimeout(() => {
            props.values.forEach((val, idx) => {
                val.index = idx
            })
        }, 100)
    }

    const getLockedStyle = (fieldIndex: number): string => {
        const fieldValue = props.values[fieldIndex]
        if (!fieldValue) {
            return ''
        }
        return fieldValue.locked === true ? 'locked-style' : ''
    }

    const onFocus = async (fieldIndex: number) => {
        const fieldValue = props.values[fieldIndex]
        if (!fieldValue) {
            return
        }

        if (props.edit === true) {
            try {
                await lockReportItem(props.reportItemId, { field_id: fieldValue.id })
            } catch (error) {
                console.error('Failed to lock field:', error)
            }
        }
    }

    const onBlur = async (fieldIndex: number) => {
        const fieldValue = props.values[fieldIndex]
        if (!fieldValue) {
            return
        }

        if (props.edit === true) {
            await onEdit(fieldIndex)
            try {
                await unlockReportItem(props.reportItemId, { field_id: fieldValue.id })
            } catch (error) {
                console.error('Failed to unlock field:', error)
            }
        }
    }

    const onKeyUp = (fieldIndex: number) => {
        const fieldValue = props.values[fieldIndex]
        if (!fieldValue) {
            return
        }

        if (props.edit === true) {
            if (keyTimeout.value) {
                clearTimeout(keyTimeout.value)
            }
            keyTimeout.value = setTimeout(() => {
                holdLockReportItem(props.reportItemId, { field_id: fieldValue.id }).catch((error: unknown) => {
                    console.error('Failed to hold lock:', error)
                })
            }, 1000)
        }
    }

    const onEdit = async (fieldIndex: number) => {
        const value = props.values[fieldIndex]
        if (!value) {
            return
        }

        if (props.edit === true) {
            try {
                const dataUpdate: DataUpdatePayload = {
                    update: true
                }

                if (value.id !== undefined) {
                    dataUpdate.attribute_id = value.id
                }

                let attrValue = value.value
                const valueDescr = value.value_description

                if (props.attributeGroup?.attribute?.type === 'CPE' && typeof attrValue === 'string') {
                    attrValue = attrValue.replace(/\*/g, '%')
                } else if (props.attributeGroup?.attribute?.type === 'BOOLEAN') {
                    attrValue = value.value === true ? 'true' : 'false'
                }

                dataUpdate.attribute_value = attrValue
                if (valueDescr !== undefined) {
                    dataUpdate.value_description = valueDescr
                }

                const updateResponse = await updateReportItem(props.reportItemId, dataUpdate)
                const response = await getReportItemData(props.reportItemId, (updateResponse as { data: unknown }).data)
                const itemData = (response as ReportItemDataResponse).data

                value.last_updated = itemData.attribute_last_updated
                value.user = { name: String(itemData.attribute_user ?? '') }
            } catch (error) {
                console.error('Failed to save attribute value:', error)
            }
        }
    }

    const enumSelected = (data: EnumSelectedData) => {
        const value = props.values[data.index]
        if (!value) {
            return
        }

        value.value = data.value
        if (data.value_description !== undefined) {
            value.value_description = data.value_description
        } else {
            delete value.value_description
        }
        onEdit(data.index)
    }

    /**
     * Reorder values by moving the one at `from` to position `to`.
     *
     * The backend has no per-value ordering column (values of an attribute are
     * returned ordered by their id), so we cannot persist a reordered record
     * list. Instead we keep the records (and their ids/locks) fixed and rotate
     * their value payloads, then persist each changed slot via onEdit. Because
     * the records stay in id order, reloading from the backend preserves the new
     * visual order. In create mode (edit === false) the array order is the
     * submitted order, so this works there too.
     */
    const move = async (from: number, to: number) => {
        const last = props.values.length - 1
        if (from === to || from < 0 || to < 0 || from > last || to > last) {
            return
        }

        // Don't reorder across a slot that is locked by someone else.
        const lo = Math.min(from, to)
        const hi = Math.max(from, to)
        for (let index = lo; index <= hi; index++) {
            if (props.values[index]?.locked === true) {
                return
            }
        }

        type Payload = { value: unknown; value_description: string | undefined }
        const payloads: Payload[] = props.values.map((val) => ({
            value: val.value,
            value_description: val.value_description
        }))
        const moved = payloads.splice(from, 1)[0]
        if (!moved) {
            return
        }
        payloads.splice(to, 0, moved)

        const changed: number[] = []
        props.values.forEach((val, index) => {
            const payload = payloads[index]
            if (!payload) {
                return
            }
            if (val.value !== payload.value || val.value_description !== payload.value_description) {
                changed.push(index)
            }
            val.value = payload.value
            if (payload.value_description === undefined) {
                delete val.value_description
            } else {
                val.value_description = payload.value_description
            }
        })

        if (props.edit === true) {
            for (const index of changed) {
                await onEdit(index)
            }
        }
    }

    const moveUp = (index: number) => move(index, index - 1)
    const moveDown = (index: number) => move(index, index + 1)

    const reportItemLocked = (data: ReportEventData) => {
        if (props.edit === true && props.reportItemId === data.report_item_id) {
            if (data.user_id !== currentUserId()) {
                for (let index = 0; index < props.values.length; index++) {
                    const item = props.values[index]
                    if (item && String(item.id) === String(data.field_id)) {
                        item.locked = true
                        break
                    }
                }
            }
        }
    }

    const reportItemUnlocked = (data: ReportEventData) => {
        if (props.edit === true && props.reportItemId === data.report_item_id) {
            if (data.user_id !== currentUserId()) {
                for (let index = 0; index < props.values.length; index++) {
                    const item = props.values[index]
                    if (item && String(item.id) === String(data.field_id)) {
                        item.locked = false
                        break
                    }
                }
            }
        }
    }

    const reportItemUpdated = async (dataInfo: ReportEventData) => {
        if (props.edit === true && props.reportItemId === dataInfo.report_item_id) {
            if (dataInfo.user_id !== currentUserId()) {
                if (dataInfo.update !== undefined) {
                    const response = await getReportItemData(props.reportItemId, dataInfo)
                    const itemData = (response as ReportItemDataResponse).data

                    for (let index = 0; index < props.values.length; index++) {
                        const item = props.values[index]
                        if (!item || item.id !== Number(itemData.attribute_id)) {
                            continue
                        }
                        let value = itemData.attribute_value
                        if (props.attributeGroup?.attribute?.type === 'CPE' && typeof value === 'string') {
                            value = value.replace(/%/g, '*')
                        } else if (props.attributeGroup?.attribute?.type === 'BOOLEAN') {
                            value = value === 'true'
                        }

                        item.value = value
                        item.value_description = String(itemData.attribute_value_description ?? '')
                        item.last_updated = itemData.attribute_last_updated
                        item.user = { name: String(itemData.attribute_user ?? '') }
                        break
                    }
                } else if (dataInfo.add !== undefined) {
                    if (dataInfo.attribute_group_item_id === props.attributeGroup?.id) {
                        const response = await getReportItemData(props.reportItemId, dataInfo)
                        const itemData = (response as ReportItemDataResponse).data

                        props.values.push({
                            id: Number(itemData.attribute_id),
                            index: props.values.length,
                            value: itemData.attribute_value,
                            value_description: String(itemData.value_description ?? ''),
                            binary_mime_type: itemData.binary_mime_type,
                            binary_size: itemData.binary_size,
                            binary_description: itemData.binary_description,
                            last_updated: itemData.attribute_last_updated,
                            user: { name: String(itemData.attribute_user ?? '') }
                        })
                    }
                } else if (dataInfo.delete !== undefined) {
                    for (let index = 0; index < props.values.length; index++) {
                        const item = props.values[index]
                        if (item && item.id === dataInfo.attribute_id) {
                            props.values.splice(index, 1)
                            break
                        }
                    }
                }
            }
        }
    }

    const reportItemLockedEvent = (event: Event) => {
        reportItemLocked((event as CustomEvent<ReportEventData>).detail)
    }

    const reportItemUnlockedEvent = (event: Event) => {
        reportItemUnlocked((event as CustomEvent<ReportEventData>).detail)
    }

    const reportItemUpdatedEvent = (event: Event) => {
        reportItemUpdated((event as CustomEvent<ReportEventData>).detail)
    }

    onMounted(() => {
        window.addEventListener('report-item-locked', reportItemLockedEvent)
        window.addEventListener('report-item-unlocked', reportItemUnlockedEvent)
        window.addEventListener('report-item-updated', reportItemUpdatedEvent)
    })

    onUnmounted(() => {
        if (keyTimeout.value) {
            clearTimeout(keyTimeout.value)
        }
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
        enumSelected,
        move,
        moveUp,
        moveDown
    }
}
