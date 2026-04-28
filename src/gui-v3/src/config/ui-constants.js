/**
 * UI Constants - Centralized UI configuration for consistent styling across the app
 * Based on Vue2 layout_config.js but adapted for Vue3/Vuetify3
 */

/**
 * Icon constants - Material Design Icons
 */
export const ICONS = Object.freeze({
  ACCOUNT: 'mdi-account',
  ACCOUNT_ARROW_RIGHT: 'mdi-account-arrow-right',
  ACCOUNT_GROUP: 'mdi-account-group',
  ALERT: 'mdi-alert',
  ALERT_CIRCLE: 'mdi-alert-circle',
  ALPHABETICAL: 'mdi-alphabet-latin',
  ANALYZE: 'mdi-file-outline',
  ARROW_COLLAPSE_DOWN: 'mdi-arrow-collapse-down',
  ARROW_COLLAPSE_UP: 'mdi-arrow-collapse-up',
  ARROW_DOWN: 'mdi-arrow-down',
  ARROW_DOWN_BOLD_CIRCLE_OUTLINE: 'mdi-arrow-down-bold-circle-outline',
  ARROW_DOWN_CIRCLE_OUTLINE: 'mdi-arrow-down-circle-outline',
  ARROW_UP: 'mdi-arrow-up',
  ARROW_UP_CIRCLE_OUTLINE: 'mdi-arrow-up-circle-outline',
  ASC: 'mdi-sort-ascending',
  CALCULATOR: 'mdi-calculator',
  CARD_SEARCH_OUTLINE: 'mdi-card-search-outline',
  CHART_BOX: 'mdi-chart-box',
  CHECK_CIRCLE: 'mdi-check-circle',
  CHECKBOX_BLANK_OUTLINE: 'mdi-checkbox-blank-outline',
  CHECKBOX_MULTIPLE_MARKED: 'mdi-checkbox-multiple-marked',
  CLOCK: 'mdi-clock-outline',
  CLOCK_ALERT: 'mdi-clock-alert',
  CLOSE: 'mdi-close-circle',
  CLOSE_BOX: 'mdi-close',
  CLOSE_BOX_OUTLINE: 'mdi-close-box-outline',
  COG: 'mdi-cog',
  COMPLETED: 'mdi-progress-check',
  CONTENT_SAVE: 'mdi-content-save',
  CREATION: 'mdi-creation',
  DATABASE_OFF: 'mdi-database-off',
  DELETE: 'mdi-delete-outline',
  DELETE_BOX: 'mdi-delete',
  DESC: 'mdi-sort-descending',
  DOWNLOAD: 'mdi-download',
  DOWNLOAD_NETWORK: 'mdi-download-network',
  EDIT: 'mdi-pencil',
  EMAIL_OPEN: 'mdi-email-open',
  EXCLAMATION_THICK: 'mdi-exclamation-thick',
  EXPORT: 'mdi-export',
  FILE_CABINET: 'mdi-file-cabinet',
  FILE_CHART_OUTLINE: 'mdi-file-chart-outline',
  FILE_DOCUMENT: 'mdi-file-document',
  FILE_OUTLINE: 'mdi-file-outline',
  FILE_TABLE: 'mdi-file-table',
  FILE_TABLE_OUTLINE: 'mdi-file-table-outline',
  FILTER_OUTLINE: 'mdi-filter-outline',
  FORMAT_LIST_BULLETED: 'mdi-format-list-bulleted',
  GROUP: 'mdi-group',
  HELP: 'mdi-help-circle-outline',
  IMPORT: 'mdi-import',
  IMPORTANT: 'mdi-star',
  IMPORTANT_OUTLINE: 'mdi-star-outline',
  INFORMATION: 'mdi-information',
  INFORMATION_OUTLINE: 'mdi-information-outline',
  IN_ANALYZE: 'mdi-file-cog-outline',
  INCOMPLETED: 'mdi-progress-close',
  LIKE: 'mdi-thumb-up',
  LIKE_OUTLINE: 'mdi-thumb-up-outline',
  LOCK: 'mdi-lock-outline',
  LOCK_CHECK: 'mdi-lock-check',
  MAGNIFY: 'mdi-magnify',
  MULTISELECT: 'mdi-checkbox-multiple-marked-outline',
  NEWSPAPER_VARIANT: 'mdi-newspaper-variant',
  NEWSPAPER_VARIANT_OUTLINE: 'mdi-newspaper-variant-outline',
  NO_STATE: 'mdi-progress-helper',
  OFFICE_BUILDING: 'mdi-office-building',
  OPEN: 'mdi-open-in-new',
  OPEN_SOURCE: 'mdi-open-in-app',
  PLUS: 'mdi-plus-circle-outline',
  PLUS_BOX: 'mdi-plus-box',
  PUBLISH: 'mdi-file-outline',
  READ: 'mdi-eye',
  READ_OUTLINE: 'mdi-eye-outline',
  RELOAD: 'mdi-reload',
  RELEVANT: 'mdi-thumb-up',
  REMOVE: 'mdi-minus-thick',
  SELECT_ALL: 'mdi-checkbox-multiple-outline',
  SEND: 'mdi-send',
  SEND_OUTLINE: 'mdi-send-outline',
  SEPARATOR: 'mdi-drag-vertical',
  SHIELD_SEARCH: 'mdi-shield-search',
  TEXT_BOX_OUTLINE: 'mdi-text-box-outline',
  TIMER_SAND: 'mdi-timer-sand',
  TIMER_SAND_COMPLETE: 'mdi-timer-sand-complete',
  TIMER_SAND_PAUSED: 'mdi-timer-sand-paused',
  UNGROUP: 'mdi-ungroup',
  UNIMPORTANT: 'mdi-star-off',
  UNLIKE: 'mdi-thumb-down',
  UNLIKE_OUTLINE: 'mdi-thumb-down-outline',
  UNREAD: 'mdi-eye-off',
  UNSELECT_ALL: 'mdi-checkbox-multiple-blank-outline',
  VULNERABLE: 'mdi-alert-octagon-outline',
  VIEW_DASHBOARD_VARIANT_OUTLINE: 'mdi-view-dashboard-variant-outline',
  VIEW_HEADLINE: 'mdi-view-headline',
  WRENCH: 'mdi-wrench'
})

