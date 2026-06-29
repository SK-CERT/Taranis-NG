<template>
    <v-container fluid class="pa-4">
        <component
            :is="cardComponent"
            v-for="item in typedItems"
            :key="item.id"
            :card="item"
            :delete-permission="deletePermission"
            :lock-default="lockDefault"
            @delete="handleDelete"
            @edit="handleEdit"
        />

        <!-- Empty state -->
        <v-row v-if="items.length === 0" justify="center" class="mt-8">
            <v-col cols="12" class="text-center">
                <v-icon size="64" color="grey-lighten-1">
                    {{ ICONS.DATABASE_OFF }}
                </v-icon>
                <p class="text-h6 text-grey-lighten-1 mt-4">
                    {{ t('common.no_data') }}
                </p>
            </v-col>
        </v-row>

        <!-- Loading indicator -->
        <v-row v-if="loading" justify="center" class="mt-4">
            <v-col cols="12" class="text-center">
                <v-progress-circular indeterminate color="primary" />
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    // Import available card components
    import CardCompact from '@/components/common/CardCompact.vue'
    // TODO: Import other card components as they are migrated
    // import CardNode from '@/components/common/CardNode.vue'
    // import CardPreset from '@/components/common/CardPreset.vue'
    // import CardUser from '@/components/config/users/CardUser.vue'
    // import CardProductType from '@/components/config/product_types/CardProductType.vue'
    // import CardSource from '@/components/config/osint_sources/CardSource.vue'
    // import CardGroup from '@/components/config/osint_sources/CardGroup.vue'

    type CardItem = {
        id: string | number
        [key: string]: unknown
    }

    const props = defineProps({
        items: {
            type: Array,
            default: () => []
        },
        cardItem: {
            type: String,
            required: true
        },
        deletePermission: {
            type: String,
            default: ''
        },
        loading: {
            type: Boolean,
            default: false
        },
        lockDefault: {
            type: Boolean,
            default: false
        }
    })

    const emit = defineEmits(['delete', 'edit', 'refresh'])

    const { t } = useI18n()

    // Map of card component names to actual components
    const cardComponents: Record<string, any> = {
        CardCompact
        // Add more as they are migrated
    }

    // Get the actual component based on cardItem prop
    const cardComponent = computed(() => {
        return cardComponents[props.cardItem] || CardCompact
    })

    const typedItems = computed<CardItem[]>(() => props.items as CardItem[])

    const handleDelete = (item: CardItem): void => {
        emit('delete', item)
    }

    const handleEdit = (item: CardItem): void => {
        emit('edit', item)
    }
</script>

<style scoped>
    /* Add any custom styles here */
</style>
