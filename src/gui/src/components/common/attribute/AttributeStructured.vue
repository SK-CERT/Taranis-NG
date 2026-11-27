<template>
    <AttributeItemLayout
        :add-button="addButtonVisible"
        :values="values"
        @add-value="add"
    >
        <template #content>
            <div
                v-for="(value, index) in values"
                :key="rowKey(value)"
                class="value-holder"
                :data-test="`structured-${type}`"
            >
                <!-- Read-only or remote: one line per value -->
                <div
                    v-if="readOnly || value.remote || !canModify"
                    class="structured-summary py-2"
                    data-test="structured-summary"
                >
                    <a
                        v-if="type === 'REFERENCE' && isHttpUrl(referenceUrl(value.value))"
                        :href="referenceUrl(value.value)"
                        target="_blank"
                        rel="noopener noreferrer"
                        >{{ summary(value.value) }}</a
                    >
                    <span v-else>{{ summary(value.value) }}</span>
                </div>

                <AttributeValueLayout
                    v-else
                    :del-button="true"
                    :occurrence="attributeGroup.min_occurrence"
                    :values="values"
                    :val-index="index"
                    @del-value="del(index)"
                >
                    <template #col_middle>
                        <!-- One lock for the whole value: moving between its fields is not leaving it. -->
                        <div
                            class="structured-form"
                            :class="getLockedStyle(index)"
                            @focusin="enter(index)"
                            @focusout="leave(index, $event)"
                        >
                            <!-- Affected product -->
                            <template v-if="type === 'AFFECTED'">
                                <v-row dense>
                                    <v-col
                                        cols="12"
                                        md="4"
                                    >
                                        <v-text-field
                                            :model-value="field(value, 'vendor')"
                                            :label="t('gna.field.vendor')"
                                            v-bind="fieldProps(value)"
                                            data-test="affected-vendor"
                                            @update:model-value="set(value, 'vendor', $event)"
                                        />
                                    </v-col>
                                    <v-col
                                        cols="12"
                                        md="4"
                                    >
                                        <v-text-field
                                            :model-value="field(value, 'product')"
                                            :label="t('gna.field.product')"
                                            v-bind="fieldProps(value)"
                                            data-test="affected-product"
                                            @update:model-value="set(value, 'product', $event)"
                                        />
                                    </v-col>
                                    <v-col
                                        cols="12"
                                        md="4"
                                    >
                                        <v-select
                                            :model-value="field(value, 'defaultStatus') || null"
                                            :items="statusItems"
                                            :label="t('gna.field.default_status')"
                                            clearable
                                            v-bind="fieldProps(value)"
                                            data-test="affected-default-status"
                                            @update:model-value="setAndSave(value, index, 'defaultStatus', $event)"
                                        />
                                    </v-col>
                                </v-row>
                                <div class="text-label-medium text-medium-emphasis mt-2 mb-3">{{ t('gna.field.versions') }}</div>
                                <template
                                    v-for="(version, versionIndex) in versions(value)"
                                    :key="versionIndex"
                                >
                                    <v-row
                                        dense
                                        align="center"
                                        data-test="affected-version"
                                    >
                                        <v-col
                                            cols="6"
                                            md="2"
                                        >
                                            <v-text-field
                                                :model-value="version.version"
                                                :label="t('gna.field.version')"
                                                v-bind="fieldProps(value)"
                                                @update:model-value="setVersion(value, versionIndex, 'version', $event)"
                                            />
                                        </v-col>
                                        <v-col
                                            cols="6"
                                            md="2"
                                        >
                                            <v-select
                                                :model-value="limitKind(version)"
                                                :items="limitItems"
                                                :label="t('gna.field.limit')"
                                                v-bind="fieldProps(value)"
                                                @update:model-value="setLimitKind(value, index, versionIndex, $event)"
                                            />
                                        </v-col>
                                        <v-col
                                            cols="6"
                                            md="2"
                                        >
                                            <v-text-field
                                                :model-value="limitKind(version) ? String(version[limitKind(version)] ?? '') : ''"
                                                :label="t('gna.field.limit_version')"
                                                :disabled="!limitKind(version) || value.locked === true"
                                                v-bind="fieldProps(value, true)"
                                                @update:model-value="setVersion(value, versionIndex, limitKind(version), $event)"
                                            />
                                        </v-col>
                                        <v-col
                                            cols="6"
                                            md="2"
                                        >
                                            <v-combobox
                                                :model-value="version.versionType ?? null"
                                                :items="[...VERSION_TYPES]"
                                                :label="t('gna.field.version_type')"
                                                v-bind="fieldProps(value)"
                                                @update:model-value="setVersion(value, versionIndex, 'versionType', $event)"
                                            />
                                        </v-col>
                                        <v-col
                                            cols="10"
                                            md="3"
                                        >
                                            <v-select
                                                :model-value="version.status ?? null"
                                                :items="statusItems"
                                                :label="t('gna.field.version_status')"
                                                v-bind="fieldProps(value)"
                                                @update:model-value="setVersionAndSave(value, index, versionIndex, 'status', $event)"
                                            />
                                        </v-col>
                                        <v-col cols="auto">
                                            <v-btn
                                                icon="mdi-close"
                                                variant="text"
                                                size="small"
                                                :title="t('gna.field.remove_version')"
                                                :disabled="value.locked === true"
                                                @click="removeVersion(value, index, versionIndex)"
                                            />
                                        </v-col>
                                    </v-row>
                                    <!-- A range's status may change within it (CVE Record Format "changes"). -->
                                    <div
                                        v-if="limitKind(version)"
                                        class="version-changes"
                                        data-test="affected-version-changes"
                                    >
                                        <div
                                            v-for="(change, changeIndex) in changes(version)"
                                            :key="changeIndex"
                                            class="version-change"
                                            data-test="affected-version-change"
                                        >
                                            <v-text-field
                                                :model-value="change.at ?? ''"
                                                :label="t('gna.field.change_at')"
                                                class="version-change-at"
                                                v-bind="fieldProps(value)"
                                                data-test="affected-change-at"
                                                @update:model-value="setChange(value, versionIndex, changeIndex, 'at', $event)"
                                            />
                                            <v-select
                                                :model-value="change.status ?? null"
                                                :items="statusItems"
                                                :label="t('gna.field.version_status')"
                                                class="version-change-status"
                                                v-bind="fieldProps(value)"
                                                data-test="affected-change-status"
                                                @update:model-value="
                                                    setChangeAndSave(value, index, versionIndex, changeIndex, 'status', $event)
                                                "
                                            />
                                            <v-btn
                                                icon="mdi-close"
                                                variant="text"
                                                size="small"
                                                :title="t('gna.field.remove_change')"
                                                :disabled="value.locked === true"
                                                @click="removeChange(value, index, versionIndex, changeIndex)"
                                            />
                                        </div>
                                        <v-btn
                                            variant="text"
                                            size="small"
                                            prepend-icon="mdi-plus"
                                            class="align-self-start"
                                            :disabled="value.locked === true"
                                            data-test="affected-add-change"
                                            @click="addChange(value, versionIndex)"
                                        >
                                            {{ t('gna.field.add_change') }}
                                        </v-btn>
                                    </div>
                                </template>
                                <v-btn
                                    variant="text"
                                    size="small"
                                    prepend-icon="mdi-plus"
                                    :disabled="value.locked === true"
                                    data-test="affected-add-version"
                                    @click="addVersion(value)"
                                >
                                    {{ t('gna.field.add_version') }}
                                </v-btn>
                                <v-expansion-panels
                                    variant="accordion"
                                    class="mt-1"
                                >
                                    <v-expansion-panel :title="t('gna.field.more')">
                                        <v-expansion-panel-text>
                                            <v-row dense>
                                                <v-col
                                                    v-for="name in AFFECTED_TEXTS"
                                                    :key="name"
                                                    cols="12"
                                                    md="6"
                                                >
                                                    <v-text-field
                                                        :model-value="field(value, name)"
                                                        :label="t(`gna.field.${snake(name)}`)"
                                                        v-bind="fieldProps(value)"
                                                        @update:model-value="set(value, name, $event)"
                                                    />
                                                </v-col>
                                                <v-col
                                                    v-for="name in AFFECTED_LISTS"
                                                    :key="name"
                                                    cols="12"
                                                    md="6"
                                                >
                                                    <v-combobox
                                                        :model-value="list(value, name)"
                                                        :label="t(`gna.field.${snake(name)}`)"
                                                        multiple
                                                        chips
                                                        closable-chips
                                                        v-bind="fieldProps(value)"
                                                        @update:model-value="setAndSave(value, index, name, $event)"
                                                    />
                                                </v-col>
                                            </v-row>
                                        </v-expansion-panel-text>
                                    </v-expansion-panel>
                                </v-expansion-panels>
                            </template>

                            <!-- Credit -->
                            <v-row
                                v-else-if="type === 'CREDIT'"
                                dense
                            >
                                <v-col
                                    cols="12"
                                    md="5"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'value')"
                                        :label="t('gna.field.credit_name')"
                                        v-bind="fieldProps(value)"
                                        data-test="credit-name"
                                        @update:model-value="set(value, 'value', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="3"
                                >
                                    <v-select
                                        :model-value="field(value, 'type') || null"
                                        :items="vocabulary"
                                        :label="t('gna.field.credit_role')"
                                        clearable
                                        v-bind="fieldProps(value)"
                                        data-test="credit-role"
                                        @update:model-value="setAndSave(value, index, 'type', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="4"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'user')"
                                        :label="t('gna.field.credit_user')"
                                        v-bind="fieldProps(value)"
                                        @update:model-value="set(value, 'user', $event)"
                                    />
                                </v-col>
                            </v-row>

                            <!-- Timeline event -->
                            <v-row
                                v-else-if="type === 'TIMELINE'"
                                dense
                            >
                                <v-col
                                    cols="12"
                                    md="4"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'time')"
                                        type="datetime-local"
                                        :label="t('gna.field.time')"
                                        v-bind="fieldProps(value)"
                                        data-test="timeline-time"
                                        @update:model-value="set(value, 'time', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="8"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'value')"
                                        :label="t('gna.field.event')"
                                        v-bind="fieldProps(value)"
                                        data-test="timeline-event"
                                        @update:model-value="set(value, 'value', $event)"
                                    />
                                </v-col>
                            </v-row>

                            <!-- Relationship to another record -->
                            <v-row
                                v-else-if="type === 'RELATIONSHIP'"
                                dense
                            >
                                <v-col
                                    cols="12"
                                    md="4"
                                >
                                    <v-select
                                        :model-value="field(value, 'type') || null"
                                        :items="vocabulary"
                                        :label="t('gna.field.relationship_type')"
                                        v-bind="fieldProps(value)"
                                        data-test="relationship-type"
                                        @update:model-value="setAndSave(value, index, 'type', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="5"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'destId')"
                                        :label="t('gna.field.dest_id')"
                                        v-bind="fieldProps(value)"
                                        data-test="relationship-dest"
                                        @update:model-value="set(value, 'destId', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="3"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'srcId')"
                                        :label="t('gna.field.src_id')"
                                        v-bind="fieldProps(value)"
                                        @update:model-value="set(value, 'srcId', $event)"
                                    />
                                </v-col>
                            </v-row>

                            <!-- Reference -->
                            <v-row
                                v-else-if="type === 'REFERENCE'"
                                dense
                            >
                                <v-col
                                    cols="12"
                                    md="5"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'url')"
                                        :label="t('gna.field.url')"
                                        :rules="[urlRule]"
                                        v-bind="fieldProps(value)"
                                        data-test="reference-url"
                                        @update:model-value="set(value, 'url', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="3"
                                >
                                    <v-text-field
                                        :model-value="field(value, 'name')"
                                        :label="t('gna.field.reference_name')"
                                        v-bind="fieldProps(value)"
                                        data-test="reference-name"
                                        @update:model-value="set(value, 'name', $event)"
                                    />
                                </v-col>
                                <v-col
                                    cols="12"
                                    md="4"
                                >
                                    <v-select
                                        :model-value="list(value, 'tags')"
                                        :items="vocabulary"
                                        :label="t('gna.field.tags')"
                                        multiple
                                        chips
                                        closable-chips
                                        v-bind="fieldProps(value)"
                                        data-test="reference-tags"
                                        @update:model-value="setAndSave(value, index, 'tags', $event)"
                                    />
                                </v-col>
                            </v-row>

                            <!-- A JSON fragment (other metric, taxonomy mapping) -->
                            <v-textarea
                                v-else
                                :model-value="jsonText(value)"
                                :label="t('gna.field.json')"
                                :error-messages="jsonError(value)"
                                class="structured-json"
                                rows="3"
                                auto-grow
                                v-bind="fieldProps(value)"
                                data-test="structured-json"
                                @update:model-value="setJson(value, $event)"
                            />
                        </div>
                    </template>
                </AttributeValueLayout>
            </div>
        </template>
    </AttributeItemLayout>
