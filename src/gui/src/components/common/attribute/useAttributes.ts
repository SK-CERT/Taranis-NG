import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/stores/user'
import AuthService from '@/services/auth_service'
import Permissions from '@/services/auth/permissions'
import { getReportItemData, holdLockReportItem, lockReportItem, unlockReportItem, updateReportItem } from '@/api/analyze'
import { generateLinkKey } from '@/utils/linkReferences'

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
    // A value of an attached remote report item, listed among the report's own.
    remote?: boolean
    last_updated?: unknown
    user?: AttributeUser
    // Version of the stored value this copy is based on; sent back on save so the server can
    // refuse the write when somebody else changed the value in the meantime.
    version?: number
}

/** What the server reports when it refuses a write because the value moved on. */
type ConflictPayload = {
    attribute_id: number
    current_version: number
    current_value: unknown
    current_value_description?: string | null
    last_updated?: string | null
    user?: string | null
}

type AttributeGroup = {
    id?: number
    min_occurrence?: number
    max_occurrence?: number | null
    attribute?: {
        type?: string
        default_value?: string | null
        enum_values?: unknown[]
        enum_items?: unknown[]
        attribute_enums?: unknown[]
    } | null
}

type UseAttributesProps = {
    edit?: boolean
    modify?: boolean
    readOnly?: boolean
    // Null while a report item is being created (not yet persisted). The API calls that
    // consume it only run in edit mode (behind `props.edit === true`), where it is a real id.
    reportItemId: number | null
    attributeGroup?: AttributeGroup
    values: AttributeValue[]
    // A language variant of the report: the values are its translations. They are saved with
    // the language, locked per language, and never added, deleted or reordered.
    language?: string | null
}

type EnumSelectedData = {
    index: number
    value: unknown
    value_description?: string
}

type ReportEventData = {
    report_item_id: number
    user_id?: number | string
    language?: string | null
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
        attribute_version?: number
        value_description?: string
        binary_mime_type?: unknown
        binary_size?: unknown
        binary_description?: unknown
    }
}

type DataUpdatePayload = {
    update: true
    language?: string
    attribute_id?: number | string
    attribute_value?: unknown
    value_description?: string
    base_version?: number
}

/**
 * An attribute with max_occurrence 0 can hold no values at all: it is a label-only
 * field (a caption/separator in the report form), so it gets no inputs and no add
 * button. A missing max_occurrence means "unbounded", not zero.
 */
export function isLabelOnly(attributeGroup?: AttributeGroup | null): boolean {
    return (attributeGroup?.max_occurrence ?? Infinity) === 0
}

// Writes of attribute values this tab has under way - adds, saves, removals - across every
// attribute. A report reloaded meanwhile (a resync) would show what they have not stored yet:
// an added value twice, typed text as it was before.
const pendingWrites = ref(0)
// How many writes have begun: a reload read before one began is out of date, even if the write
// is done by the time the reload arrives.
let writesBegun = 0

/** Whether an attribute value is still being added, saved or removed. */
export function attributeWritesPending(): boolean {
    return pendingWrites.value > 0
}

/** A mark to tell, with {@link attributeWritesSince}, whether a write began after it. */
export function attributeWriteMark(): number {
    return writesBegun
}

/** Whether an attribute write began after ``mark`` (see {@link attributeWriteMark}). */
export function attributeWritesSince(mark: number): boolean {
    return writesBegun !== mark
}

async function tracked<R>(write: () => Promise<R>): Promise<R> {
    writesBegun++
    pendingWrites.value++
    try {
        return await write()
    } finally {
        pendingWrites.value--
    }
}

/**
 * Composable for shared attribute editing logic.
 * Handles add/delete operations, locking, and API synchronization.
 */
/** Tell the user a value did not reach the server; the field keeps their text, still unsaved. */
function notifySaveFailed(): void {
    window.dispatchEvent(new CustomEvent('notification', { detail: { type: 'error', loc: 'common.error_saving' } }))
}

