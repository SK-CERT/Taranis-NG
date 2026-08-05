<template>
    <div
        ref="containerRef"
        class="word-cloud-container"
        :class="{ 'word-cloud-container--viewport-fit': viewportFit }"
    >
        <svg
            v-if="layoutWords.length > 0"
            class="word-cloud"
            :viewBox="`0 0 ${layoutSize.width} ${layoutSize.height}`"
            preserveAspectRatio="xMidYMid meet"
            role="group"
            aria-label="Word cloud"
        >
            <g :transform="`translate(${layoutSize.width / 2} ${layoutSize.height / 2})`">
                <text
                    v-for="word in layoutWords"
                    :key="word.text"
                    class="word-cloud-item"
                    text-anchor="middle"
                    :transform="`translate(${word.x} ${word.y}) rotate(${word.rotate})`"
                    :font-size="word.size"
                    :font-weight="word.weight"
                    :fill="word.color"
                    tabindex="0"
                    role="button"
                    :aria-label="`${wordActionLabel}: ${word.text} (${word.quantity})`"
                    @click="emit('select-word', word.text)"
                    @keydown.enter.prevent="emit('select-word', word.text)"
                    @keydown.space.prevent="emit('select-word', word.text)"
                >
                    <title>{{ wordActionLabel }}: {{ word.text }} ({{ word.quantity }})</title>
                    {{ word.text }}
                </text>
            </g>
        </svg>

        <div
            v-else-if="!layingOut"
            class="word-cloud-empty"
        >
            <v-alert
                type="info"
                variant="tonal"
            >
                {{ emptyMessage }}
            </v-alert>
        </div>
    </div>
</template>

