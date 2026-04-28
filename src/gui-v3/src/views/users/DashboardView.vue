<template>
  <ViewLayout>
    <template #panel>
      <!-- Future: Add dashboard controls/filters here -->
    </template>
    <template #content>
      <v-row no-gutters>
        <!-- Main Content - News Items & Tag Cloud -->
        <v-col cols="12" lg="8" class="pa-2">
          <v-card class="mt-4">
            <v-card-text class="pt-0">
              <div class="text-headline-medium mb-2">{{ t('nav_menu.newsitems') }}</div>
              <div class="text-subtitle-2 text-medium-emphasis">
                {{ t('dashboard.assess.tagcloud') }}
              </div>
              <v-divider class="my-2" />

              <!-- Word Cloud -->
              <WordCloud
                :data="tagCloud"
                :color-scheme="getColorScheme()"
                :min-font-size="14"
                :max-font-size="50"
                :empty-message="t('common.no_data')"
                @word-click="handleWordClick"
              />

              <v-divider class="my-2" />
              <v-icon class="mr-2" color="primary">mdi-email-multiple</v-icon>
              <span class="text-caption text-medium-emphasis">
                <strong>{{ dashboardData.total_news_items || 0 }}</strong>
                {{ t('dashboard.assess.total') }}
              </span>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Sidebar - Stats Cards -->
        <v-col cols="12" lg="4" class="pa-2">
          <!-- Collection Status -->
          <v-card class="mt-4">
            <v-card-text class="pt-0">
              <div class="text-headline-small mb-2">{{ t('dashboard.collect.title') }}</div>
              <div class="text-subtitle-2 text-medium-emphasis">
                {{ t('dashboard.collect.status') }}
              </div>
              <v-divider class="my-2" />

              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2" color="green">mdi-lightbulb-off-outline</v-icon>
                <span class="text-caption text-medium-emphasis">
                  {{ t('dashboard.collect.pending') }}
                </span>
              </div>
              <v-divider inset class="mb-2 mt-2" />

              <div class="d-flex align-center">
                <v-icon class="mr-2" color="primary">mdi-clock-check-outline</v-icon>
                <span class="text-caption text-medium-emphasis">
                  {{ t('dashboard.collect.last_attempt') }}
                  <strong>{{ dashboardData.latest_collected || 'N/A' }}</strong>
                </span>
              </div>
            </v-card-text>
          </v-card>

          <!-- Report Items Status -->
          <v-card class="mt-4">
            <v-card-text class="pt-0">
              <div class="text-headline-small mb-2">{{ t('nav_menu.report_items') }}</div>
              <div class="text-subtitle-2 text-medium-emphasis">
                {{ t('dashboard.analyze.status') }}
              </div>
              <v-divider class="my-2" />

              <!-- Dynamic state display -->
              <template
                v-for="(stateData, stateName) in dashboardData.report_item_states"
                :key="stateName"
              >
                <div v-if="stateData.count > 0">
                  <div class="d-flex align-center mb-2">
                    <v-icon class="mr-2" :color="stateData.color" size="small">
                      {{ stateData.icon }}
                    </v-icon>
                    <span class="text-caption text-medium-emphasis">
                      <strong>{{ stateData.count }}</strong>
                      {{ getStateDisplayName(stateData.display_name).toLowerCase() }}
                      {{ t('dashboard.analyze.report_items') }}
                    </span>
                  </div>
                  <v-divider inset class="mb-2" />
                </div>
              </template>

              <!-- Total summary -->
              <div class="d-flex align-center mt-2">
                <v-icon class="mr-2" color="primary">mdi-file-document</v-icon>
                <span class="text-caption text-medium-emphasis">
                  <strong>{{ dashboardData.total_report_items || 0 }}</strong>
                  {{ t('dashboard.analyze.total') }}
                </span>
              </div>
            </v-card-text>
          </v-card>

          <!-- Products Status -->
          <v-card class="mt-4">
            <v-card-text class="pt-0">
              <div class="text-headline-small mb-2">{{ t('nav_menu.products') }}</div>
              <div class="text-subtitle-2 text-medium-emphasis">
                {{ t('dashboard.publish.status') }}
              </div>
              <v-divider class="my-2" />

              <!-- Dynamic state display -->
              <template
                v-for="(stateData, stateName) in dashboardData.product_states"
                :key="stateName"
              >
                <div v-if="stateData.count > 0">
                  <div class="d-flex align-center mb-2">
                    <v-icon class="mr-2" :color="stateData.color" size="small">
                      {{ stateData.icon }}
                    </v-icon>
                    <span class="text-caption text-medium-emphasis">
                      <strong>{{ stateData.count }}</strong>
                      {{ getStateDisplayName(stateData.display_name).toLowerCase() }}
                      {{ t('dashboard.publish.products') }}
                    </span>
                  </div>
                  <v-divider inset class="mb-2" />
                </div>
              </template>

              <!-- Total summary -->
              <div class="d-flex align-center mt-2">
                <v-icon class="mr-2" color="primary">mdi-package-variant</v-icon>
                <span class="text-caption text-medium-emphasis">
                  <strong>{{ dashboardData.total_products || 0 }}</strong>
                  {{ t('dashboard.publish.total') }}
                </span>
              </div>
            </v-card-text>
          </v-card>

          <!-- About Section -->
          <v-card class="mt-4">
            <v-card-text class="pt-0">
              <div class="text-h6 mb-2">{{ t('dashboard.about.title') }}</div>
              <v-divider class="my-2" />

              <!-- Version Info -->
              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2" color="blue">mdi-information-outline</v-icon>
                <span class="text-caption text-medium-emphasis">
                  {{ t('dashboard.about.version') }}
                  <strong>{{ appVersion }}</strong> {{ built }}
                </span>
              </div>

              <!-- Commit Info -->
              <v-divider inset class="my-2" />
              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2" color="blue">mdi-source-branch</v-icon>
                <span class="text-caption text-medium-emphasis">
                  {{ t('dashboard.about.commit') }}
                  <strong>{{ commit }}</strong> {{ commited }} {{ branchDisplay }}
                </span>
              </div>

              <!-- Database Records -->
              <v-divider inset class="my-2" />
              <div class="d-flex align-center">
                <v-icon class="mr-2" color="blue">mdi-database</v-icon>
                <span class="text-caption text-medium-emphasis">
                  <strong>{{ dashboardData.total_database_items || 0 }}</strong>
                  {{ t('dashboard.about.total') }}
                </span>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </ViewLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDashboardStore } from '@/stores/dashboard'
