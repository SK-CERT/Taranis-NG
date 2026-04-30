# Unified Toolbar Filter System

**Last Updated:** April 28, 2026

## Overview

The toolbar filter components across Assess, Analyze, and Publish views have been unified using a base component architecture. This ensures consistency, reduces code duplication, and makes future maintenance easier.

There are two notable exceptions:
- **Assets** uses `ToolbarFilterAssets.vue`, a dedicated toolbar tailored to vulnerability filtering and alphabetical/vulnerability sorting
- **Admin CRUD views** use `components/common/ToolbarFilter.vue`, a simpler search-and-count toolbar

## Architecture

### BaseToolbarFilter (`/components/common/BaseToolbarFilter.vue`)

The base component provides common functionality organized in three toolbars:

**Toolbar 1 - Main Actions:**
- Title and search bar
- Add button slot

**Toolbar 2 - Filtering & Sorting:**
- Day range filters (optional, configurable)
- Custom filter slots for view-specific filters
- Sort buttons (optional, customizable via slot)

**Toolbar 3 - Count Information:**
- Total count display
- Selected count display (optional)

**Features:**
- Separate toolbars for clean layout
- No overlapping UI elements
- Consistent layout and styling
- Responsive design

**Props:**
- `title` - Toolbar title (i18n key)
- `showAddButton` - Show the shared add button component (default: false)
- `addButtonLabel` - I18n key for the shared add button label (default: 'common.add_btn')
- `totalCountTitle` - Total count label (i18n key, default: 'toolbar_filter.total_count')
- `totalCount` - Number to display (default: 0)
- `currentlyShowingCount` - Optional secondary count shown in the info toolbar
- `showSelectedCount` - Show/hide selected count (default: false)
- `selectedCountTitle` - Selected count label (i18n key, default: 'toolbar_filter.selected_count')
- `selectedCount` - Selected items count (default: 0)
- `initialFilter` - Initial filter state object
- `showDayRanges` - Show/hide day range filters (default: true)
- `dayRanges` - Array of day range options (customizable)
- `showSort` - Show/hide default sort buttons (default: true)
- `sortTooltipPrefix` - I18n prefix used for the default date sort tooltip (default: 'toolbar_filter')
- `searchDebounceMs` - Search debounce delay (default: 300ms)

**Slots:**
- `#addbutton` - Slot for add/action buttons in the top toolbar
- `#custom-filters` - Slot for view-specific filters (in filter toolbar)
- `#sort-buttons` - Slot to override default sort buttons (in filter toolbar)

**Events:**
- `@update-filter` - Emitted when filter changes

## Toolbar Layout

### Visual Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Main Toolbar 1: Actions                                     │
│ [Title]        [Search Field]             [Add Button]      │
└─────────────────────────────────────────────────────────────┘
──────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────┐
│ Filter Toolbar 2: Filters & Sorting                         │
│ [Day Ranges] | [Custom Filters] [Flex Space] [Sort Buttons]│
└─────────────────────────────────────────────────────────────┘
──────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────┐
│ Count Toolbar 3: Information                                │
│ Total: 42     Selected: 5                                   │
└─────────────────────────────────────────────────────────────┘
```

## ToolbarFilter (/components/common/ToolbarFilter.vue)

Basic toolbar alternative with simpler layout:

**Features:**
- Title
- Search field with debounce
- Total count display
- Selected count display (optional)
- Add button slot

**Usage:** Used by standalone CRUD list views

## View-Specific Implementations

### 1. ToolbarFilterAssess

**Location:** `/components/assess/ToolbarFilterAssess.vue`

**Custom Features:**
- Three-state filters (read, important, relevant)
  - States: ALL → true → false → ALL
  - Visual indicators: outline icons for ALL, solid for active states
  - Blue background when active
- Relevance sort (in addition to date sort)
- Compact mode toggle
- Selection count display

**Filter States:**
```javascript
{
  search: '',
  range: 'ALL',
  read: false,        // Default: show unread only
  important: 'ALL',
  relevant: 'ALL',
  sort: 'DATE_DESC'   // or 'DATE_ASC', 'RELEVANCE_DESC'
}
```

### 2. ToolbarFilterAnalyze

**Location:** `/components/analyze/ToolbarFilterAnalyze.vue`

**Custom Features:**
- Completed/incompleted toggle filters (mutually exclusive)
- Date sort (ascending/descending)
- Uses shared `ToolbarGroup.vue` for multi-select actions

**Filter States:**
```javascript
{
  search: '',
  range: 'ALL',
  completed: false,
  incompleted: true,
  sort: 'DATE_DESC'   // or 'DATE_ASC'
}
```

### 3. ToolbarFilterPublish

**Location:** `/components/publish/ToolbarFilterPublish.vue`

**Custom Features:**
- Published/unpublished toggle filters (mutually exclusive)
- Date sort (ascending/descending)
- Longer search debounce (800ms vs 300ms)
- Uses shared `ToolbarGroup.vue` for multi-select actions

**Filter States:**
```javascript
{
  search: '',
  range: 'ALL',
  published: false,
  unpublished: true,
  sort: 'DATE_DESC'   // or 'DATE_ASC'
}
```

### 4. ToolbarFilterAssets

**Location:** `/components/assets/ToolbarFilterAssets.vue`

**Custom Features:**
- Search field
- Vulnerable-only chip filter
- Sort toggle between alphabetical and vulnerability order
- Inline total count display
- Separate add-button slot (`#add-button`)

