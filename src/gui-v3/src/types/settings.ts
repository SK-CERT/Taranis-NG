export const Settings = {
    // global settings
    DATE_FORMAT: 'DATE_FORMAT',
    REPORT_SELECTOR_READ_ONLY: 'REPORT_SELECTOR_READ_ONLY',
    TIME_FORMAT: 'TIME_FORMAT',
    CASCADE_STATES_ENABLED: 'CASCADE_STATES_ENABLED',
    // user settings
    CONTENT_DEFAULT_LANGUAGE: 'CONTENT_DEFAULT_LANGUAGE',
    DARK_THEME: 'DARK_THEME',
    HOTKEYS: 'HOTKEYS',
    SPELLCHECK: 'SPELLCHECK',
    TAG_COLOR: 'TAG_COLOR',
    UI_LANGUAGE: 'UI_LANGUAGE',
    UI_THEME: 'UI_THEME'
} as const

export const HotkeyAction = {
    COLLECTION_UP_1: 'collection_up_1',
    COLLECTION_UP_2: 'collection_up_2',
    COLLECTION_DOWN_1: 'collection_down_1',
    COLLECTION_DOWN_2: 'collection_down_2',
    SHOW_ITEM_1: 'show_item_1',
    SHOW_ITEM_2: 'show_item_2',
    SHOW_ITEM_3: 'show_item_3',
    CLOSE_ITEM_1: 'close_item_1',
    CLOSE_ITEM_2: 'close_item_2',
    CLOSE_ITEM_3: 'close_item_3',
    HOME: 'home',
    END: 'end',
    SOURCE_GROUP_UP: 'source_group_up',
    SOURCE_GROUP_DOWN: 'source_group_down',
    READ_ITEM: 'read_item',
    IMPORTANT_ITEM: 'important_item',
    LIKE_ITEM: 'like_item',
    UNLIKE_ITEM: 'unlike_item',
    DELETE_ITEM: 'delete_item',
    SELECTION: 'selection',
    GROUP: 'group',
    UNGROUP: 'ungroup',
    NEW_PRODUCT: 'new_product',
    AGGREGATE_OPEN: 'aggregate_open',
    OPEN_ITEM_SOURCE: 'open_item_source',
    OPEN_SEARCH: 'open_search',
    RELOAD: 'reload',
    ENTER_VIEW_MODE: 'enter_view_mode',
    DASHBOARD_VIEW: 'dashboard_view',
    ANALYZE_VIEW: 'analyze_view',
    PUBLISH_VIEW: 'publish_view',
    MY_ASSETS_VIEW: 'my_assets_view',
    CONFIGURATION_VIEW: 'configuration_view',
    ENTER_FILTER_MODE: 'enter_filter_mode'
} as const

export type SettingKey = (typeof Settings)[keyof typeof Settings]
export type HotkeyActionType = (typeof HotkeyAction)[keyof typeof HotkeyAction]

export interface SettingEntry {
    key: SettingKey
    value: string
}
