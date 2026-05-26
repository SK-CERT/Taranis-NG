# GUI v3 TypeScript Migration Checklist

## Scope

- [x] Migrate GUI v3 incrementally from JavaScript to TypeScript
- [x] Keep runtime behavior stable during migration
- [x] Keep compatibility shims for existing JS import paths

## Phase 1: Tooling foundation

- [x] Add TS config with mixed JS+TS mode so existing code still runs
- [x] Add TypeScript tooling (`typescript`, `vue-tsc`, parser support)
- [x] Add/adjust ESLint + formatter support for TS files
- [x] Add typecheck script and validation command flow

## Phase 2: Shared types

- [x] Define common interfaces for auth (`src/types/auth.ts`)
- [x] Define common interfaces for API payloads (`src/types/api.ts`)
- [x] Define common interfaces for permissions (`src/types/permissions.ts`)
- [x] Define common interfaces for route/meta/settings (`src/types/routing.ts`, `src/types/settings.ts`)

## Phase 3: Utilities first

- [x] Convert low-risk helper modules and constants
- [x] `src/config/ui-constants.ts`
- [x] `src/components/common/cvss-utils.ts`

## Phase 4: API/services

- [x] Convert initial service layer modules with typed signatures
- [x] `src/services/permissions.ts`
- [x] `src/services/auth/permissions.ts`
- [x] `src/services/settings.ts`
- [x] `src/services/auth_service.ts`
- [x] `src/services/api_service.ts`
- [x] `src/api/analyze.ts`
- [x] `src/api/assess.ts`
- [x] `src/api/assets.ts`
- [x] `src/api/auth.ts`
- [x] `src/api/config.ts`
- [x] `src/api/dashboard.ts`
- [x] `src/api/publish.ts`
- [x] `src/api/state.ts`
- [x] `src/api/user.ts`
- [x] Convert remaining API/service JS modules as needed for full TS coverage

## Phase 5: Stores by domain

- [x] Migrate low/medium-risk stores with per-slice validation
- [x] `src/stores/user.ts`
- [x] `src/stores/settings.ts`
- [x] `src/stores/dashboard.ts`
- [x] `src/stores/assets.ts`
- [x] `src/stores/publish.ts`
- [x] `src/stores/osint_source.ts`
- [x] `src/stores/auth.ts`
- [x] `src/stores/config.ts`
- [x] `src/stores/analyze.ts`
- [x] `src/stores/assess.ts`
- [x] `src/stores/index.ts`
- [x] Remaining high-impact store domains migrated

## Phase 6: Composables

- [x] Migrate composables with explicit return/event types
- [x] `src/composables/useAuth.ts`
- [x] `src/composables/useSSE.ts`
- [ ] Convert any remaining JS composables (if introduced)

## Phase 7: Components by feature batch

- [ ] Convert Vue scripts in vertical slices:
- [x] app shell/login
- [x] dashboard
- [x] assess
- [x] analyze
- [x] publish
- [x] config
- [x] config: settings shell + users/roles/organizations/workflow
- [x] config: data providers + AI providers
- [x] config: remote (access + nodes)
- [x] config: external users tab + dialog + admin shell
- [x] config: collectors/presenters/publishers/bots admin tab shells
- [x] config: publishers nodes + publisher presets (views + dialogs)
- [x] config: collectors nodes + OSINT sources/groups (views + dialogs)
- [x] config: presenters nodes + product types (views + dialogs)
- [x] config: report types + attributes (views + dialogs)
- [x] config: bots nodes + bot presets (views + dialogs)
- [x] config: ACL + asset groups + notification templates (views + dialogs)
- [x] config: word lists (view + dialog)
- [x] nav/layout: home + nav shells + MyAssets view shell
- [x] common primitives: action/add buttons, confirmation dialog, snackbar, base/card/dialog components
- [x] common filters/list selectors: BaseToolbarFilter, ToolbarFilter, ContentData, StateSelector
- [x] common actions: ToolbarGroup
- [x] common attributes (batch 1): String, Number, Boolean, Text, Date, Time, DateTime, Enum
- [x] common attributes (batch 2): ItemLayout, ValueLayout, Container, Radio, RichText
- [x] common attributes (batch 3): TLP, Attachment
- [x] common attributes (batch 4): CPE, CVE, CWE
- [x] common attributes (batch 5): CVSS
- [x] assets: ToolbarFilterAssets, ContentDataAssets, NewAsset, CardAsset
- [x] navigation/user shell: MainMenu, UserMenu
- [x] user settings dialog: UserSettings
- [x] common attributes (batch 6): RemoteAttributeContainer, RemoteAttributeString, RemoteAttributeAttachment
- [x] common tools: CalculatorCVSS
- [x] analyze/publish selectors: RemoteReportItem, RemoteReportItemSelector, ReportItemSelector
- [x] analyze/publish cards: CardAnalyze, CardProduct
- [x] assess details/actions: NewsItemAttribute, NewsItemSingleDetail, NewsItemAggregateDetail, ReportsListDialog
- [x] assess dialogs/cards: AssessItemActions, CardAssess, NewsItemDetailDialog, AddNewsItemDialog
- [x] analyze editor/selector: NewReportItem, NewsItemSelector
- [x] publish editor: NewProduct
- [x] assets editor: AssetDetailDialog
- [x] final pass: all Vue `script setup` blocks migrated to TypeScript (`<script setup lang="ts">`)

