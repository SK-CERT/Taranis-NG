# Routing and Authentication

**Last Updated:** April 28, 2026

## Overview

Routing uses **Vue Router 4** with `createWebHistory` base `/v2/`. Authentication is JWT-based with optional external (Keycloak/OIDC) login support. All route protection is handled in a single `beforeEach` guard.

## Route Structure

Routes are defined in `src/router.js`. Each route specifies:
- `meta.requiresAuth` — whether the user must be logged in
- `meta.requiresPerm` — array of permissions; user must have at least one

```js
{
  path: '/assess/group/:groupId',
  name: 'assess',
  components: {
    default: () => import('./views/users/AssessView.vue'),
    nav:     () => import('./views/nav/AssessNav.vue')
  },
  meta: { requiresAuth: true, requiresPerm: [Permissions.ASSESS_ACCESS] }
}
```

### Named Router Views

`App.vue` has two `<router-view>` outlets:

| Outlet | Purpose |
|--------|---------|
| `default` (unnamed) | Main content area (`<v-main>`) |
| `nav` | Side navigation drawer (96px rail) |

Each route provides separate components for both outlets. Views that share the same nav (e.g. all `/config/*` routes) all point to `ConfigNav.vue`.

### View Layout

Most views use `ViewLayout.vue` which renders a toolbar slot above a scrollable content slot:

```
┌─────────────────────────────┐
│ Toolbar (slot)              │
├─────────────────────────────┤
│ Content (slot, scrollable)  │
└─────────────────────────────┘
```

## Navigation Guard

The `beforeEach` guard in `router.js` runs on every navigation:

```
Request to route
    │
    ├─ requiresAuth?
    │       │
    │   not authenticated ──► external login URL? ──► redirect externally
    │                                    │
    │                               no ──► /login?redirect=...
    │       │
    │   authenticated + path is "/"
    │       │
    │       ├─ has ASSESS_ACCESS? ──► /dashboard
    │       ├─ has CONFIG_ACCESS? ──► /config
    │       └─ has MY_ASSETS_ACCESS? ──► /myassets
    │       │
    │   authenticated + other path
    │       │
    │       └─ requiresPerm has entries?
    │               │
    │           user has any perm? ──► allow
    │                        │
    │                        no ──► redirect /
    │
    └─ no requiresAuth ──► allow (e.g. /login)
```

After each navigation, `afterEach` sets `document.title` from `route.meta.title`.

## Authentication Services

| File | Purpose |
|------|---------|
| `src/services/auth_service.js` | JWT decode, token validity, permission checks |
| `src/services/permissions.js` | Main enum of permission strings used by route and UI checks |
| `src/services/auth/permissions.js` | Secondary permissions module used by the attribute editing composable |
| `src/stores/auth.js` | Pinia store — JWT, login/logout actions, external URL state |
| `src/stores/user.js` | Current user profile (id, name, roles) |
| `src/composables/useAuth.js` | Convenience composable combining auth + user stores |

### Permission Checking

```js
import { useAuth } from '@/composables/useAuth'

const { checkPermission, checkAnyPermission } = useAuth()

// Single permission
if (checkPermission(Permissions.ANALYZE_UPDATE)) { ... }

// Any of several
if (checkAnyPermission([Permissions.CONFIG_USER_CREATE, Permissions.CONFIG_USER_UPDATE])) { ... }
```

`Permissions` constants follow the pattern `{DOMAIN}_{ACTION}`:

```
ASSESS_ACCESS / CREATE / UPDATE / DELETE
ANALYZE_ACCESS / CREATE / UPDATE / DELETE
PUBLISH_ACCESS / CREATE / UPDATE / DELETE / PRODUCT
MY_ASSETS_ACCESS / CREATE / CONFIG
CONFIG_ACCESS
CONFIG_{RESOURCE}_ACCESS / CREATE / UPDATE / DELETE
```

### External Authentication (Keycloak/OIDC)

When `authStore.externalLoginUrl` is set:
- The login page redirects to the external provider instead of showing the username/password form
- `Login.vue` completes the external login flow using `code` and `session_state` query parameters
- `App.vue` can also consume a `jwt` cookie and convert it into the active session token
- `authStore.hasExternalLogoutUrl` determines whether logout redirects externally

## SSE (Server-Sent Events)

Real-time updates are managed by the `useSSE()` composable (`src/composables/useSSE.js`), initialized in `App.vue` on mount.

```js
const { connect, subscribe, disconnect } = useSSE()

await connect()
subscribe('news-items-updated', (data) => assessStore.handleUpdate(data))
subscribe('report-items-updated', (data) => analyzeStore.handleUpdate(data))
```

The SSE endpoint URL is read from `VITE_APP_TARANIS_NG_CORE_SSE` (falls back to `/sse`). The composable:
- Automatically re-registers all handlers after reconnect
- Calls `disconnect()` on `onUnmounted`
- Uses `withCredentials: true` on the `EventSource`

`App.vue` subscribes to these events and re-emits them as window events for workflow-specific components:
- `news-items-updated`
- `report-items-updated`
- `report-item-updated`
- `report-item-locked`
- `report-item-unlocked`
