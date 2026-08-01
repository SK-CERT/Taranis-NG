/**
 * Registry describing each "node" config type. Collectors / Presenters / Publishers /
 * Bots nodes share the same management UI (name, description, API URL, API key); only
 * their naming, store slice, API functions and permissions differ. The shared
 * NodesManager + NodeDialog components are driven by these entries.
 */
import {
    createNewCollectorsNode,
    updateCollectorsNode,
    deleteCollectorsNode,
    createNewPresentersNode,
    updatePresentersNode,
    deletePresentersNode,
    createNewPublishersNode,
    updatePublishersNode,
    deletePublishersNode,
    createNewBotsNode,
    updateBotsNode,
    deleteBotsNode
} from '@/api/config'

export type NodeType = 'collectors' | 'presenters' | 'publishers' | 'bots'

export type NodeTypeConfig = {
    /** i18n key prefix for the dialog/labels (e.g. "collectors_node"). */
    i18nPrefix: string
    /** Permission key prefix (e.g. "CONFIG_COLLECTORS_NODE"); CREATE/DELETE are appended. */
    permissionPrefix: string
    /** Name of the config-store list slice (e.g. "collectorsNodes"). */
    listKey: string
    /** Name of the config-store load action (e.g. "loadCollectorsNodes"). */
    loadAction: string
    createFn: (node: unknown) => Promise<unknown>
    updateFn: (node: unknown) => Promise<unknown>
    deleteFn: (node: unknown) => Promise<unknown>
    /** Whether the API key is mandatory (true for bots). */
    apiKeyRequired: boolean
}

export const NODE_TYPES: Record<NodeType, NodeTypeConfig> = {
    collectors: {
        i18nPrefix: 'collectors.nodes',
        permissionPrefix: 'CONFIG_COLLECTORS_NODE',
        listKey: 'collectorsNodes',
        loadAction: 'loadCollectorsNodes',
        createFn: createNewCollectorsNode,
        updateFn: updateCollectorsNode,
        deleteFn: deleteCollectorsNode,
        apiKeyRequired: false
    },
    presenters: {
        i18nPrefix: 'presenters.nodes',
        permissionPrefix: 'CONFIG_PRESENTERS_NODE',
        listKey: 'presentersNodes',
        loadAction: 'loadPresentersNodes',
        createFn: createNewPresentersNode,
        updateFn: updatePresentersNode,
        deleteFn: deletePresentersNode,
        apiKeyRequired: false
    },
    publishers: {
        i18nPrefix: 'publishers.nodes',
        permissionPrefix: 'CONFIG_PUBLISHERS_NODE',
        listKey: 'publishersNodes',
        loadAction: 'loadPublishersNodes',
        createFn: createNewPublishersNode,
        updateFn: updatePublishersNode,
        deleteFn: deletePublishersNode,
        apiKeyRequired: false
    },
    bots: {
        i18nPrefix: 'bots.nodes',
        permissionPrefix: 'CONFIG_BOTS_NODE',
        listKey: 'botsNodes',
        loadAction: 'loadBotsNodes',
        createFn: createNewBotsNode,
        updateFn: updateBotsNode,
        deleteFn: deleteBotsNode,
        apiKeyRequired: true
    }
}