<script setup lang="ts">
    import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
    import cloud, { type Word as D3CloudWord } from 'd3-cloud'

    type WordCloudItem = {
        word: string
        word_quantity: number
    }

    type LayoutInput = D3CloudWord & {
        text: string
        quantity: number
        size: number
        weight: number
        color: string
        rotate: number
    }

    type RenderWord = LayoutInput & {
        x: number
        y: number
    }

    const props = withDefaults(
        defineProps<{
            data?: WordCloudItem[]
            minFontSize?: number
            maxFontSize?: number
            colorScheme?: string[]
            emptyMessage?: string
            viewportFit?: boolean
            wordActionLabel?: string
        }>(),
        {
            data: () => [],
            minFontSize: 14,
            maxFontSize: 50,
            colorScheme: () => ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef'],
            emptyMessage: 'No data available',
            viewportFit: false,
            wordActionLabel: 'Search'
        }
    )

    const emit = defineEmits<{
        (event: 'select-word', word: string): void
    }>()

    const containerRef = ref<HTMLElement | null>(null)
    const layoutWords = ref<RenderWord[]>([])
    const layoutSize = ref({ width: 800, height: 420 })
    const layingOut = ref(false)

    let resizeObserver: { observe: (target: Element) => void; disconnect: () => void } | null = null
    let resizeFrame = 0
    let layoutGeneration = 0
    let activeLayout: { start: () => unknown; stop: () => unknown } | null = null

    const cloudWords = computed(() => {
        if (!Array.isArray(props.data)) return []

        return props.data
            .filter((item) => item && typeof item.word === 'string' && item.word.trim() && Number.isFinite(item.word_quantity))
            .map((item) => ({ ...item, word: item.word.trim() }))
            .sort((left, right) => right.word_quantity - left.word_quantity || left.word.localeCompare(right.word))
    })

    const stableHash = (value: string): number =>
        Array.from(value).reduce((hash, character) => (hash * 31 + character.codePointAt(0)!) >>> 0, 2166136261)

    const getColor = (word: string): string => {
        const colors = props.colorScheme.filter(Boolean)
        return colors.length > 0 ? colors[stableHash(word) % colors.length]! : 'rgb(var(--v-theme-primary))'
    }

    const getRotation = (word: string): number => {
        const bucket = stableHash(word) % 14
        if (bucket === 0) return -90
        if (bucket === 1) return -45
        if (bucket === 2) return 45
        if (bucket === 3) return 90
        return 0
    }

    const seededRandom = (seed: number): (() => number) => {
        let value = seed >>> 0
        return () => {
            value += 0x6d2b79f5
            let result = value
            result = Math.imul(result ^ (result >>> 15), result | 1)
            result ^= result + Math.imul(result ^ (result >>> 7), result | 61)
            return ((result ^ (result >>> 14)) >>> 0) / 4294967296
        }
    }

    const buildWords = (fontScale: number): LayoutInput[] => {
        const quantities = cloudWords.value.map((item) => Math.max(0, item.word_quantity))
        const minimum = quantities.length ? Math.min(...quantities) : 0
        const maximum = quantities.length ? Math.max(...quantities) : 1

        return cloudWords.value.map((item) => {
            const ratio = maximum === minimum ? 0.5 : (Math.max(0, item.word_quantity) - minimum) / (maximum - minimum)
            const prominence = Math.sqrt(Math.max(0, ratio))
            const size = (props.minFontSize + prominence * (props.maxFontSize - props.minFontSize)) * fontScale

            return {
                text: item.word,
                quantity: item.word_quantity,
                size,
                weight: Math.round(450 + prominence * 250),
                color: getColor(item.word),
                rotate: getRotation(item.word)
            }
        })
    }

    const runLayout = (fontScale = 1, attempt = 0, generation = ++layoutGeneration): void => {
        const element = containerRef.value
        if (!element || cloudWords.value.length === 0) {
            activeLayout?.stop()
            layoutWords.value = []
            layingOut.value = false
            return
        }

        activeLayout?.stop()
        layingOut.value = true

        const width = Math.max(240, Math.floor(element.clientWidth))
        const height = Math.max(180, Math.floor(element.clientHeight))
        const inputWords = buildWords(fontScale)
        const randomSeed = stableHash(`${width}:${height}:${inputWords.map((word) => word.text).join('|')}`)

        layoutSize.value = { width, height }
        activeLayout = cloud<LayoutInput>()
            .size([width, height])
            .words(inputWords)
            .padding(fontScale < 0.55 ? 1 : 2)
            .rotate((word) => word.rotate)
            .font('Roboto, Arial, sans-serif')
            .fontWeight((word) => word.weight)
            .fontSize((word) => word.size)
            .spiral('archimedean')
            .random(seededRandom(randomSeed))
            .on('end', (placedWords) => {
                if (generation !== layoutGeneration) return

                if (placedWords.length < inputWords.length && attempt < 7) {
                    runLayout(fontScale * 0.78, attempt + 1, generation)
                    return
                }

                layoutWords.value = placedWords
                    .filter((word): word is RenderWord => Number.isFinite(word.x) && Number.isFinite(word.y))
                    .map((word) => ({ ...word, x: word.x, y: word.y }))
                layingOut.value = false
            })

        activeLayout.start()
    }

    const scheduleLayout = (): void => {
        window.cancelAnimationFrame(resizeFrame)
        resizeFrame = window.requestAnimationFrame(() => runLayout())
    }

    watch([cloudWords, () => props.colorScheme, () => props.minFontSize, () => props.maxFontSize], async () => {
        await nextTick()
        scheduleLayout()
    })

    onMounted(() => {
        resizeObserver = new window.ResizeObserver(scheduleLayout)
        if (containerRef.value) resizeObserver.observe(containerRef.value)
        scheduleLayout()
    })

    onBeforeUnmount(() => {
        resizeObserver?.disconnect()
        activeLayout?.stop()
        window.cancelAnimationFrame(resizeFrame)
    })
</script>

<style scoped>
    .word-cloud-container {
        position: relative;
        display: grid;
        width: 100%;
        height: clamp(20rem, 44vh, 34rem);
        min-height: 0;
        place-items: center;
        overflow: hidden;
        background:
            radial-gradient(circle at 50% 45%, rgba(var(--v-theme-primary), 0.08), transparent 62%),
            rgba(var(--v-theme-surface-variant), 0.16);
    }

    .word-cloud-container--viewport-fit {
        height: clamp(14rem, calc(100dvh - 27rem), 32rem);
    }

    .word-cloud {
        display: block;
        width: 100%;
        height: 100%;
        overflow: visible;
    }

    .word-cloud-item {
        cursor: pointer;
        opacity: 0.9;
        transition:
            opacity 140ms ease,
            filter 140ms ease;
    }

    .word-cloud-item:hover {
        opacity: 1;
        filter: brightness(0.78) saturate(1.15);
    }

    .word-cloud-item:focus-visible {
        opacity: 1;
        outline: none;
        paint-order: stroke;
        stroke: rgba(var(--v-theme-surface), 0.92);
        stroke-width: 5px;
        filter: brightness(0.78) saturate(1.2);
    }

    .word-cloud-empty {
        width: min(28rem, calc(100% - 2rem));
    }

    @media (max-width: 600px) {
        .word-cloud-container,
        .word-cloud-container--viewport-fit {
            height: clamp(13rem, 46vh, 24rem);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .word-cloud-item {
            transition: none;
        }
    }
</style>
