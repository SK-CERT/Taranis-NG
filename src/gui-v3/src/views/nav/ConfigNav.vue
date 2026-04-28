<template>
  <v-list density="compact" class="pa-0">
    <!-- Section icon -->
    <v-list-item class="justify-center pa-2">
      <v-icon :color="iconColor" size="large">mdi-cog</v-icon>
    </v-list-item>

    <v-divider class="mx-2" :color="dividerColor" />

    <!-- Config links with permission filtering -->
    <template v-for="link in filteredLinks" :key="link.id">
      <v-divider
        v-if="link.separator"
        class="mx-2 my-1"
        :color="dividerColor"
        :thickness="1"
      />
      <v-list-item
        v-else
        :to="link.route"
        class="px-1 py-2"
        density="compact"
      >
        <template #default>
          <div class="d-flex flex-column align-center text-center">
            <v-icon :color="iconColor" size="small" class="mb-1">
              {{ link.icon }}
            </v-icon>
            <span class="text-caption" :style="{ color: textColor, fontSize: '0.65rem', lineHeight: '1.2' }">
              {{ link.translate ? $t(link.title) : link.title }}
            </span>
          </div>
        </template>
      </v-list-item>
    </template>
  </v-list>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import { useAuth } from '@/composables/useAuth'

const { checkPermission } = useAuth()
const { global: themeGlobal } = useTheme()

const isDark = computed(() => themeGlobal.name.value === 'dark')
const textColor = computed(() => isDark.value ? '#ffffff' : '#000000')
const iconColor = computed(() => isDark.value ? '#ffffff' : 'rgba(0, 0, 0, 0.54)')
const dividerColor = computed(() => isDark.value ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.12)')

const links = [
  {
    id: 1,
    icon: 'mdi-account-group',
    title: 'nav_menu.users',
    route: '/config/users',
    permission: 'CONFIG_USER_ACCESS',
    translate: true
  },
  {
    id: 2,
    icon: 'mdi-office-building',
    title: 'nav_menu.organizations',
    route: '/config/organizations',
    permission: 'CONFIG_ORGANIZATION_ACCESS',
    translate: true
  },
  {
    id: 3,
    icon: 'mdi-account-arrow-right',
    title: 'nav_menu.roles',
    route: '/config/roles',
    permission: 'CONFIG_ROLE_ACCESS',
    translate: true
  },
  {
    id: 4,
    icon: 'mdi-lock-check',
    title: 'nav_menu.acls',
    route: '/config/acls',
    permission: 'CONFIG_ACL_ACCESS',
    translate: true
  },
  { id: 5, separator: true },
  {
    id: 6,
    icon: 'mdi-download-network',
    title: 'nav_menu.collectors',
    route: '/config/collectors',
    translate: true
  },
  { id: 7, separator: true },
  {
    id: 8,
    icon: 'mdi-presentation',
    title: 'nav_menu.presenters',
    route: '/config/presenters',
    translate: true
  },
  { id: 9, separator: true },
  {
    id: 10,
    icon: 'mdi-upload-network',
    title: 'nav_menu.publishers',
    route: '/config/publishers',
    translate: true
  },
  { id: 11, separator: true },
  {
    id: 12,
    icon: 'mdi-application-variable-outline',
    title: 'nav_menu.attributes',
    route: '/config/reportitems/attributes',
    permission: 'CONFIG_ATTRIBUTE_ACCESS',
    translate: true
  },
  {
    id: 13,
    icon: 'mdi-file-table',
    title: 'nav_menu.report_types',
    route: '/config/reportitems/types',
    permission: 'CONFIG_REPORT_TYPE_ACCESS',
    translate: true
  },
  { id: 14, separator: true },
  { id: 15, icon: 'mdi-robot', title: 'nav_menu.bots', route: '/config/bots', translate: true },
  { id: 16, separator: true },
  {
    id: 17,
    icon: 'mdi-remote',
    title: 'nav_menu.remote',
    route: '/config/remote',
    translate: true
  },
  { id: 18, separator: true },
  {
    id: 19,
    icon: 'mdi-application-cog-outline',
    title: 'nav_menu.settings',
    route: '/config/settings',
    permission: 'CONFIG_SETTINGS_ACCESS',
    translate: true
  },
  {
    id: 20,
    icon: 'mdi-format-list-text',
    title: 'nav_menu.word_lists',
    route: '/config/wordlists',
    permission: 'CONFIG_WORD_LIST_ACCESS',
    translate: true
  },
  {
    id: 21,
    icon: 'mdi-state-machine',
    title: 'nav_menu.workflow',
    route: '/config/workflow',
    permission: 'CONFIG_WORKFLOW_ACCESS',
    translate: true
  },
  {
    id: 22,
    icon: 'mdi-cloud-arrow-down',
    title: 'nav_menu.data_providers',
    route: '/config/data-providers',
    permission: 'CONFIG_DATA_PROVIDER_ACCESS',
    translate: true
  },
  { id: 23, separator: true },
  {
    id: 24,
    icon: 'mdi-database-export',
    title: 'nav_menu.external',
    route: '/config/external',
    permission: 'MY_ASSETS_CONFIG',
    translate: true
  }
]

// Filter links based on permissions and remove leading/trailing separators
const filteredLinks = computed(() => {
  const filtered = []

  for (let i = 0; i < links.length; i++) {
    const link = links[i]

    if (link.separator) {
      // Only add separator if there are items before it and it's not the first item
      if (filtered.length > 0 && !filtered[filtered.length - 1].separator) {
        filtered.push(link)
      }
    } else if (!link.permission || checkPermission(link.permission)) {
      filtered.push(link)
    }
  }

  // Remove leading separator
  if (filtered.length > 0 && filtered[0].separator) {
    filtered.shift()
  }

  // Remove trailing separator
  if (filtered.length > 0 && filtered[filtered.length - 1].separator) {
    filtered.pop()
  }

  return filtered
})
</script>

<style scoped>
.v-list-item {
  min-height: auto;
}
</style>
