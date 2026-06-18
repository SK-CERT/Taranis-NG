<template>
    <v-list density="compact">
        <!-- Group links -->
        <v-list-subheader>{{ $t('assess.groups') }}</v-list-subheader>
        <v-list-item v-for="group in groups" :key="group.id" :to="group.route" class="pa-2">
            <template #default>
                <div class="d-flex flex-column align-center text-center">
                    <v-icon :color="group.color || undefined" class="mb-2">
                        {{ group.icon }}
                    </v-icon>
                    <span class="text-body-small">
                        {{ group.translate ? $t(group.title) : group.title }}
                    </span>
                </div>
            </template>
        </v-list-item>
    </v-list>
</template>

<script setup lang="ts">
    import { ref, onMounted } from 'vue'
    import { useRouter, useRoute } from 'vue-router'
    import { useConfigStore } from '@/stores/config'

    type AssessGroup = {
        id: string | number
        icon: string
        color: string | null
        title: string
        translate: string
        route: string
    }

    const router = useRouter()
    const route = useRoute()
    const configStore = useConfigStore()

    const groups = ref<AssessGroup[]>([])

    onMounted(async () => {
        try {
            await configStore.loadOSINTSourceGroupsAssess({ search: '' })
            groups.value = configStore.osintSourceGroupsForAssess as AssessGroup[]

            // If not on a specific group route and groups exist, redirect to first
            if (!route.path.includes('/group/') && groups.value.length > 0) {
                const firstGroup = groups.value[0]
                if (firstGroup) {
                    router.push(firstGroup.route)
                }
            }
        } catch (error) {
            console.error('Error loading OSINT source groups:', error)
        }
    })
</script>
