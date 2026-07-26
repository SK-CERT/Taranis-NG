# State Management

**Last Updated:** April 28, 2026

## Overview

State is managed with **Pinia** using the Composition API setup syntax (`defineStore` with a setup function). All stores are exported from a single index for clean imports.

```
src/
├── stores/
│   ├── index.ts          ← barrel export of all stores
│   ├── auth.ts           ← JWT, login/logout, external auth
│   ├── user.ts           ← current user profile and preferences
│   ├── assess.ts         ← news item aggregates and selection
│   ├── analyze.ts        ← report items and selection
│   ├── publish.ts        ← products
│   ├── assets.ts         ← asset groups and items
│   ├── dashboard.ts      ← dashboard statistics
│   ├── config.ts         ← configuration data
│   ├── settings.ts       ← user settings (theme, locale, etc.)
│   └── osint_source.ts   ← OSINT sources
└── api/
  ├── auth.ts           ← auth API calls
  ├── assess.ts         ← news item API calls
  ├── analyze.ts        ← report item API calls
  ├── publish.ts        ← product API calls
  ├── assets.ts         ← asset API calls
  ├── dashboard.ts      ← dashboard API calls
  ├── config.ts         ← config API calls
  ├── state.ts          ← workflow state API calls
  └── user.ts           ← user API calls
```

## Store Pattern

All stores follow the same structure:

```ts
export const useAssessStore = defineStore('assess', () => {
    // State — reactive refs
    const newsitems = ref({ total_count: 0, items: [] })
    const selection = ref([])

    // Getters — computed values derived from state
    const getNewsItems = computed(() => newsitems.value)
    const selectedItems = computed(() => new Set(selection.value.map((i) => i.id)))

    // Actions — async API calls that mutate state
    async function loadNewsItemsByGroup(data: { group_id: string; data: string }) {
        const response = await getNewsItemsByGroup(data.group_id, data.data)
        if (response) {
            newsitems.value = response.data
        }
        return response
    }

    return { newsitems, selection, getNewsItems, selectedItems, loadNewsItemsByGroup }
})
```

**Key conventions:**

- No mutations — state is set directly inside actions
- API calls live in `src/api/`, not in the store itself
- Cross-store imports are limited; for example, `auth.ts` imports `user.ts` to populate and clear the active user session

## API Layer

The `src/api/` files are thin wrappers over `ApiService`. Each file groups calls for one domain:

```ts
// src/api/assess.ts
import ApiService from '@/services/api_service'

export const getNewsItemsByGroup = (groupId: string, filter: string) =>
    ApiService.getWithCancel('assess', `/api/v1/assess/news-items/${groupId}?${filter}`)
```

`ApiService` (`src/services/api_service.ts`) is an axios wrapper that provides:

| Method                               | Purpose                                                              |
| ------------------------------------ | -------------------------------------------------------------------- |
| `get(resource, params)`              | Standard GET                                                         |
| `getWithCancel(key, resource)`       | GET with automatic abort of prior in-flight request for the same key |
| `post(resource, data)`               | POST                                                                 |
| `put(resource, data)`                | PUT                                                                  |
| `delete(resource)`                   | DELETE                                                               |
| `upload(resource, formData)`         | Multipart file upload                                                |
| `download(resource, data, fileName)` | POST → blob → browser download                                       |

Authorization is set globally via `ApiService.setHeader()`, which reads `localStorage.ACCESS_TOKEN` and injects it as a `Bearer` token on all requests.

One implementation detail worth knowing: `setHeader()` currently resets `axios.defaults.headers.common` when no token is present, so the wrapper owns the global authorization header state.

## Importing Stores in Components

Import from the barrel index:

```ts
import { useAssessStore, useAnalyzeStore } from '@/stores'
import { storeToRefs } from 'pinia'

const assessStore = useAssessStore()
const analyzeStore = useAnalyzeStore()

// Use storeToRefs for reactive state in templates
const { newsitems, selection } = storeToRefs(assessStore)

// Call actions directly (no need for storeToRefs)
await assessStore.loadNewsItemsByGroup({ group_id: 'all', data: filter })
```

## UI Constants

`src/config/ui-constants.ts` exports a frozen `ICONS` object and button config constants for consistent styling across all components. Always use `ICONS.*` instead of hardcoded `mdi-*` strings.

```ts
import { ICONS } from '@/config/ui-constants'

// In template:
// <v-icon>{{ ICONS.DELETE }}</v-icon>
// <v-btn :prepend-icon="ICONS.PLUS">Add</v-btn>
```
