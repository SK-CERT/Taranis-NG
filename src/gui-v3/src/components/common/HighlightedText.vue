<template>
    <span
        v-for="(segment, index) in segments"
        :key="index"
        :class="{ 'word-list-highlight': segment.highlighted }"
    >
        {{ segment.text }}
    </span>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { splitHighlightedText } from '@/utils/word-list-highlighting'

    const props = withDefaults(
        defineProps<{
            text?: string | undefined
            words?: string[]
            enabled?: boolean
        }>(),
        {
            text: '',
            words: () => [],
            enabled: true
        }
    )

    const segments = computed(() => splitHighlightedText(props.text, props.enabled ? props.words : []))
</script>

<style scoped>
    .word-list-highlight {
        padding: 0 0.08em;
        border-radius: 2px;
        background: rgba(var(--v-theme-warning), 0.34);
        box-decoration-break: clone;
        color: inherit;
        font-weight: 700;
        -webkit-box-decoration-break: clone;
    }
</style>