**Filter States:**
```javascript
{
  search: '',
  vulnerable: false,
  sort: 'ALPHABETICAL'
}
```

## Common Day Range Options

All views use the same day range filters:
- ALL - All time
- TODAY - Today only
- WEEK - This week
- MONTH - This month
- LAST_7_DAYS - Last 7 days
- LAST_31_DAYS - Last 31 days

## Usage Example

### Creating a New Toolbar

```vue
<template>
  <BaseToolbarFilter
    ref="baseFilter"
    :title="'my_view.title'"
    :total-count-title="'toolbar_filter.total_count'"
    :total-count="totalCount"
    :show-selected-count="multiSelectActive"
    :selected-count-title="'toolbar_filter.selected_count'"
    :selected-count="selectedCount"
    :initial-filter="filter"
    :show-day-ranges="true"
    :show-sort="false"
    @update-filter="handleFilterUpdate"
  >
    <!-- Add Button -->
    <template #addbutton>
      <v-btn color="primary" @click="addItem">Add Item</v-btn>
    </template>

    <!-- Custom Filters -->
    <template #custom-filters>
      <v-divider vertical />

      <div style="display: flex; gap: 4px;">
        <v-chip
          :color="filter.myCustomFilter ? 'primary' : 'default'"
          @click="toggleCustomFilter"
        >
          <v-tooltip activator="parent">My Filter</v-tooltip>
          <v-icon>mdi-filter</v-icon>
        </v-chip>
      </div>
    </template>
  </BaseToolbarFilter>
</template>

<script setup>
import { ref } from 'vue'
import BaseToolbarFilter from '@/components/common/BaseToolbarFilter.vue'

const filter = ref({
  search: '',
  range: 'ALL',
  myCustomFilter: false,
  sort: 'DATE_DESC'
})

const totalCount = ref(0)

const handleFilterUpdate = (updatedFilter) => {
  filter.value = { ...filter.value, ...updatedFilter }
  // Emit or handle filter change
}

const toggleCustomFilter = () => {
  filter.value.myCustomFilter = !filter.value.myCustomFilter
  // Emit filter update
}
</script>
```

## Benefits

1. **Consistency** - All views have the same look and feel
2. **Maintainability** - Changes to common features only need to be made once
3. **Flexibility** - View-specific features can be added via slots
4. **Reusability** - Easy to add new views with custom filters
5. **DRY Principle** - No code duplication across views

## Usage Notes

If you need to add a new filtered view:

1. Use `BaseToolbarFilter` for Assess/Analyze/Publish-style views with range filters and shared sort behavior
2. Use `ToolbarFilter` for simple admin CRUD lists
3. Define your initial filter state
4. Use slots for view-specific filters when using `BaseToolbarFilter`
5. Handle filter updates in `@update-filter` or the view-specific event mechanism

`BaseToolbarFilter` handles:
- Search debouncing
- Day range selection
- Basic sort options
- Layout and styling
- Responsive design