import { useSettingsStore } from '@/stores/settings'
import ViewLayout from '@/components/layouts/ViewLayout.vue'
import WordCloud from '@/components/dashboard/WordCloud.vue'
import Settings from '@/services/settings'
import { format } from 'date-fns'
import gitMeta from '../../../git-info.json'
import packageJson from '../../../package.json'

const { t, te } = useI18n()
const dashboardStore = useDashboardStore()
const settingsStore = useSettingsStore()

// Version and build info (from git-info.json generated by prebuild script)
const appVersion = ref(gitMeta.version || packageJson.version || 'unknown')
const buildDate = ref(gitMeta.buildDate || null)
const commitHash = ref(gitMeta.commit || null)
const commitDate = ref(gitMeta.commitDate || null)
const branchName = ref(gitMeta.branchName || null)

const dashboardData = computed(() => dashboardStore.dashboard_data || {})
const tagCloud = computed(() => dashboardData.value.tag_cloud || [])

const formatToLocal = (dateString) => {
  return format(new Date(dateString), 'yyyy-MM-dd HH:mm')
}

const built = computed(() => {
  return buildDate.value ? `(${formatToLocal(buildDate.value)})` : ''
})

const commit = computed(() => {
  return commitHash.value ? commitHash.value : ''
})

const commited = computed(() => {
  return commitDate.value ? `(${formatToLocal(commitDate.value)})` : ''
})

const branchDisplay = computed(() => {
  return branchName.value ? `[${branchName.value}]` : ''
})

let refreshInterval = null

/**
 * Get translated state display name
 */
const getStateDisplayName = (displayName) => {
  const key = `workflow.states.${displayName}`
  return te(key) ? t(key) : displayName
}

/**
 * Get color scheme based on settings
 */
const getColorScheme = () => {
  try {
    const useCategory = settingsStore.getSetting(Settings.TAG_COLOR)
    if (useCategory) {
      return [
        '#ff7200',
        '#d9534f',
        '#5cb85c',
        '#0275d8',
        '#5bc0de',
        '#5a5a5a',
        '#ff9100',
        '#df691a',
        '#e67e22',
        '#27ae60'
      ]
    }
  } catch (e) {
    console.warn('[Dashboard] Could not load TAG_COLOR setting:', e)
  }
  return ['#1f77b4', '#629fc9', '#94bedb', '#c9e0ef']
}

/**
 * Handle word click from word cloud
 */
const handleWordClick = (tag) => {
  console.log('[Dashboard] Word clicked:', tag.word, 'Quantity:', tag.word_quantity)
}

/**
 * Refresh dashboard data
 */
const refreshDashboard = async () => {
  try {
    await dashboardStore.loadDashboardData()
  } catch (error) {
    console.error('[Dashboard] Error refreshing data:', error)
  }
}

/**
 * Component mount
 */
onMounted(async () => {
  console.log('[DashboardView] Mounting - initial load')

  // Initial data load
  await refreshDashboard()

  console.log('[DashboardView] Dashboard data loaded:', {
    tagCloudLength: tagCloud.value?.length,
    tagCloud: tagCloud.value,
    dashboardData: dashboardData.value
  })

  // Auto-refresh every 10 minutes (600000ms)
  refreshInterval = setInterval(() => {
    refreshDashboard()
  }, 600000)
})

/**
 * Component unmount
 */
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.text-h5 {
  font-weight: 500;
}

.text-h6 {
  font-weight: 500;
}
</style>