/**
 * Button configurations - Standard button props for common actions
 */
export const BUTTON_CONFIGS = Object.freeze({
  DELETE: {
    icon: ICONS.DELETE,
    color: 'error',
    variant: 'text',
    size: 'small'
  },
  EDIT: {
    icon: ICONS.EDIT,
    color: 'primary',
    variant: 'text',
    size: 'small'
  },
  PUBLISH: {
    icon: ICONS.PUBLISH,
    color: 'info',
    variant: 'text',
    size: 'small'
  },
  REMOVE: {
    icon: ICONS.REMOVE,
    color: 'accent',
    variant: 'text',
    size: 'small'
  },
  LOCK: {
    icon: ICONS.LOCK,
    color: 'warning',
    variant: 'text',
    size: 'small'
  },
  OPEN: {
    icon: ICONS.OPEN,
    color: 'primary',
    variant: 'plain',
    size: 'small'
  },
  OPEN_SOURCE: {
    icon: ICONS.OPEN_SOURCE,
    color: 'primary',
    variant: 'plain',
    size: 'small'
  }
})

/**
 * Color constants
 */
export const COLORS = Object.freeze({
  PRIMARY: 'primary',
  SECONDARY: 'secondary',
  ERROR: 'error',
  WARNING: 'warning',
  SUCCESS: 'success',
  INFO: 'info',
  ACCENT: 'accent',
  ACTIVE: 'amber-darken-2'
})