## Phase 8: Tests

- [x] Keep JS tests running while app code moves to TS
- [ ] Migrate helpers/tests gradually to TS where beneficial
- [x] Run full GUI v3 unit suite after major migration batches
- [x] Run E2E smoke/regression checks for migrated flows
- [x] E2E blocker (historical): `npm run test:e2e` reported 106 failed, 2 passed
- [x] E2E blocker detail (resolved): WebKit browser executable missing (`npx playwright install` completed)
- [x] E2E blocker detail (resolved): Chromium/Firefox intermittent `NS_ERROR_CONNECTION_REFUSED` fixed by Playwright webServer env pinning
- [x] E2E smoke detail (resolved): Chromium auth from `4 passed, 3 failed` to `7 passed`
- [x] E2E setup progress: installed Playwright browsers (`chromium`, `firefox`, `webkit`)
- [x] E2E setup progress: Playwright webServer now pins Vite proxy env to local E2E core (`127.0.0.1:8082`) in both configs
- [x] E2E smoke progress: Chromium auth suite now passes (`7 passed`)
- [x] E2E regression status (Chromium all specs): from `17 passed, 19 failed` to `36 passed`
- [x] E2E regression blocker detail (resolved): stale test assumptions/selectors updated (route expectations, strict locator ambiguity, and form field selectors)
- [x] E2E regression progress: updated helpers/specs for current table-based config UI and route behavior
- [x] E2E regression progress: Chromium subset green for migrated admin/navigation flows (`navigation.spec.js` + `organizations.spec.js` + `roles.spec.js`: `29 passed`)
- [x] E2E final matrix status: `108 passed` across configured browsers (`chromium`, `firefox`, `webkit`)

## Phase 9: Tighten strictness

