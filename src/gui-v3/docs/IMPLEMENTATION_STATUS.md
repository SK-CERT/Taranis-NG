# Vue3 GUI Implementation Status

**Last Updated:** April 28, 2026

This file is the canonical current-status snapshot for the Vue3 GUI under `src/gui-v3/`. It is intentionally a current-state document, not a phase-by-phase migration diary.

## Current Status

The Vue3 GUI is implemented and runs in parallel with the legacy Vue2 GUI:
- **Vue2** remains present in `src/gui/`
- **Vue3** is implemented in `src/gui-v3/`
- **Router base path:** `/v2/`
- **Deployment model:** parallel Vue2 + Vue3 during migration/cutover period

The Vue3 application has the expected core architecture in place:
- Vue 3 + Composition API
- Vue Router 4
- Pinia
- Vuetify 3
- Vue I18n
- Axios-based API service layer
- SSE integration via composables

## Implemented Areas

### Application Shell

Implemented and present in the current repo:
- `src/main.js`
- `src/App.vue`
- `src/router.js`
- `src/services/api_service.js`
- `src/services/auth_service.js`
- `src/services/permissions.js`
- `src/composables/useAuth.js`
- `src/composables/useSSE.js`
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

The following components are confirmed absent from the current `src/gui-v3/src` tree as of April 28, 2026:

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
- Vue3 app shell is present and wired
- Main user views are present
- Assess, Analyze, Publish, and Assets flows all have working Vue3 component surfaces
- Attribute system is present
- Admin/config views are present
- Architecture documentation exists and has been refreshed

### Not Yet Complete
- Full parity with every legacy Vue2 component is not finished
- Vue2 is still present and has not been cut over or removed
- Some specialized views/components remain absent

## Canonical Documentation

For architecture details, use:
- [README.md](./README.md)
- [architecture/STATE_MANAGEMENT.md](./architecture/STATE_MANAGEMENT.md)
- [architecture/ROUTING_AND_AUTH.md](./architecture/ROUTING_AND_AUTH.md)
- [architecture/ATTRIBUTE_SYSTEM.md](./architecture/ATTRIBUTE_SYSTEM.md)
- [architecture/UNIFIED_TOOLBAR_FILTERS.md](./architecture/UNIFIED_TOOLBAR_FILTERS.md)

## Validation Basis

This status document was refreshed by direct inspection of the current repo on April 28, 2026:
- current docs tree
- current Vue3 views tree
- current component directories for Assess, Analyze, Publish, Assets, and the attribute system
- confirmed missing component names checked directly against the `src/gui-v3/src` tree