</template>

<script setup lang="ts">
    /**
     * Editor of a structured CVD Report field (see structuredValue.ts): each value is an object
     * edited field by field and stored as JSON. A value is locked once while the focus is inside
     * it and saved when the focus leaves it; a choice is saved as soon as it is picked.
     */
    import { computed, onMounted, reactive } from 'vue'
    import { useI18n } from 'vue-i18n'
    import AttributeItemLayout from './AttributeItemLayout.vue'
    import AttributeValueLayout from './AttributeValueLayout.vue'
    import { enumOptionLabel, enumOptionValue, enumOptionsOf, type EnumAttributeGroup } from './enumOptions'
    import { rowKey, useAttributes } from './useAttributes'
    import {
        VERSION_TYPES,
        parseStructured,
        referenceUrl,
        serializeStructured,
        structuredSummary,
        type StructuredData,
        type StructuredType
    } from './structuredValue'
    import { isHttpUrl } from '@/utils/linkReferences'

    type AttributeValueItem = {
        id?: number | string
        index?: string | number
        value: unknown
        remote?: boolean
        locked?: boolean
        [key: string]: unknown
    }

    type AttributeGroup = EnumAttributeGroup & {
        min_occurrence?: number
        attribute?: { type?: string; validator_parameter?: string | null; [key: string]: unknown } | null
    }

    // A status change within a range: from version ``at`` on, the status is ``status``.
    type Change = { at?: string; status?: string; [key: string]: unknown }
    type Version = {
        version?: string
        status?: string
        versionType?: string
        lessThan?: string
        lessThanOrEqual?: string
        changes?: Change[]
        [key: string]: unknown
    }
    type LimitKind = '' | 'lessThan' | 'lessThanOrEqual'

    const props = withDefaults(
        defineProps<{
            attributeGroup: AttributeGroup
            values: AttributeValueItem[]
            readOnly?: boolean
            edit?: boolean
            modify?: boolean
            reportItemId: number | null
        }>(),
        { readOnly: false, edit: false, modify: false }
    )

    const { t } = useI18n()
    const { canModify, addInitialValues, addButtonVisible, add, del, getLockedStyle, onFocus, onBlur, onKeyUp, onEdit } = useAttributes(props)

    const AFFECTED_TEXTS = ['collectionURL', 'packageName', 'packageURL', 'repo'] as const
    const AFFECTED_LISTS = ['cpes', 'platforms', 'modules', 'programFiles', 'programRoutines'] as const

    const type = computed(() => (props.attributeGroup.attribute?.type ?? 'JSON') as StructuredType)
    // The vocabulary the shipped attribute carries: credit roles, relationship types, reference tags, statuses.
    const vocabulary = computed(() =>
        enumOptionsOf(props.attributeGroup).map((option) => ({ title: enumOptionLabel(option), value: enumOptionValue(option) }))
    )
    const statusItems = computed(() =>
        (vocabulary.value.length ? vocabulary.value.map((item) => String(item.value)) : ['affected', 'unaffected', 'unknown']).map(
            (status) => ({
                title: t(`gna.status.${status}`),
                value: status
            })
        )
    )
    const limitItems = computed(() => [
        { title: t('gna.field.limit_none'), value: '' },
        { title: t('gna.field.limit_less_than'), value: 'lessThan' },
        { title: t('gna.field.limit_less_than_or_equal'), value: 'lessThanOrEqual' }
    ])

    // The i18n key of a CVE field name: collectionURL -> collection_url, programFiles -> program_files.
    const snake = (name: string): string => name.replace(/URL$/, 'Url').replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
    const summary = (raw: unknown): string => structuredSummary(type.value, raw)

    // The object each value holds while it is edited, re-read when the stored text changes from
    // elsewhere (another user's save arriving).
    const drafts = reactive(new Map<AttributeValueItem, { raw: unknown; data: StructuredData; json?: string }>())
    const draft = (value: AttributeValueItem) => {
        let entry = drafts.get(value)
        if (!entry || entry.raw !== value.value) {
            entry = { raw: value.value, data: parseStructured(value.value) }
            drafts.set(value, entry)
        }
        return entry
    }
    const write = (value: AttributeValueItem, data: StructuredData): void => {
        const serialized = serializeStructured(data)
        drafts.set(value, { raw: serialized, data })
        value.value = serialized
    }

    const field = (value: AttributeValueItem, name: string): string => {
        const item = draft(value).data[name]
        return item === undefined || item === null ? '' : String(item)
    }
    const list = (value: AttributeValueItem, name: string): string[] => {
        const item = draft(value).data[name]
        if (!Array.isArray(item)) return []
        // Program routines are objects ({name}) in the CVE Record Format; edited by their names.
        return item.map((entry) => (entry && typeof entry === 'object' ? String((entry as { name?: unknown }).name ?? '') : String(entry)))
    }
    const set = (value: AttributeValueItem, name: string, item: unknown): void => {
        const stored = name === 'programRoutines' && Array.isArray(item) ? item.map((routine) => ({ name: String(routine) })) : item
        write(value, { ...draft(value).data, [name]: stored ?? undefined })
    }
    const setAndSave = (value: AttributeValueItem, index: number, name: string, item: unknown): void => {
        set(value, name, item)
        void onEdit(index)
    }

    const versions = (value: AttributeValueItem): Version[] => {
        const item = draft(value).data['versions']
        return Array.isArray(item) ? (item as Version[]) : []
    }
    const writeVersions = (value: AttributeValueItem, next: Version[]): void => {
        write(value, { ...draft(value).data, versions: next })
    }
    const setVersion = (value: AttributeValueItem, versionIndex: number, name: string, item: unknown): void => {
        writeVersions(
            value,
            versions(value).map((version, position) => (position === versionIndex ? { ...version, [name]: item ?? undefined } : version))
        )
    }
    const setVersionAndSave = (value: AttributeValueItem, index: number, versionIndex: number, name: string, item: unknown): void => {
        setVersion(value, versionIndex, name, item)
        void onEdit(index)
    }
    const limitKind = (version: Version): LimitKind =>
        version.lessThanOrEqual !== undefined ? 'lessThanOrEqual' : version.lessThan !== undefined ? 'lessThan' : ''
    const setLimitKind = (value: AttributeValueItem, index: number, versionIndex: number, kind: LimitKind): void => {
        writeVersions(
            value,
            versions(value).map((version, position) => {
                if (position !== versionIndex) return version
                const limit = version.lessThan ?? version.lessThanOrEqual ?? ''
                const { lessThan: _lessThan, lessThanOrEqual: _lessThanOrEqual, ...rest } = version
                if (!kind) {
                    // A single version has no status changes within it.
                    const { changes: _changes, ...single } = rest
                    return single
                }
                // A range needs a numbering scheme (CVE Record Format): semver unless one is chosen.
                return { ...rest, [kind]: limit, versionType: rest.versionType || 'semver' }
            })
        )
        void onEdit(index)
    }
    const addVersion = (value: AttributeValueItem): void => {
        writeVersions(value, [...versions(value), { version: '', status: 'affected' }])
    }
    const removeVersion = (value: AttributeValueItem, index: number, versionIndex: number): void => {
        writeVersions(
            value,
            versions(value).filter((_version, position) => position !== versionIndex)
        )
        void onEdit(index)
    }

    const changes = (version: Version | undefined): Change[] => {
        const list = version?.changes
        return Array.isArray(list) ? list : []
    }
    const writeChanges = (value: AttributeValueItem, versionIndex: number, next: Change[]): void => {
        setVersion(value, versionIndex, 'changes', next)
    }
    const setChange = (value: AttributeValueItem, versionIndex: number, changeIndex: number, name: string, item: unknown): void => {
        writeChanges(
            value,
            versionIndex,
            changes(versions(value)[versionIndex]).map((change, position) =>
                position === changeIndex ? { ...change, [name]: item ?? undefined } : change
            )
        )
    }
    const setChangeAndSave = (
        value: AttributeValueItem,
        index: number,
        versionIndex: number,
        changeIndex: number,
        name: string,
        item: unknown
    ): void => {
        setChange(value, versionIndex, changeIndex, name, item)
        void onEdit(index)
    }
    // Most often a fix: from some version on, the range is no longer affected.
    const addChange = (value: AttributeValueItem, versionIndex: number): void => {
        writeChanges(value, versionIndex, [...changes(versions(value)[versionIndex]), { at: '', status: 'unaffected' }])
    }
    const removeChange = (value: AttributeValueItem, index: number, versionIndex: number, changeIndex: number): void => {
        writeChanges(
            value,
            versionIndex,
            changes(versions(value)[versionIndex]).filter((_change, position) => position !== changeIndex)
        )
        void onEdit(index)
    }

    // A JSON field keeps what is typed until it parses.
    const jsonText = (value: AttributeValueItem): string => {
        const entry = draft(value)
        return entry.json ?? (Object.keys(entry.data).length ? JSON.stringify(entry.data, null, 2) : '')
    }
    const jsonError = (value: AttributeValueItem): string[] => {
        const typed = draft(value).json
        if (typed === undefined || !typed.trim()) return []
        try {
            const parsed: unknown = JSON.parse(typed)
            return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? [] : [t('gna.field.json_object')]
        } catch {
            return [t('gna.field.json_invalid')]
        }
    }
    const setJson = (value: AttributeValueItem, typed: string): void => {
        const entry = draft(value)
        entry.json = typed
        if (!typed.trim()) {
            value.value = ''
            entry.raw = ''
            entry.data = {}
            return
        }
        try {
            const parsed: unknown = JSON.parse(typed)
            if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                const serialized = serializeStructured(parsed as StructuredData)
                drafts.set(value, { raw: serialized, data: parsed as StructuredData, json: typed })
                value.value = serialized
            }
        } catch {
            // Kept as typed, not stored, until it is valid JSON.
        }
    }

    const urlRule = (url: string): boolean | string => !url || isHttpUrl(url) || t('enter.link_invalid')

    const fieldProps = (value: AttributeValueItem, keepDisabled = false) => ({
        density: 'compact' as const,
        variant: 'outlined' as const,
        hideDetails: 'auto' as const,
        ...(keepDisabled ? {} : { disabled: value.locked === true || !canModify.value }),
        onKeyup: () => onKeyUp(props.values.indexOf(value))
    })

    // The focus moving between the fields of one value does not leave it.
    let focused: number | null = null
    const enter = (index: number): void => {
        if (focused === index) return
        focused = index
        void onFocus(index)
    }
    const leave = (index: number, event: FocusEvent): void => {
        const next = event.relatedTarget as Node | null
        if (next && (event.currentTarget as HTMLElement | null)?.contains(next)) return
        focused = null
        void onBlur(index)
    }

    onMounted(addInitialValues)

    defineExpose({ write, draft })
</script>

<style scoped>
    .value-holder {
        width: 100%;
        margin-bottom: 6px;
    }

    .structured-form {
        width: 100%;
        padding: 4px 0;
    }

    .structured-summary {
        word-break: break-word;
    }

    /* A range's status changes, under it and indented. */
    .version-changes {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding-left: 24px;
        margin: 4px 0 8px;
    }

    .version-change {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .version-change-at,
    .version-change-status {
        flex: 0 1 220px;
    }

    .structured-summary a {
        color: rgb(var(--v-theme-primary));
    }

    .structured-json :deep(textarea) {
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
