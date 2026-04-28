# Attribute System Vue3 Migration

**Status:** IN PROGRESS (Foundation Phase)
**Started:** March 7, 2026
**Estimated Completion:** Phase 1 (3-5 days)

## Architecture Overview

The Attribute System is a Vue3 implementation of dynamic attribute rendering and editing for Taranis-NG items (News Items, Report Items, Products, Assets).

### Components Structure

```
attribute/
├── useAttributes.js              # Composable with shared logic (from AttributesMixin)
├── AttributeItemLayout.vue       # Layout wrapper for attribute items
├── AttributeValueLayout.vue      # Layout for individual values
├── AttributeContainer.vue        # Dynamic dispatcher component
├── basic/
│   ├── AttributeString.vue       # Single-line text
│   ├── AttributeNumber.vue       # Numeric values
│   ├── AttributeBoolean.vue      # True/False toggle
│   └── AttributeEnum.vue         # Dropdown selector
├── temporal/
│   ├── AttributeDate.vue         # Date picker
│   ├── AttributeTime.vue         # Time picker
│   └── AttributeDateTime.vue     # Combined date+time
├── text/
│   ├── AttributeText.vue         # Multi-line text
│   └── AttributeRichText.vue     # Rich text editor (requires vue-editor investigation)
├── specialized/
│   ├── AttributeTLP.vue          # TLP classification selector
│   ├── AttributeRadio.vue        # Radio button group
│   ├── AttributeCPE.vue          # CPE selector/search
│   ├── AttributeCVE.vue          # CVE lookup
│   ├── AttributeCWE.vue          # CWE lookup
│   └── AttributeCVSS.vue         # CVSS score calculator
├── file/
│   ├── AttributeAttachment.vue   # File upload/download (CSP fix needed)
│   └── RemoteAttributeAttachment.vue # Remote file handling
└── remote/
    ├── RemoteAttributeContainer.vue
    ├── RemoteAttributeString.vue
    └── ...RemoteAttribute* variants
```

## Vue 2 → Vue 3 Conversion Notes

### Key Changes
1. **Mixin → Composable:** Options API mixins → Composition API with `useAttributes()`
2. **API Integration:** Pinia store access instead of `this.$store`
3. **Router:** `useRoute()` composable instead of `this.$route`
4. **i18n:** Direct import from `vue-i18n` instead of `$t()`
5. **Event Emission:** Define using `defineEmits()` instead of `this.$emit()`
6. **Props:** Use `defineProps()` for type safety

### Phase 1: MVP Foundation (5-7 days, 1 senior dev)
- [x] Create directory structure
- [ ] Port `useAttributes` composable
- [ ] Port layout components (ItemLayout, ValueLayout)
- [ ] Port `AttributeContainer` dispatcher
- [ ] Port basic types: String, Number, Boolean, Enum, Radio
- [ ] Test with NewsItemDetail component

**Deliverable:** MVP supports READ/EDIT of basic item attributes

### Phase 2: Common Types (3-5 days)
- [ ] Temporal types: Date, Time, DateTime
- [ ] Text types: Text, RichText (requires integration investigation)
- [ ] Special types: TLP, Radio
- [ ] Remote variants

**Deliverable:** Handle 80% of common attribute types

### Phase 3: Advanced Types (5-7 days)
- [ ] Specialized types: CPE, CVE, CWE, CVSS
- [ ] File handling: Attachment (with CSP fixes)
- [ ] Integration testing

**Deliverable:** Complete attribute system ready for all workflows

## Dependencies & Blockers

### External Dependencies
- ✅ Pinia stores (working)
- ✅ API layer (working)
- ✅ i18n translations (working)
- ⚠️ Rich Text Editor (need vue-editor replacement)
- ⚠️ CPE/CVE/CWE data APIs (need to verify)

### Blocked By
- None (can start immediately)

### Blocks
- NewsItemDetail component
- ReportItemDetail component
- All item editing workflows

## Testing Strategy

1. **Unit Tests:** Each attribute type independently
2. **Integration Tests:** Container dispatching to correct type
3. **E2E Tests:** Full item edit workflow
4. **Accessibility:** Screen reader support for all types
5. **Performance:** Test with large attribute lists

## Rollout Plan

1. Merge foundation (Phase 1) when MVP complete
2. Incrementally add additional types
3. Monitor performance and user feedback
4. Refactor complex types as needed

## Key Files to Update After Migration

- `NewsItemDetail.vue` - Use AttributeContainer
- `NewReportItem.vue` - Use AttributeContainer
- `NewProduct.vue` - Use AttributeContainer
- `NewAsset.vue` - Use AttributeContainer
- `AttributesView.vue` - Config for attribute management
