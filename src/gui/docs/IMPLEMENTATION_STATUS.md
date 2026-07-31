# Vue3 GUI Implementation Status

**Last Updated:** July 26, 2026

This file is the canonical current-status snapshot for the Taranis-NG GUI at
`src/gui/`. The legacy Vue 2 GUI has been removed; this Vue 3 application is
the sole UI, served at `/`.

## Current Status

- **Location:** `src/gui/`
- **Router base path:** `/`
- **Deployment model:** single `gui` Docker service (`taranis-ng-gui` image,
  built from `docker/Dockerfile.gui`) behind Traefik.

The application has the expected core architecture in place:

- Vue 3 + Composition API (`<script setup>`)
- Vue Router 4
- Pinia
- Vuetify 3
- Vue I18n
- Axios-based API service layer
- SSE integration via composables

## Implemented Areas

### Application Shell

Implemented and present in the current repo:

- `src/main.ts`
- `src/App.vue`
- `src/router.ts`
- `src/services/api_service.ts`
- `src/services/auth_service.ts`
- `src/services/permissions.ts`
- `src/composables/useAuth.ts`
- `src/composables/useSSE.ts`
- Pinia stores under `src/stores/`

### Main User Views

Present in `src/views/users/`:

- `DashboardView.vue`
- `AssessView.vue`
- `AnalyzeView.vue`
- `PublishView.vue`
- `MyAssetsView.vue`

Also present:

- `HomeView.vue`
- `Login.vue`
- Navigation views for Assess, Analyze, Publish, MyAssets, Dashboard, and Config

### Assess Workflow

Implemented components currently present:

- `CardAssess.vue`
- `ContentDataAssess.vue`
- `ToolbarFilterAssess.vue`
- `NewsItemDetailDialog.vue`
- `NewsItemSingleDetail.vue`
- `NewsItemAggregateDetail.vue`
- `NewsItemAttribute.vue`
- `ReportsListDialog.vue`
- `AddNewsItemDialog.vue`
- `AssessItemActions.vue`

### Analyze Workflow

Implemented components currently present:

- `CardAnalyze.vue`
- `ContentDataAnalyze.vue`
- `ToolbarFilterAnalyze.vue`
- `NewReportItem.vue`
- `NewsItemSelector.vue`
- `RemoteReportItem.vue`
- `RemoteReportItemSelector.vue`

### Publish Workflow

Implemented components currently present:

- `CardProduct.vue`
- `ContentDataPublish.vue`
- `ToolbarFilterPublish.vue`
- `NewProduct.vue`
- `ReportItemSelector.vue`

### Assets Workflow

Implemented components currently present:

- `CardAsset.vue`
- `ContentDataAssets.vue`
- `ToolbarFilterAssets.vue`
- `NewAsset.vue`
- `AssetDetailDialog.vue`

### Attribute System

The shared attribute system is implemented under `src/components/common/attribute/`.

Present components include:

- Core types: `AttributeString`, `AttributeNumber`, `AttributeBoolean`, `AttributeEnum`, `AttributeRadio`, `AttributeText`, `AttributeDate`
- Common types: `AttributeTime`, `AttributeDateTime`, `AttributeRichText`, `AttributeTLP`, `AttributeAttachment`
- Advanced types: `AttributeCPE`, `AttributeCVE`, `AttributeCWE`, `AttributeCVSS`
- Layout/dispatcher: `AttributeContainer`, `AttributeItemLayout`, `AttributeValueLayout`
- Remote variants: `RemoteAttributeContainer`, `RemoteAttributeAttachment`, `RemoteAttributeString`

### Admin / Configuration

The admin/config surface is broadly implemented. Current `src/views/admin/` includes:

- ACL entries
- Asset groups
- Attributes
- Bot presets / bots
- Collectors
- Config landing view
- Data providers
- External users / external view
- Notification templates
- Organizations
- OSINT sources / groups
- Presenters
- Product types
- Publisher presets / publishers
- Remote accesses / remote view
- Report types
- Roles
- Settings
- Users
- Word lists
- Workflow

## Confirmed Remaining Gaps

The following components are confirmed absent from the current `src/gui/src` tree:

### User-Facing Gaps

- `EnterView.vue`
- `EnterNav.vue`

### Assets / Vulnerability Gaps

- `CPETable.vue`
- `CardVulnerability.vue`
- `VulnerabilityDetail.vue`

### Config / Specialized Card or Table Gaps

- `CardSource.vue`
- `CardGroup.vue`
- `CardProductType.vue`
- `CardUser.vue`
- `WordTable.vue`
- `AttributeTable.vue`
- `RecipientTable.vue`

### Legacy / Specialized Helper Gaps

- `ToolbarGroupAnalyze.vue`
- `ToolbarGroupAssess.vue`
- `CardAssessItem.vue`

Some of these may be intentionally superseded by generic Vue3 patterns rather than being direct blockers. This list is only a statement of current file presence/absence.

## Status Summary

### Current Working Surface

- App shell is present and wired
- Main user views are present
- Assess, Analyze, Publish, and Assets flows all have working component surfaces
- Attribute system is present
- Admin/config views are present
- Architecture documentation exists

### Not Yet Complete

- Full parity with every former Vue2 component is not finished
- Some specialized views/components remain absent (listed above)

## Canonical Documentation

For architecture details, use:

- [README.md](../README.md)
- [architecture/STATE_MANAGEMENT.md](./architecture/STATE_MANAGEMENT.md)
- [architecture/ROUTING_AND_AUTH.md](./architecture/ROUTING_AND_AUTH.md)
- [architecture/ATTRIBUTE_SYSTEM.md](./architecture/ATTRIBUTE_SYSTEM.md)
- [architecture/UNIFIED_TOOLBAR_FILTERS.md](./architecture/UNIFIED_TOOLBAR_FILTERS.md)
