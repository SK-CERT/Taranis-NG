<template>
    <v-container
        fluid
        class="pa-0"
    >
        <div
            v-if="processedData && processedData.length > 0"
            class="word-cloud-container d-flex flex-wrap gap-2 align-center justify-center pa-4"
        >
            <v-chip
                v-for="tag in processedData"
                :key="tag.word"
                :style="getChipStyle(tag)"
                :color="getRandomColor()"
                variant="tonal"
                size="large"
                class="word-chip"
                @click="handleWordClick(tag)"
            >
                <span :style="{ fontSize: getTagFontSize(tag) + 'px' }">{{ tag.word }}</span>
                <!-- <span class="ml-1 text-caption">{{ tag.word_quantity }}</span> -->
            </v-chip>
        </div>
        <div
            v-else
            class="pa-4 text-center"
        >
            <v-alert
                type="info"
                variant="tonal"
            >
                {{ emptyMessage }}
            </v-alert>
        </div>
    </v-container>
</template>

<script setup lang="ts">
    import { computed } from 'vue'

    type WordCloudItem = {
        word: string
        word_quantity: number
    }

    const props = withDefaults(
        defineProps<{
            data?: WordCloudItem[]
            minFontSize?: number
            maxFontSize?: number
            colorScheme?: string[]
            emptyMessage?: string
        }>(),
        {
            data: () => [],
            minFontSize: 14,
            maxFontSize: 50,
            colorScheme: () => ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'],
            emptyMessage: 'No data available'
        }
    )

    /**
     * Process and validate data
     */
    const processedData = computed(() => {
        if (!props.data) {
            console.warn('[WordCloud] No data provided')
            return []
        }

        if (!Array.isArray(props.data)) {
            console.warn('[WordCloud] Data is not an array:', props.data)
            return []
        }

        if (props.data.length === 0) {
            // console.log('[WordCloud] Empty data array')
            return []
        }

        // Validate data items have required fields
        const validated = props.data.filter((item) => {
            if (!item.word || item.word_quantity === undefined) {
                console.warn('[WordCloud] Invalid item structure:', item)
                return false
            }
            return true
        })

        // console.log('[WordCloud] Processed data:', validated.length, 'items')
        return validated
    })

    /**
     * Sort tags by word quantity in descending order
     */
    const sortedTags = computed(() => {
        if (!processedData.value || processedData.value.length === 0) {
            return []
        }
        return [...processedData.value].sort((a, b) => (b.word_quantity || 0) - (a.word_quantity || 0))
    })

    /**
     * Get min and max quantities for scaling
     */
    const quantityRange = computed(() => {
        if (sortedTags.value.length === 0) {
            return { min: 0, max: 1 }
        }
        const quantities = sortedTags.value.map((t) => t.word_quantity || 0)
        const min = Math.min(...quantities)
        const max = Math.max(...quantities)
        return { min, max }
    })

    /**
     * Calculate font size for a tag based on its quantity
     */
    const getTagFontSize = (tag: WordCloudItem): number => {
        const { min, max } = quantityRange.value
        if (max === min) {
            return (props.minFontSize + props.maxFontSize) / 2
        }
        const ratio = (tag.word_quantity - min) / (max - min)
        return props.minFontSize + ratio * (props.maxFontSize - props.minFontSize)
    }

    /**
     * Get random color from scheme
     */
    const getRandomColor = (): string => {
        return props.colorScheme[Math.floor(Math.random() * props.colorScheme.length)] || 'var(--v-theme-primary)'
    }

    /**
     * Get chip style (opacity based on frequency)
     */
    const getChipStyle = (tag: WordCloudItem): { opacity: number } => {
        const { min, max } = quantityRange.value
        if (max === min) {
            return { opacity: 0.8 }
        }
        const ratio = (tag.word_quantity - min) / (max - min)
        const opacity = 0.5 + ratio * 0.5 // Range from 0.5 to 1.0
        return { opacity }
    }

    /**
     * Handle word click
     */
    const handleWordClick = (tag: WordCloudItem): void => {
        console.log('[WordCloud] Word clicked:', tag.word, 'Quantity:', tag.word_quantity)
    }
</script>

<style scoped>
    .word-cloud-container {
        background: rgba(0, 0, 0, 0.01);
        border-radius: 4px;
        min-height: 300px;
        max-height: 500px;
        overflow-y: auto;
    }

    .word-chip {
        cursor: pointer;
        transition: all 0.3s ease;
        margin: 4px;
    }

    .word-chip:hover {
        transform: scale(1.1);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
    }

    .gap-2 {
        gap: 8px;
    }
</style>
