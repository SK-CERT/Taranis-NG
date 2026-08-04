<template>
    <v-container
        fluid
        class="pa-0"
    >
        <div
            v-if="cloudWords.length > 0"
            class="word-cloud-container"
            role="list"
            aria-label="Word cloud"
        >
            <span
                v-for="tag in cloudWords"
                :key="tag.word"
                class="word-cloud-item"
                role="listitem"
                :style="getWordStyle(tag)"
                :title="`${tag.word}: ${tag.word_quantity}`"
            >
                {{ tag.word }}
            </span>
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

    type WordCloudStyle = {
        color: string
        fontSize: string
        fontWeight: number
        opacity: number
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
     * Keep valid words only and sort the cloud by relevance. The API normally
     * returns this order already, but doing it here makes the component stable
     * for every caller.
     */
    const cloudWords = computed(() => {
        if (!Array.isArray(props.data)) {
            return []
        }

        return props.data
            .filter((item) => item && typeof item.word === 'string' && item.word.trim() && Number.isFinite(item.word_quantity))
            .map((item) => ({ ...item, word: item.word.trim() }))
            .sort((a, b) => b.word_quantity - a.word_quantity || a.word.localeCompare(b.word))
    })

    const quantityRange = computed(() => {
        if (cloudWords.value.length === 0) {
            return { min: 0, max: 1 }
        }

        const quantities = cloudWords.value.map(({ word_quantity }) => Math.max(0, word_quantity))
        return {
            min: Math.min(...quantities),
            max: Math.max(...quantities)
        }
    })

    /**
     * A square-root scale keeps one very frequent word from visually drowning
     * out the rest of the cloud while preserving the relative prominence.
     */
    const getScale = (tag: WordCloudItem): number => {
        const { min, max } = quantityRange.value
        if (max === min) {
            return 0.5
        }

        const ratio = (Math.max(0, tag.word_quantity) - min) / (max - min)
        return Math.sqrt(Math.max(0, ratio))
    }

    const getColor = (word: string): string => {
        const colors = props.colorScheme.filter(Boolean)
        if (colors.length === 0) {
            return 'rgb(var(--v-theme-primary))'
        }

        // Stable colors prevent the cloud from changing on every reactive update.
        const hash = Array.from(word).reduce((value, character) => (value * 31 + character.codePointAt(0)!) >>> 0, 0)
        return colors[hash % colors.length]!
    }

    const getWordStyle = (tag: WordCloudItem): WordCloudStyle => {
        const scale = getScale(tag)
        const fontSize = props.minFontSize + scale * (props.maxFontSize - props.minFontSize)

        return {
            color: getColor(tag.word),
            fontSize: `clamp(${props.minFontSize}px, ${fontSize.toFixed(2)}px, ${props.maxFontSize}px)`,
            fontWeight: Math.round(450 + scale * 250),
            opacity: 0.7 + scale * 0.3
        }
    }
</script>

<style scoped>
    .word-cloud-container {
        display: flex;
        flex-wrap: wrap;
        align-content: center;
        align-items: baseline;
        justify-content: center;
        min-height: clamp(20rem, 44vh, 34rem);
        padding: clamp(1.5rem, 4vw, 4rem);
        gap: clamp(0.55rem, 1.2vw, 1.15rem) clamp(0.9rem, 1.8vw, 1.75rem);
        overflow: visible;
        border-radius: 8px;
        background:
            radial-gradient(circle at 50% 45%, rgba(var(--v-theme-primary), 0.08), transparent 62%),
            rgba(var(--v-theme-surface-variant), 0.16);
    }

    .word-cloud-item {
        display: inline-block;
        max-width: 100%;
        line-height: 1.05;
        overflow-wrap: anywhere;
        text-align: center;
        text-wrap: balance;
        transition:
            opacity 160ms ease,
            transform 160ms ease;
    }

    .word-cloud-item:hover {
        opacity: 1 !important;
        transform: translateY(-2px) scale(1.04);
    }

    @media (max-width: 600px) {
        .word-cloud-container {
            min-height: 16rem;
            padding: 1.25rem;
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .word-cloud-item {
            transition: none;
        }
    }
</style>