- [ ] Increase strict TS flags step-by-step
- [ ] Reduce temporary `any` / broad casts over time
- [ ] Address warnings that block stricter settings
- [x] Baseline check: current app code typecheck passes with `strict: false` (next step is incremental strictness)
- [x] Strictness progress: enabled `noImplicitReturns` and fixed first surfaced issue (`NewReportItem.vue`)
- [x] Strictness progress: enabled `noFallthroughCasesInSwitch` (no additional type issues surfaced)
- [x] Strictness progress: enabled `noUncheckedIndexedAccess` (no additional type issues surfaced)
- [x] Strictness progress: enabled `useUnknownInCatchVariables` and narrowed error handling in analyze/assess components
- [x] Strictness progress: enabled `noImplicitOverride` (no additional type issues surfaced)
- [x] Strictness progress: enabled `exactOptionalPropertyTypes` after optional-prop/default normalization sweeps
- [x] Strictness progress: enabled `noPropertyAccessFromIndexSignature` after dedicated sweep (TS4111 reduced from 68 to 0)
- [x] Cast-reduction progress: reduced broad casts in auth/settings paths (`stores/auth.ts`, `stores/settings.ts`, `services/settings.ts`) with typecheck + focused tests green
- [x] Cast-reduction progress: reduced broad casts in analyze/assess stores (`stores/analyze.ts`, `stores/assess.ts`) and normalized cancelable-response typing while preserving state behavior
- [x] Cast-reduction progress: reduced broad casts in dashboard/config stores (`stores/dashboard.ts`, `stores/config.ts`) with typecheck + focused tests green
- [x] Cast-reduction progress: reduced broad casts in API/services (`api/auth.ts`, `services/jwt.ts`, `services/permissions.ts`) and restored backward-compatible auth token/id handling with typecheck + focused tests green
- [x] Cast-reduction progress: removed analyze/publish card-level store casts in `CardAnalyze.vue` and `CardProduct.vue` while keeping multiselect/delete flows type-safe
- [x] Cast-reduction progress: removed store-level `as any` usage in `CardAssess.vue`, `ContentDataAssets.vue`, and `UserMenu.vue` with no diagnostics regressions
- [x] Cast-reduction progress: removed analyze-store `as any` usage in `ReportItemSelector.vue` and `RemoteReportItemSelector.vue` and dropped redundant update payload casts
- [x] Cast-reduction progress: removed assess/settings store `as any` usage in `NewsItemSelector.vue` and `UserSettings.vue` with diagnostics clean
- [x] Cast-reduction progress: removed `as any`/`: any` store and callback usage in `ToolbarGroup.vue` via typed store instances and unknown-safe error handling
- [x] Cast-reduction progress: removed API/payload `as any` usage in `ReportsListDialog.vue` and `RemoteReportItem.vue` with typed response normalization
- [x] Cast-reduction progress: removed remaining low-risk `as any` usage in `MainMenu.vue`, `AddNewsItemDialog.vue`, `NewsItemAggregateDetail.vue`, `NewsItemAttribute.vue`, `NewsItemSingleDetail.vue`, `AttributeItemLayout.vue`, and `NewReportItem.vue`
- [x] Cast-reduction progress: reduced `: any` from 27 -> 14 by typing `CalculatorCVSS.vue`, `NewProduct.vue`, `AddNewsItemDialog.vue`, `AssetDetailDialog.vue`, and `NewReportItem.vue`
- [x] Cast-reduction progress: removed the final 14 `: any` occurrences across common attribute components (`AttributeCVSS.vue`, `AttributeDateTime.vue`, `AttributeTime.vue`, `AttributeDate.vue`, `AttributeEnum.vue`, `AttributeCVE.vue`, `AttributeString.vue`, `AttributeCWE.vue`, `AttributeCPE.vue`, `AttributeRichText.vue`, `AttributeRadio.vue`, `AttributeText.vue`, `AttributeBoolean.vue`, `AttributeNumber.vue`) -> global `: any` count is now 0
- [x] Strictness progress (`noPropertyAccessFromIndexSignature` prep): removed TS4111 clusters in `CardCompact.vue`, `useAttributes.ts`, and toolbar filter slots (assess/analyze/publish)

## Phase 10: Cleanup

- [x] Remove leftover JS twins/shims when safe (app/runtime code complete; tests intentionally out of scope)
- [x] Cleanup progress: removed JS shim twins for `src/api/*`, `src/services/api_service`, and `src/stores/*`
- [x] Cleanup progress: converted runtime entry files to TypeScript (`src/main.ts`, `src/router.ts`) and removed JS originals
- [x] Cleanup progress: removed composable JS shim (`src/composables/useSSE.js`) in favor of `useSSE.ts`
- [x] Cleanup progress: migrated attribute shared composable to TypeScript (`src/components/common/attribute/useAttributes.ts`) and updated all component imports
- [ ] Enforce TS-first checks in CI
- [x] Confirm final state: typecheck + unit + E2E all green

## Ongoing Validation Rules

- [x] Run format after each migration slice
- [x] Run `vue-tsc --noEmit` after each migration slice
- [x] Run focused unit tests after each migration slice
