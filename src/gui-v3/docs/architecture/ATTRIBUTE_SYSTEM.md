# Attribute System

**Last Updated:** April 28, 2026

## Overview

The attribute system renders structured data fields on news items, report items, and products. It uses a **dispatcher pattern**: `AttributeContainer` reads the attribute type string from the backend and dynamically renders the correct component.

All attribute components live in `src/components/common/attribute/`.

The shared editing logic lives alongside them in `src/components/common/attribute/useAttributes.js`.

## Component Map

`AttributeContainer.vue` maps backend type strings to components:

| Backend type | Component | Description |
|---|---|---|
| `STRING` | `AttributeString` | Single-line text input |
| `NUMBER` | `AttributeNumber` | Numeric input |
| `BOOLEAN` | `AttributeBoolean` | Toggle switch |
| `ENUM` | `AttributeEnum` | Dropdown list |
| `RADIO` | `AttributeRadio` | Radio button group |
| `TEXT` | `AttributeText` | Multi-line textarea |
| `DATE` | `AttributeDate` | Date picker |
| `TIME` | `AttributeTime` | Time picker (HTML5 native) |
| `DATE_TIME` | `AttributeDateTime` | ISO 8601 datetime picker |
| `RICH_TEXT` | `AttributeRichText` | Quill WYSIWYG editor (PrimeVue Editor) |
| `TLP` | `AttributeTLP` | Traffic Light Protocol selector |
| `ATTACHMENT` | `AttributeAttachment` | File upload/download |
| `CPE` | `AttributeCPE` | CPE string with validation |
| `CVE` | `AttributeCVE` | CVE identifier |
| `CWE` | `AttributeCWE` | CWE identifier |
| `CVSS` | `AttributeCVSS` | CVSS score input |

## Usage

```vue
<AttributeContainer
  :attribute-item="attributeItem"
  :report-item-id="item.id"
  :read-only="true"
/>
```

To loop over all attributes on an item:

```vue
<v-col v-for="attributeItem in item.attributes" :key="attributeItem.id" cols="12">
  <AttributeContainer
    :attribute-item="attributeItem"
    :report-item-id="item.id"
    :read-only="!canEdit"
    :edit="editMode"
    :modify="hasPermission"
  />
</v-col>
```

### Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `attributeItem` | Object | required | Full attribute item object from API |
| `reportItemId` | Number | required | ID of the parent item (used for save API calls) |
| `readOnly` | Boolean | `false` | Disable all editing |
| `edit` | Boolean | `false` | Show edit controls |
| `modify` | Boolean | `false` | Allow value modifications |

## Data Structure

The `attributeItem` object passed to `AttributeContainer`:

```json
{
  "attribute_group_item": {
    "attribute": {
      "type": "STRING",
      "name": "Title",
      "description": ""
    },
    "min_occurrence": 1,
    "max_occurrence": 1
  },
  "values": [
    {
      "index": 0,
      "value": "Example value",
      "locked": false,
      "remote": false
    }
  ]
}
```

## Layout Components

Two shared layout wrappers keep visual consistency:

- **`AttributeItemLayout`** — outer container, renders label and an "add value" button when `max_occurrence > current count`
- **`AttributeValueLayout`** — per-value row with optional delete button and left/middle/right column slots

Each attribute component uses these layouts internally so they all look and behave consistently.

## useAttributes Composable

`src/components/common/attribute/useAttributes.js` provides shared logic used inside each attribute component:

```js
const {
  canModify,      // computed: edit && modify && !readOnly
  addButtonVisible, // computed: can add more values
  getLockedStyle,   // (index) → CSS class for locked state
  add,            // add a blank value
  del,            // (index) → remove a value
  onFocus,        // (index) → lock field
  onBlur,         // (index) → save + unlock field
  onKeyUp         // (index) → save on Enter
} = useAttributes(props)
```

Implementation note: the composable currently targets report-item attribute editing APIs (`updateReportItem`, lock/unlock calls in `@/api/analyze`).

## Adding a New Attribute Type

1. Create `src/components/common/attribute/AttributeMyType.vue`
2. Accept props: `attributeGroup`, `values`, `readOnly`, `edit`, `modify`, `reportItemId`
3. Use `useAttributes` composable for add/delete/lock logic
4. Wrap content in `<AttributeItemLayout>` / `<AttributeValueLayout>`
5. Register the new type in `AttributeContainer.vue`'s `componentMap`
6. Add the backend type string to the map key
