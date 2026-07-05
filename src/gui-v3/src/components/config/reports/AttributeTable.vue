<template>
    <EditableEntityTable
        v-model="items"
        :title="t('attribute.attributes')"
        :headers="headers"
        :default-item="defaultItem"
        :add-title="t('attribute.add_attribute')"
        :edit-title="t('attribute.edit_attribute')"
        :disabled="disabled"
        reorderable
    >
        <template #form="{ item }">
            <v-select
                :model-value="item.attribute_id >= 0 ? item.attribute_id : null"
                :items="attributeTemplates"
                item-title="name"
                item-value="id"
                :label="t('attribute.attribute')"
                variant="outlined"
                density="comfortable"
                class="mb-3"
                :rules="[(v) => (v != null && v >= 0) || t('error.required')]"
                @update:model-value="(id: number) => selectAttribute(item, id)"
            />
            <v-text-field
                v-model="item.title"
                :label="t('reports.types.name')"
                variant="outlined"
                density="comfortable"
                class="mb-3"
            />
            <v-text-field
                v-model="item.description"
                :label="t('reports.types.description')"
                variant="outlined"
                density="comfortable"
                class="mb-3"
            />
            <v-row>
                <v-col cols="6">
                    <v-text-field
                        v-model.number="item.min_occurrence"
                        :label="t('attribute.min_occurrence')"
                        type="number"
                        variant="outlined"
                        density="comfortable"
                    />
                </v-col>
                <v-col cols="6">
                    <v-text-field
                        v-model.number="item.max_occurrence"
                        :label="t('attribute.max_occurrence')"
                        type="number"
                        variant="outlined"
                        density="comfortable"
                    />
                </v-col>
            </v-row>
            <v-select
                v-if="showAI"
                v-model="item.ai_provider_id"
                :items="aiProviderOptions"
                item-title="name"
                item-value="id"
                :label="t('attribute.ai_provider')"
                variant="outlined"
                density="comfortable"
                class="mb-3"
            />
            <v-textarea
                v-if="item.ai_provider_id != null"
                v-model="item.ai_prompt"
                :label="t('attribute.ai_prompt')"
                variant="outlined"
                density="comfortable"
                rows="3"
                clearable
            />
        </template>
    </EditableEntityTable>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import EditableEntityTable from '@/components/common/EditableEntityTable.vue'

    export type AttributeGroupItem = {
        id: number
        index: number
        attribute_id: number
        attribute_name: string
        title: string
        description: string
        min_occurrence: number
        max_occurrence: number
        ai_provider_id: number | null
        ai_prompt: string
        [key: string]: unknown
    }

    type AttributeTemplate = {
        id: number
        name: string
        [key: string]: unknown
    }

    type AiProvider = {
        id: number
        name: string
        [key: string]: unknown
    }

    const props = withDefaults(
        defineProps<{
            attributeTemplates?: AttributeTemplate[]
            aiProviders?: AiProvider[]
            disabled?: boolean
        }>(),
        {
            attributeTemplates: () => [],
            aiProviders: () => [],
            disabled: false
        }
    )

    // Two-way bound list of attribute group items owned by the parent group.
    const items = defineModel<AttributeGroupItem[]>({ required: true })

    const { t } = useI18n()

    const defaultItem = (): AttributeGroupItem => ({
        id: -1,
        index: 0,
        attribute_id: -1,
        attribute_name: '',
        title: '',
        description: '',
        min_occurrence: 0,
        max_occurrence: 1,
        ai_provider_id: null,
        ai_prompt: ''
    })

    const headers = [
        { title: t('attribute.type'), key: 'attribute_name', sortable: false },
        { title: t('reports.types.name'), key: 'title', sortable: false },
        { title: t('reports.types.description'), key: 'description', sortable: false },
        { title: t('attribute.min_occurrence'), key: 'min_occurrence', sortable: false },
        { title: t('attribute.max_occurrence'), key: 'max_occurrence', sortable: false },
        { title: t('settings.actions'), key: 'actions', align: 'end' as const, sortable: false }
    ]

    const showAI = computed(() => props.aiProviders.length > 0)

    // Prepend a "None" option so the AI provider can be cleared.
    const aiProviderOptions = computed(() => [{ id: null as number | null, name: 'None' }, ...props.aiProviders])

    // Keep the denormalised attribute_name in sync with the selected template id.
    const selectAttribute = (item: AttributeGroupItem, id: number): void => {
        item.attribute_id = id
        item.attribute_name = props.attributeTemplates.find((a) => a.id === id)?.name ?? ''
    }
</script>