// A stable identity per value row, for the v-for keys: the position (index) changes when rows are
// added, deleted or sorted, and a key built from it re-mounts the rows - destroying the input the
// user is typing in, whose blur then never saves it.
const rowKeys = new WeakMap<object, number>()
let nextRowKey = 0

export function rowKey(value: object): number {
    let key = rowKeys.get(value)
    if (key === undefined) {
        key = ++nextRowKey
        rowKeys.set(value, key)
    }
    return key
}

export function useAttributes<T extends UseAttributesProps>(props: Readonly<T>) {
    const userStore = useUserStore()
    const keyTimeout = ref<ReturnType<typeof setTimeout> | null>(null)

    // What a field held when it was last focused or saved, keyed by attribute id, plus the
    // field that currently has focus. Together they answer "did the user actually change
    // this?" — without that, merely clicking into a field and out again re-sends whatever
    // this tab has in memory, which silently overwrites a newer edit from somebody else
    // whenever the tab missed an update.
    const savedFingerprints = ref(new Map<string, string>())
    const focusedFieldId = ref<string | null>(null)

    const fingerprint = (value: AttributeValue): string => JSON.stringify([value.value ?? null, value.value_description ?? null])

    const isDirty = (value: AttributeValue): boolean => {
        const known = savedFingerprints.value.get(String(value.id))
        // Nothing recorded (e.g. blur without a preceding focus): fall back to saving.
        return known === undefined || known !== fingerprint(value)
    }

    /**
     * True while the user has this field focused with changes that are not saved yet.
     * Applying an incoming remote value to such a field would throw away what they are
     * in the middle of typing.
     */
    const hasUnsavedFocus = (value: AttributeValue): boolean => {
        return focusedFieldId.value === String(value.id) && isDirty(value)
    }

    const currentUserId = () => userStore.userId

    // A translated value is locked per language, so editing the Czech text does not block the
    // English one: `<attribute id>:<language>`.
    const lockId = (value: AttributeValue): number | string | undefined => (props.language ? `${value.id}:${props.language}` : value.id)

    // Events about another language's values (or about the source, in a language tab) are not ours.
    const ownLanguage = (data: ReportEventData): boolean => (data.language ?? null) === (props.language ?? null)

    // A value can reach the list more than once: from this tab's add, from another user's add
    // (announced to every copy of the attribute on the page), from a resync. Listed already,
    // it is not added again.
    const listed = (id: unknown): boolean =>
        props.values.some((item) => item.remote !== true && item.id !== undefined && Number(item.id) === Number(id))

    const canModify = computed(() => {
        if (props?.edit === false) {
            return AuthService.hasPermission(Permissions.ANALYZE_UPDATE) && props?.modify === true
        }
        return true
    })

    const addButtonVisible = computed(() => {
        return (
            !props.language && props.values.length < (props.attributeGroup?.max_occurrence ?? Infinity) && !props.readOnly && canModify.value
        )
    })

    const delButtonVisible = computed(() => {
        // This is set by parent based on hover state, just for reference.
        return (props.attributeGroup?.min_occurrence || 0) < props.values.length
    })

    const add = async () => {
        if (isLabelOnly(props.attributeGroup)) {
            return
        }

        if (props.edit === true) {
            try {
                const data = {
                    add: true,
                    report_item_id: props.reportItemId,
                    attribute_id: -1,
                    attribute_group_item_id: props.attributeGroup?.id
                }

                // Listed while still counted as pending, so no resync can come in between.
                await tracked(async () => {
                    const updateResponse = await updateReportItem(props.reportItemId, data)
                    const response = await getReportItemData(props.reportItemId, (updateResponse as { data: unknown }).data)
                    const itemData = (response as ReportItemDataResponse).data
                    if (listed(itemData.attribute_id)) {
                        return
                    }

                    props.values.push({
                        id: Number(itemData.attribute_id),
                        index: props.values.length,
                        // The server seeds a new value from the attribute's default_value, so take
                        // what it stored rather than blanking the field the user is about to see.
                        value: toLocalValue(itemData.attribute_value ?? ''),
                        // A new link comes with the citation key the server gave it.
                        value_description: String(itemData.attribute_value_description ?? ''),
                        last_updated: itemData.attribute_last_updated,
                        user: { name: String(itemData.attribute_user ?? '') },
                        version: Number(itemData.attribute_version ?? 1)
                    })
                })
            } catch (error) {
                console.error('Failed to add attribute value:', error)
                notifySaveFailed()
            }
        } else {
            // Nothing is persisted while a report item is being created, so apply the
            // attribute's default here instead - and give a new link its citation key, which
            // the server keeps when the report item is saved.
            const value: AttributeValue = {
                id: -1,
                index: props.values.length,
                value: toLocalValue(props.attributeGroup?.attribute?.default_value ?? ''),
                user: null
            }
            if (props.attributeGroup?.attribute?.type === 'LINK') {
                value.value_description = generateLinkKey(props.values.map((item) => String(item.value_description ?? '')))
            }
            props.values.push(value)
        }

        props.values.forEach((val, idx) => {
            val.index = idx
        })
    }

    /**
     * Seed empty values until the attribute holds its min_occurrence, so every required
     * row is ready to type into. min_occurrence 0 means no value is required: such an
     * attribute starts empty (with only the add button) and can be emptied again via the
     * delete button, which is why nothing may be seeded for it — in edit mode `add()`
     * persists the value server-side and would resurrect what the user just deleted.
     */
    const addInitialValues = async () => {
        if (props.readOnly || !canModify.value || props.language) {
            return
        }

        const required = props.attributeGroup?.min_occurrence ?? 0
        // add() appends one value, so re-read the length each round rather than
        // firing all the (awaited, API-backed) adds up front.
        while (props.values.length < required) {
            const before = props.values.length
            await add()
            if (props.values.length === before) {
                // add() failed (e.g. the API rejected it); stop instead of looping forever.
                break
            }
        }
    }

    const del = async (index: number) => {
        if (!props.values[index]) {
            console.warn('Cannot delete attribute: values array or item is undefined')
            return
        }

        if (props.edit === true) {
            try {
                const value = props.values[index]
                const data = {
                    delete: true,
                    report_item_id: props.reportItemId,
                    attribute_group_item_id: props.attributeGroup?.id,
                    attribute_id: value.id
                }

                await tracked(async () => {
                    await updateReportItem(props.reportItemId, data)
                    // Found again: the list may have changed while the server removed it.
                    const at = props.values.indexOf(value)
                    if (at !== -1) {
                        props.values.splice(at, 1)
                    }
                })
            } catch (error) {
                console.error('Failed to delete attribute value:', error)
            }
        } else {
            props.values.splice(index, 1)
        }

        renumber()
    }

    const renumber = (): void => {
        props.values.forEach((val, idx) => {
            val.index = idx
        })
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

        const key = String(fieldValue.id)
        focusedFieldId.value = key
        savedFingerprints.value.set(key, fingerprint(fieldValue))

        if (props.edit === true) {
            try {
                await lockReportItem(props.reportItemId, { field_id: lockId(fieldValue) })
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

        const key = String(fieldValue.id)
        const changed = isDirty(fieldValue)
        if (focusedFieldId.value === key) {
            focusedFieldId.value = null
        }

        if (props.edit === true) {
            // Persist only a real change, so leaving an untouched field alone never
            // pushes this tab's copy over what somebody else saved in the meantime.
            if (changed) {
                await onEdit(fieldIndex)
            }
            try {
                await unlockReportItem(props.reportItemId, { field_id: lockId(fieldValue) })
            } catch (error) {
                console.error('Failed to unlock field:', error)
            }
        }

        savedFingerprints.value.delete(key)
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
                holdLockReportItem(props.reportItemId, { field_id: lockId(fieldValue) }).catch((error: unknown) => {
                    console.error('Failed to hold lock:', error)
                })
            }, 1000)
        }
    }

    /** Convert a value as stored by the backend into the form this attribute type edits. */
    const toLocalValue = (raw: unknown): unknown => {
        if (props.attributeGroup?.attribute?.type === 'CPE' && typeof raw === 'string') {
            return raw.replace(/%/g, '*')
        }
        if (props.attributeGroup?.attribute?.type === 'BOOLEAN') {
            return raw === 'true'
        }
        return raw
    }

    const extractConflict = (error: unknown): ConflictPayload | null => {
        const response = (error as { response?: { status?: number; data?: { conflict?: ConflictPayload } } })?.response
        if (response?.status !== 409) {
            return null
        }
        return response.data?.conflict ?? null
    }

    const applyConflictValue = (value: AttributeValue, conflict: ConflictPayload): void => {
        value.value = toLocalValue(conflict.current_value)
        value.value_description = String(conflict.current_value_description ?? '')
        value.version = conflict.current_version
        value.last_updated = conflict.last_updated
        value.user = { name: String(conflict.user ?? '') }
        savedFingerprints.value.set(String(value.id), fingerprint(value))
    }

    /**
     * Hand a refused write over to the dialog that owns this form, which asks the user whose
     * version wins. Nothing was stored, so until they decide, the field keeps their text.
     */
    const announceConflict = (value: AttributeValue, conflict: ConflictPayload, mine: unknown): void => {
        // Found by the value itself, not by its position: rows may have been added, deleted or
        // sorted while the save was on its way.
        if (!props.values.includes(value)) {
            return
        }

        window.dispatchEvent(
            new CustomEvent('report-item-conflict', {
                detail: {
                    reportItemId: props.reportItemId,
                    attributeId: conflict.attribute_id,
                    mine,
                    theirs: toLocalValue(conflict.current_value),
                    user: conflict.user,
                    lastUpdated: conflict.last_updated,
                    keepMine: async () => {
                        // Rebase onto the stored version, then send the local value again.
                        value.version = conflict.current_version
                        await saveValue(value)
                    },
                    takeTheirs: () => {
                        applyConflictValue(value, conflict)
                    }
                }
            })
        )
    }

    // Saves of one value run one after the other: a save sends the version the previous one
    // returned, so two overlapping saves (a blur, then an inserted citation) would otherwise
    // refuse each other as conflicting edits.
    const pendingSaves = new Map<string, Promise<void>>()

    const onEdit = (fieldIndex: number): Promise<void> => {
        const value = props.values[fieldIndex]
        return value ? saveValue(value) : Promise.resolve()
    }

    const saveValue = (value: AttributeValue): Promise<void> => {
        if (props.edit !== true) {
            return Promise.resolve()
        }
        const key = String(value.id)
        // Counted from when it is queued, not only while it is sent.
        const save = tracked(() => (pendingSaves.get(key) ?? Promise.resolve()).then(() => persist(value)))
        pendingSaves.set(key, save)
        // Only bookkeeping: the caller gets `save` itself, failures included.
        save.finally(() => {
            if (pendingSaves.get(key) === save) {
                pendingSaves.delete(key)
            }
        }).catch(() => {})
        return save
    }

    const persist = async (value: AttributeValue) => {
        if (!props.values.includes(value)) {
            return
        }

        if (props.edit === true) {
            // What this save sends. The user may type on while it is on its way: only this text,
            // not theirs since, counts as saved when the answer comes - so the next blur sends the rest.
            const sent = fingerprint(value)
            const sentValue = value.value
            try {
                const dataUpdate: DataUpdatePayload = {
                    update: true
                }
                if (props.language) {
                    dataUpdate.language = props.language
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
                } else if (typeof attrValue === 'number') {
                    attrValue = String(attrValue)
                }

                dataUpdate.attribute_value = attrValue
                if (valueDescr !== undefined) {
                    dataUpdate.value_description = valueDescr
                }
                if (value.version !== undefined) {
                    // Let the server refuse the write if this is no longer the current value.
                    dataUpdate.base_version = value.version
                }

                const updateResponse = await updateReportItem(props.reportItemId, dataUpdate)
                const response = await getReportItemData(props.reportItemId, (updateResponse as { data: unknown }).data)
                const itemData = (response as ReportItemDataResponse).data

                value.last_updated = itemData.attribute_last_updated
                value.user = { name: String(itemData.attribute_user ?? '') }
                if (itemData.attribute_version !== undefined) {
                    value.version = Number(itemData.attribute_version)
                }
                // What the server now holds, so a later blur won't re-send it - but will send
                // whatever was typed after it.
                savedFingerprints.value.set(String(value.id), sent)
            } catch (error) {
                const conflict = extractConflict(error)
                if (conflict) {
                    announceConflict(value, conflict, sentValue)
                    return
                }
                console.error('Failed to save attribute value:', error)
                notifySaveFailed()
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
                    if (item && String(lockId(item)) === String(data.field_id)) {
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
                    if (item && String(lockId(item)) === String(data.field_id)) {
                        item.locked = false
                        break
                    }
                }
            }
        }
    }

    const reportItemUpdated = async (dataInfo: ReportEventData) => {
        if (props.edit === true && props.reportItemId === dataInfo.report_item_id && ownLanguage(dataInfo)) {
            if (dataInfo.user_id !== currentUserId()) {
                if (dataInfo.update !== undefined) {
                    // Attribute record ids are globally unique per report, so exactly one component
                    // on the page owns the edited value. Title/state events carry no attribute_id:
                    // Number(undefined) is NaN and matches nothing, so they never fetch here
                    // (NewReportItem.vue syncs titles on its own).
                    const editedId = Number(dataInfo.attribute_id)
                    if (!props.values.some((item) => item.id !== undefined && Number(item.id) === editedId)) {
                        return
                    }

                    const response = await getReportItemData(props.reportItemId, dataInfo)
                    const itemData = (response as ReportItemDataResponse).data

                    for (let index = 0; index < props.values.length; index++) {
                        const item = props.values[index]
                        if (!item || item.id !== Number(itemData.attribute_id)) {
                            continue
                        }
                        if (hasUnsavedFocus(item) || pendingSaves.has(String(item.id))) {
                            // The user is typing in this very field, or their save of it is still on
                            // its way - keep their text instead of overwriting it; the save sends it,
                            // and the server tells it if somebody else's came first.
                            break
                        }
                        item.value = toLocalValue(itemData.attribute_value)
                        item.value_description = String(itemData.attribute_value_description ?? '')
                        if (itemData.binary_description !== undefined) {
                            item.binary_description = itemData.binary_description
                        }
                        if (itemData.binary_mime_type !== undefined) {
                            item.binary_mime_type = itemData.binary_mime_type
                        }
                        if (itemData.binary_size !== undefined) {
                            item.binary_size = itemData.binary_size
                        }
                        item.last_updated = itemData.attribute_last_updated
                        item.user = { name: String(itemData.attribute_user ?? '') }
                        if (itemData.attribute_version !== undefined) {
                            item.version = Number(itemData.attribute_version)
                        }
                        if (savedFingerprints.value.has(String(item.id))) {
                            savedFingerprints.value.set(String(item.id), fingerprint(item))
                        }
                        break
                    }
                } else if (dataInfo.add !== undefined) {
                    if (dataInfo.attribute_group_item_id === props.attributeGroup?.id) {
                        const response = await getReportItemData(props.reportItemId, dataInfo)
                        const itemData = (response as ReportItemDataResponse).data
                        if (listed(itemData.attribute_id)) {
                            return
                        }

                        props.values.push({
                            id: Number(itemData.attribute_id),
                            index: props.values.length,
                            value: itemData.attribute_value,
                            value_description: String(itemData.attribute_value_description ?? itemData.value_description ?? ''),
                            binary_mime_type: itemData.binary_mime_type,
                            binary_size: itemData.binary_size,
                            binary_description: itemData.binary_description,
                            last_updated: itemData.attribute_last_updated,
                            user: { name: String(itemData.attribute_user ?? '') },
                            version: Number(itemData.attribute_version ?? 1)
                        })
                    }
                } else if (dataInfo.delete !== undefined) {
                    for (let index = 0; index < props.values.length; index++) {
                        const item = props.values[index]
                        if (item && item.id === dataInfo.attribute_id) {
                            props.values.splice(index, 1)
                            renumber()
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
        addInitialValues,
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
