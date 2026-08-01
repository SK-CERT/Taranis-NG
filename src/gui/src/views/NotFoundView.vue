<template>
    <v-container
        class="d-flex flex-column align-center justify-center text-center"
        style="min-height: 70vh"
    >
        <v-icon
            size="96"
            color="primary"
            class="mb-4"
        >
            {{ ICONS.ALERT_CIRCLE }}
        </v-icon>

        <div class="text-h3 font-weight-medium mb-2">404</div>
        <div class="text-h5 mb-2">{{ t('error.not_found.title') }}</div>
        <p class="text-body-1 text-medium-emphasis mb-2">
            {{ t('error.not_found.message') }}
        </p>
        <code class="text-caption text-medium-emphasis mb-6">{{ attemptedPath }}</code>

        <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-home"
            @click="goHome"
        >
            {{ t('error.not_found.home') }}
        </v-btn>
    </v-container>
</template>

<script setup lang="ts">
    import { computed } from 'vue'
    import { useRoute, useRouter } from 'vue-router'
    import { useI18n } from 'vue-i18n'
    import { ICONS } from '@/config/ui-constants'

    const { t } = useI18n()
    const route = useRoute()
    const router = useRouter()

    const attemptedPath = computed(() => route.fullPath)

    const goHome = (): void => {
        router.push('/')
    }
</script>
